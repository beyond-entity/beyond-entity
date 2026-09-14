-- FX_COVERAGE_GAP  (Beyond Entity: ent_F3qXHMxMYd, model mdl_uI9JmSHuG3 "Snowflake CORE Layer")
--
-- This table IS the data quality failure. A non-empty FX_COVERAGE_GAP means the dependent
-- revenue builds MUST fail rather than publish. It exists so the failure is inspectable --
-- an operator sees which currency/date pairs are missing and how many rows they block,
-- instead of a stack trace.
--
-- USD never appears here: a USD row needs no conversion, so no rate is "required" for it.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.FX_COVERAGE_GAP (
    REQUIRED_CURRENCY   VARCHAR(3)    NOT NULL,
    REQUIRED_DATE       DATE          NOT NULL,
    SOURCE_TABLE        VARCHAR(60)   NOT NULL,
    AFFECTED_ROW_COUNT  NUMERIC(18)   NOT NULL,
    DETECTED_AT         TIMESTAMP_NTZ NOT NULL
);
