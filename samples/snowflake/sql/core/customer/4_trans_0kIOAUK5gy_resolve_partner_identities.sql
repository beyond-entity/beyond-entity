-- Beyond Entity trans_0kIOAUK5gy  |  proc_j3HyTdoXBh "Resolve Customer Identity"  |  order 4
-- RAW_PARTNER_CUSTOMER_MAP -> CUSTOMER_IDENTITY_MAP. Weakest branch: confidence 0.80,
-- MATCH_METHOD 'PARTNER_DECLARED'. The partner asserts the mapping; we cannot verify it.
--
-- D19. The partner customer identifier is only unique WITHIN a partner -- the same scoping
-- that makes CAMPAIGN_KEY composite. Two consequences, both wrong before this fix:
--   * PARTITION BY PARTNER_CUSTOMER_ID alone silently discarded one partner's mapping
--     whenever two partners happened to reuse an identifier;
--   * SOURCE_CUSTOMER_REF held a value that could not be traced back to a single source
--     row, because two partners' refs collide under one SOURCE_SYSTEM.
-- The reference is now the pair, and dedup partitions on the pair.
--
-- Tie-break is latest delivery (_INGESTED_AT, then _BATCH_ID), the append-only RAW rule
-- used everywhere else. SIGNUP_AT is a business timestamp that does not change between
-- deliveries of the same mapping, so ordering by it decided nothing and hid that.
INSERT INTO CUSTOMER_IDENTITY_MAP (ENTERPRISE_CUSTOMER_KEY, SOURCE_SYSTEM, SOURCE_CUSTOMER_REF, EMAIL_NORMALIZED, EMAIL_HASH, MATCH_METHOD, MATCH_CONFIDENCE, RESOLVED_AT, IS_ACTIVE)
SELECT MD5(LOWER(TRIM(m.EMAIL))), m._SOURCE_SYSTEM, CONCAT(m.PARTNER_ID, ':', m.PARTNER_CUSTOMER_ID), LOWER(TRIM(m.EMAIL)), SHA2(LOWER(TRIM(m.EMAIL)), 256), 'PARTNER_DECLARED', 0.80, CURRENT_TIMESTAMP(), TRUE
FROM RAW_PARTNER_CUSTOMER_MAP m
WHERE m.EMAIL IS NOT NULL AND TRIM(m.EMAIL) <> ''
QUALIFY ROW_NUMBER() OVER (PARTITION BY m.PARTNER_ID, m.PARTNER_CUSTOMER_ID ORDER BY m._INGESTED_AT DESC, m._BATCH_ID DESC) = 1
