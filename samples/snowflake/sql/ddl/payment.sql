-- PAYMENT  (Beyond Entity: ent_2Qa8irf5XI, model mdl_uI9JmSHuG3 "Snowflake CORE Layer")
--
-- Grain: one row per payment. Full rebuild.
-- PAYMENT_AMOUNT_USD is NOT NULL for the same reason as ORDER_FACT.ORDER_AMOUNT_USD.
--
-- Known gap: unlike ORDER_FACT there is no source-amount or applied-rate column here, so
-- the USD figure is not reproducible from the row alone. Worth adding if payment amounts
-- are ever disputed.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.PAYMENT (
    PAYMENT_KEY              VARCHAR(64)   NOT NULL PRIMARY KEY,
    ORDER_KEY                VARCHAR(64)   NOT NULL,
    ENTERPRISE_CUSTOMER_KEY  VARCHAR(64),
    PAYMENT_STATUS           VARCHAR(20),
    PAYMENT_METHOD           VARCHAR(30),
    PAID_AT_UTC              TIMESTAMP_NTZ,
    SOURCE_CURRENCY_CODE     VARCHAR(3),
    PAYMENT_AMOUNT_USD       NUMERIC(18,2) NOT NULL
);
