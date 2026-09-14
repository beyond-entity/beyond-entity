-- ORDER_FACT  (Beyond Entity: ent_8QPT9Jv4Ch, model mdl_uI9JmSHuG3 "Snowflake CORE Layer")
--
-- Grain: one row per order. Full rebuild.
--
-- ORDER_AMOUNT_USD and FX_RATE_APPLIED are NOT NULL, and that is the structural backstop
-- for the FX quality policy. Assert FX Rate Coverage is meant to stop the build before it
-- gets here; if a missing rate ever slips past the gate, this constraint fails the insert
-- rather than publishing an unresolved revenue number. Publishing null USD is the one
-- outcome the policy forbids, so it is made impossible rather than merely discouraged.
--
-- ORDER_AMOUNT_SOURCE and FX_RATE_APPLIED are both retained so ORDER_AMOUNT_USD is always
-- reproducible and auditable from the row itself.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.ORDER_FACT (
    ORDER_KEY                VARCHAR(64)   NOT NULL PRIMARY KEY,
    ENTERPRISE_CUSTOMER_KEY  VARCHAR(64)   NOT NULL,
    ORDER_STATUS             VARCHAR(20),
    ORDERED_AT_UTC           TIMESTAMP_NTZ NOT NULL,
    ORDER_DATE_UTC           DATE,
    SOURCE_CURRENCY_CODE     VARCHAR(3),
    ORDER_AMOUNT_SOURCE      NUMERIC(18,2),
    FX_RATE_APPLIED          NUMERIC(18,8) NOT NULL,
    ORDER_AMOUNT_USD         NUMERIC(18,2) NOT NULL,
    CHANNEL_CODE             VARCHAR(30)
);
