-- FX_RATE_DAILY  (Beyond Entity: ent_LoXHnTba1h, model mdl_uI9JmSHuG3 "Snowflake CORE Layer")
--
-- Reference data. Every USD figure in the platform reads this table, so every column is
-- NOT NULL: a rate row that cannot answer "what is this pair worth on this date" is not a
-- rate row. Rebuilt in full each run.
--
-- Direction: consumers multiply a source-currency amount by FX_RATE where FROM_CURRENCY is
-- the source currency and TO_CURRENCY is USD.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.FX_RATE_DAILY (
    RATE_DATE      DATE          NOT NULL,
    FROM_CURRENCY  VARCHAR(3)    NOT NULL,
    TO_CURRENCY    VARCHAR(3)    NOT NULL,
    FX_RATE        NUMERIC(18,8) NOT NULL
);
