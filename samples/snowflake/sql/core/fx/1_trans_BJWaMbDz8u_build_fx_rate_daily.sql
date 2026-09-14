-- Beyond Entity trans_BJWaMbDz8u  |  proc_AsyyNwdM2X "Build Core FX Rate"  |  order 1
-- RAW_FX_RATES -> FX_RATE_DAILY. Full rebuild.
--
-- Three guards, each against a different silent failure:
--   * the NOT NULL checks enforce what FX_RATE_DAILY declares and RAW deliberately
--     tolerates, so a row that failed to cast is dropped here and stays countable in RAW;
--   * FX_RATE > 0 is the important one. A zero rate errors nowhere. It multiplies through
--     every revenue figure in the platform and reports the affected currency as earning
--     nothing, which reads as a business result rather than a data fault;
--   * the QUALIFY takes the latest delivery per rate date and currency pair.
--
-- The _BATCH_ID tiebreak is load-bearing here in a way it is not in the customer builds.
-- There, a tie means two copies of the same source version and either will do. Here, two
-- deliveries of the same rate date can carry genuinely DIFFERENT rates, so an ambiguous
-- ordering would pick a revenue number at random. _BATCH_ID is the orchestrator run id,
-- which sorts chronologically for scheduled runs.

INSERT INTO FX_RATE_DAILY (RATE_DATE, FROM_CURRENCY, TO_CURRENCY, FX_RATE)
SELECT r.RATE_DATE, r.FROM_CURRENCY, r.TO_CURRENCY, r.FX_RATE
FROM RAW_FX_RATES r
WHERE r.RATE_DATE IS NOT NULL AND r.FROM_CURRENCY IS NOT NULL AND r.TO_CURRENCY IS NOT NULL AND r.FX_RATE IS NOT NULL AND r.FX_RATE > 0
QUALIFY ROW_NUMBER() OVER (PARTITION BY r.RATE_DATE, r.FROM_CURRENCY, r.TO_CURRENCY ORDER BY r._INGESTED_AT DESC, r._BATCH_ID DESC) = 1
