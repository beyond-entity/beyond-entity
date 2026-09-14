-- Beyond Entity trans_MydYVq9TcJ  |  proc_PASXcCWvuz "Build Core Customer"  |  order 1
-- CUSTOMER_IDENTITY_MAP (spine) + RAW_CUSTOMERS + RAW_PARTNER_CUSTOMER_MAP -> CUSTOMER.
--
-- The spine is the crosswalk, not Oracle: every resolved enterprise customer key gets a
-- CUSTOMER row, and Oracle attributes contribute when that customer exists in Oracle. A
-- customer discovered only through subscriptions, support or the partner feed still reaches
-- CUSTOMER and therefore CUSTOMER_360.
--
-- The SOURCE_SYSTEM predicate lives in the LEFT JOIN's ON clause on purpose. Moving it to
-- WHERE turns the LEFT JOIN back into an inner join and silently reinstates Oracle-only
-- membership.
--
-- :oracle_server_timezone is 'UTC' for this sample -- an explicit configuration assumption,
-- never the Snowflake session setting. VERIFY against the real Oracle system before
-- production: if Oracle stores server-local time, every FIRST_SEEN_AT_UTC is off by that
-- offset. The 3-arg CONVERT_TIMEZONE keeps the source zone explicit so this is a one-value
-- change rather than a rewrite.
--
-- D20. The partner mapping join reaches APPEND-ONLY RAW on email alone, so one customer can
-- match several rows: several deliveries of one mapping, and several partners claiming the
-- same person. The QUALIFY collapsed that fan-out to one row but said nothing about which,
-- so ACQUISITION_CAMPAIGN_ID was undefined whenever more than one candidate existed. The
-- ordering now reads FIRST_TOUCH as the earliest known signup, then the latest delivery,
-- then the partner id as a final deterministic key. It sits AFTER the Oracle and confidence
-- keys so it breaks only the ties they leave; moving it earlier would let the partner feed
-- decide which Oracle record wins.
--
-- The explicit CASE on SIGNUP_AT IS NULL is not decoration: Snowflake sorts NULLs last on
-- ASC and SQLite sorts them first, so leaving it implicit makes the result depend on the
-- engine. A mapping with a known signup time beats one without.
-- D22. ACQUISITION_CAMPAIGN_KEY added. The partner-reported FIRST_TOUCH_CAMPAIGN_ID is
-- unique only WITHIN a partner, so a consumer joining CAMPAIGN on it alone credits one
-- partner's campaign with another partner's customers and revenue. The composite key comes
-- from the same mapping row that supplies the id, so nothing new is sourced -- the
-- reference simply becomes resolvable. ACQUISITION_CAMPAIGN_ID stays as the partner-reported
-- value; every join from a customer to a campaign must use the KEY.
--
-- CONCAT returns NULL when either half is NULL, so a customer with no partner mapping gets
-- a NULL key rather than a key pointing at nothing.
INSERT INTO CUSTOMER (ENTERPRISE_CUSTOMER_KEY, CUSTOMER_NAME, EMAIL, EMAIL_HASH, PHONE_NUMBER, BILLING_COUNTRY_CODE, CUSTOMER_STATUS, FIRST_SEEN_AT_UTC, ACQUISITION_CAMPAIGN_ID, ACQUISITION_CAMPAIGN_KEY, SOURCE_SYSTEM_COUNT)
SELECT im.ENTERPRISE_CUSTOMER_KEY,
rc.CUSTOMER_NAME,
COALESCE(rc.EMAIL, im.EMAIL_NORMALIZED),
im.EMAIL_HASH,
rc.PHONE_NUMBER,
rc.COUNTRY_CODE,
CASE WHEN rc.CUSTOMER_ID IS NULL THEN 'UNKNOWN' WHEN rc.CUSTOMER_STATUS = 'ACTIVE' THEN 'ACTIVE' WHEN rc.CUSTOMER_STATUS = 'DORMANT' THEN 'DORMANT' ELSE 'CLOSED' END,
CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', rc.CREATED_AT),
pm.FIRST_TOUCH_CAMPAIGN_ID,
CONCAT(pm.PARTNER_ID, ':', pm.FIRST_TOUCH_CAMPAIGN_ID),
(SELECT COUNT(DISTINCT im2.SOURCE_SYSTEM) FROM CUSTOMER_IDENTITY_MAP im2 WHERE im2.ENTERPRISE_CUSTOMER_KEY = im.ENTERPRISE_CUSTOMER_KEY)
FROM CUSTOMER_IDENTITY_MAP im
LEFT JOIN RAW_CUSTOMERS rc ON im.SOURCE_SYSTEM = 'ORACLE_SALES' AND TO_VARCHAR(rc.CUSTOMER_ID) = im.SOURCE_CUSTOMER_REF
LEFT JOIN RAW_PARTNER_CUSTOMER_MAP pm ON LOWER(TRIM(pm.EMAIL)) = im.EMAIL_NORMALIZED
QUALIFY ROW_NUMBER() OVER (PARTITION BY im.ENTERPRISE_CUSTOMER_KEY ORDER BY CASE WHEN rc.CUSTOMER_ID IS NULL THEN 1 ELSE 0 END, rc.UPDATED_AT DESC, rc._INGESTED_AT DESC, im.MATCH_CONFIDENCE DESC, im.SOURCE_SYSTEM, CASE WHEN pm.SIGNUP_AT IS NULL THEN 1 ELSE 0 END, pm.SIGNUP_AT, pm._INGESTED_AT DESC, pm.PARTNER_ID) = 1
