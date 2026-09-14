# Snowflake Enterprise ELT

Implementation of the Beyond Entity design in `snowflask_sample.bemdl`. Six source
systems land into Snowflake RAW, conform in CORE, aggregate into ANALYTICS marts,
and surface on four BI dashboards.

**Beyond Entity is the source of truth.** Model IDs, column contracts, schedules,
PII classification and lineage live in the design, not here. Read
`overall_architecture.md` in the project documents before changing anything, and
keep design changes in the MCP workflow -- never edit the `.bemdl` directly.

## Status

| Pipeline | Processor | Status |
| --- | --- | --- |
| Oracle Customer Ingestion | `proc_4osn63QZFi` | **Implemented** |
| Resolve Customer Identity | `proc_j3HyTdoXBh` | **Implemented** |
| Build Core Customer | `proc_PASXcCWvuz` | **Implemented** |
| FX Rate File Ingestion | `proc_PzWyOakCVL` | **Implemented** |
| Build Core FX Rate | `proc_AsyyNwdM2X` | **Implemented** |
| Oracle Order Ingestion | `proc_U9h1dVHj2j` | **Implemented** |
| Assert FX Rate Coverage | `proc_UK8fvT1Asw` | **Implemented** |
| Build Core Order | `proc_3ASyTmTu51` | **Implemented** |
| Build Core Payment | `proc_3Ddf5VeRop` | **Implemented** |
| PostgreSQL Subscription Ingestion | `proc_EMd95vDcg4` | **Implemented** |
| MySQL Support Ingestion | `proc_a9NaJ21I2p` | **Implemented** |
| Build Core Support Interaction | `proc_u5kiETSFgV` | **Implemented** |
| Build Core Subscription | `proc_VlepSlkKoH` | **Implemented** |
| Partner File Ingestion | `proc_a5OA9FY6dc` | **Implemented** |
| Build Core Campaign | `proc_7x7b2hFPxu` | **Implemented** |
| Build Customer 360 | `proc_qi2OyAuAAl` | **Implemented** |
| Build Monthly Revenue | `proc_5WN7LCvuxV` | **Implemented** |
| Build Campaign Performance | `proc_EkjDDx59xe` | **Implemented** |
| Build Customer Support Health | `proc_tUDyM0IkCx` | **Implemented** |
| Build Customer Lifetime Value | `proc_AR6brQlFmY` | **Implemented** |
| Build Subscription Retention | `proc_F3jEWvf4lM` | **Implemented** |
| 4 BI dashboards | | Out of scope — see below |

The model's `implementation_status` and `test_status` fields are authoritative, not
this table.

## Run the validation

```bash
for t in tests/*.py; do python3 "$t"; done
```

252 tests, standard library only, including end-to-end tests that drive the
CORE builds from RAW tables populated by the real ingestion. They execute the pipelines against in-memory
SQLite fixtures and check the modeled contracts. They contact no Oracle or
Snowflake resource.

## Layout

- `sql/ddl/` -- table DDL generated from the modeled entities.
- `sql/ingestion/<pipeline>/`, `sql/core/<pipeline>/` -- the canonical modeled
  statement for each transformation, named for its transformation id.
- `sql/tasks/` -- Snowflake task DDL for processors whose modeled `runs_in` is a
  Snowflake task.
- `pipelines/` -- the executable pipelines.
- `dags/` -- Airflow DAGs for processors whose modeled `orchestrator` is Airflow.
- `tests/` -- contract and behaviour validation.

## Two shapes of pipeline

**Cross-system ingestion** (source -> RAW) is modeled as one `INSERT ... SELECT`
so column-level lineage is expressible, but cannot run as one statement: the
SELECT is in Oracle and the INSERT is in Snowflake. `pipelines/contract.py` parses
the modeled text and derives an extract of the source columns plus a load of all
target columns, with ingestion metadata bound at load time. Deriving them means
the executed column list cannot drift from the modeled lineage.

**CORE builds and file ingestion** are single-database, so the modeled SQL executes
verbatim through `pipelines/sql_runner.py`. File ingestion belongs in this group
because Snowflake reads the landing zone stage itself -- Airflow schedules it but
does not move the data. `pipelines/snowflake_sqlite.py` translates the SQL for the
test harness only, and refuses anything it cannot translate faithfully rather than
approximating. That refusal is what caught the `TO_NUMBER` defect below.

## Bad rows in delivered files

Plain `TO_DATE` and `TO_NUMBER` **raise** in Snowflake, so one malformed row would
abort an entire daily file load. Every file ingestion uses the `TRY_` forms, and
rejection is two-tier:

- a row whose **grain key** will not parse is rejected at ingestion and counted in
  `landing_file_manifest.rejected_row_count` -- it cannot be stored at the table's
  grain at all;
- a row whose **measure** will not parse lands with a null and is dropped at the
  CORE boundary, where it stays countable in RAW.

Currency codes are normalized at the ingestion boundary, not in CORE: a currency
code is an identifier, not a business fact, and letting `usd` and `USD ` both
through would silently split every revenue join.

## Windows and watermarks

There is no watermark table. Ingestion transformations take `:window_start` and
`:window_end` as INPUT ports supplied by the Airflow data interval, so the
orchestrator already owns run-window state. Windows are half-open, so adjacent
runs neither duplicate nor drop a row.

The one exception is subscription events, which use an `event_id` high-water mark
because the stream is immutable and an id mark cannot miss a late-written event.
That mark is read from `MAX(EVENT_ID)` on the target itself -- still one copy of
the state, not a second table.

## RAW is append-only; CORE deduplicates

RAW tables hold one row per source *version*, not per record -- hence no primary
keys. A changed record appears again with a new `_BATCH_ID`. Collapsing versions
is CORE's job, and it is load-bearing: a CORE build that joins a RAW table without
reducing it to one row per target key fans out across every historical version and
inflates every downstream mart.

Identity resolution deduplicates on the *source customer reference*, not the source
row key, for a second reason on top of versioning: one customer holds many
subscriptions and raises many tickets.

## The enterprise customer key is the spine

`CUSTOMER` is built from `CUSTOMER_IDENTITY_MAP`, not from Oracle. Every resolved
enterprise customer key gets a row, whichever system discovered it; Oracle
contributes name, phone, country, status and first-seen when that customer exists
there, and those columns are null with `CUSTOMER_STATUS = 'UNKNOWN'` otherwise.
Customers known only to the subscription, support or partner systems therefore
reach `CUSTOMER_360`.

The `SOURCE_SYSTEM = 'ORACLE_SALES'` predicate lives in the LEFT JOIN's ON clause.
Moving it to WHERE turns the LEFT JOIN back into an inner join and silently
restores Oracle-only membership.

## PII

Ingestion carries `pii_level` 3 columns across a system boundary unmasked, which is
why RAW is access-restricted. `CARD_LAST_FOUR` and `support_interactions.note_text`
are never ingested. Raw email stops at CORE; `EMAIL_HASH` (SHA-256) is the only
customer identifier that crosses into ANALYTICS. Pipelines log and return counts
and identifiers only, never row values.

## Known limitations

- Records with a null or blank email cannot be resolved at all -- email is the only
  matching key -- and are excluded from the crosswalk.
- `FIRST_SEEN_AT_UTC` is null for customers with no Oracle record. A cross-system
  first-seen would need the subscription, support and partner timestamps, each with
  its own timezone assumption.
- `:oracle_server_timezone` is `'UTC'` for this sample -- an explicit configuration
  assumption, not a session setting. **Verify it against the real Oracle system**
  before any production deployment; if Oracle stores server-local time, every
  `FIRST_SEEN_AT_UTC` is wrong by that offset.

## A missing FX rate fails the revenue build

A required exchange rate that is unavailable is a **data quality failure**. The
affected revenue rows are not dropped (revenue would be silently understated) and
not published with null USD amounts (unresolved numbers are indistinguishable from
real ones on a dashboard). The build fails and publishes nothing.

`Assert FX Rate Coverage` rebuilds `FX_COVERAGE_GAP` with every currency/date pair
the landed revenue rows require and `FX_RATE_DAILY` lacks. The gap is modelled as a
**table rather than an exception** so the failure is inspectable: which rates are
missing, for which source, and how many rows they block. `FxCoverageError` carries
those rows, because failing is only useful if someone can see which rates to obtain.

- **Blast radius is the revenue chain only.** A missing exchange rate says nothing
  about customer identity or support tickets, and those pipelines keep running.
- **USD needs no rate** and can never block revenue.
- **Payments are checked on their own settlement date**, not the order's -- a payment
  can settle days later, at a different rate, in a different currency.
- **Defence in depth:** `ORDER_AMOUNT_USD`, `FX_RATE_APPLIED` and
  `PAYMENT_AMOUNT_USD` are NOT NULL, so publishing an unresolved amount is
  structurally impossible even if the gate is bypassed.

The FX join must always carry the **whole** rate key -- currency, `TO_CURRENCY`, and
date. A join on currency alone matches every rate date in the table and multiplies
the row instead of converting it.

## Subscription MRR converts on the billing period start

This build was held back for a while with its FX defect unfixed, because the defect
could not be corrected independently: adding a `QUALIFY` would have collapsed the FX
fan-out onto one *arbitrary* rate date, turning an obvious explosion into a plausible
wrong number. A defect that multiplies rows announces itself; one that silently picks
a rate does not.

The decision, from the project owner: MRR converts on **`CURRENT_PERIOD_START`**,
because recurring revenue belongs to the period it covers rather than to an
operational timestamp such as creation or update time. `FX_RATE_APPLIED` and
`MRR_AMOUNT_SOURCE` are stored alongside `MRR_USD` so the conversion is reproducible
from the row, and `MRR_USD` is `NOT NULL`.

The FX coverage gate is now **per build**: `FX_COVERAGE_GAP.SOURCE_TABLE` says which
build a gap belongs to, so a missing subscription rate blocks the subscription build
and a missing order rate blocks the revenue build, neither blocking the other.

## The mart builds were multiplying their own numbers

Both mart statements joined several independent one-to-many facts to a single grain
and then aggregated. The joins multiply. In `Build Customer 360`, a customer with 3
orders, 2 subscriptions and 4 tickets produced 24 join rows, so `TOTAL_ORDERS` read
24, `TOTAL_ORDER_REVENUE_USD` was 8x the true figure and `CURRENT_MRR_USD` was 12x.
`Build Monthly Revenue` had the same shape.

Nothing about the output looked wrong. The numbers were plausible — just several
times too large. That is what made it the most damaging defect found here, and why
the tests for these two builds assert hand-computed totals rather than row shapes.

Both now aggregate each fact on its own — scalar subqueries in `CUSTOMER_360`,
separately staged contributions in `MONTHLY_REVENUE` — so no fact can inflate
another. The arithmetic fix was held back until the three business definitions it
depends on were decided, because half-fixing it would have replaced an obvious
explosion with a believable wrong answer.

## Business rules are written down, not implied

Three definitions in this platform are decisions rather than consequences of the
data, and each is recorded as a named rule in `business_rules.md` in Beyond Entity.
The SQL implements a rule; it does not *constitute* one.

- **BR-1 — subscription lifecycle.** `ACTIVE` and `AT_RISK` are revenue-bearing;
  `TRIAL`, `PAUSED` and `CHURNED` are not. Precedence is
  `ACTIVE > AT_RISK > TRIAL > PAUSED > CHURNED`. `CURRENT_MRR_USD` sums *all* a
  customer's revenue-bearing subscriptions; the single lifecycle column takes the
  highest-precedence state. The build maps states to explicit ranks. The previous
  `MAX()` of the state string was the alphabet deciding: `MAX` of `ACTIVE` and
  `CHURNED` is `CHURNED`.
- **BR-2 — campaign spend.** The sum of daily acquisition cost across every cost
  date, each day converted at its own `COST_DATE` rate. Campaign spend now converts
  the same way everything else does: on the date the amount belongs to.
- **BR-3 — monthly revenue.** Orders report in the order month, payments in the
  settlement month, subscription MRR in the billing period month. Previously one
  `GROUP BY` driven by `ORDER_FACT` bucketed all three on the order month, so a
  subscription-only customer contributed zero recurring revenue for ever.
- **BR-4 — net lifetime value.** A customer nets off its *share* of the acquisition
  campaign's spend — the campaign's cost per acquisition — not the campaign's whole
  spend, which the old statement charged to every customer it acquired.
  `TOTAL_SUBSCRIPTION_REVENUE` is renamed `CURRENT_MRR_USD`, because MRR is a monthly
  run rate and the platform has no billing history from which to build a lifetime
  figure.
- **BR-5 — retention.** One row per cohort and plan. Retained means the
  revenue-bearing states, so a trialling or paused subscription is neither retained
  nor churned and the two counts deliberately do not add up to the cohort.

## The four dashboards are out of scope, deliberately

They are `webapp_task` processors — BI tool artifacts, not pipeline code — and the BI
tool has not been chosen, so they stay `DESIGNING` in the model rather than being
marked done. Every mart they read *is* built and tested.

The contract they inherit is recorded on the model in Beyond Entity, because three
parts of it are easy to render wrongly: `MONTHLY_REVENUE`'s three measures sit in
three different months and must never be summed into one figure; the campaign ratios
are `NULL` when not computable and must show blank, not zero; and a stacked chart of
retained against churned will not fill the cohort bar, which is correct.

## Two progress mechanisms in one processor

PostgreSQL Subscription Ingestion windows subscriptions on the Airflow data
interval but advances subscription events on an **`EVENT_ID` high-water mark** read
from `MAX(EVENT_ID)` on the target. The event stream is immutable, and an id mark
cannot miss a late-written event the way a time window can. Reading it from the
landed data rather than a watermark table keeps exactly one copy of the progress
state.

## Open questions

**Blocking the last two marts, with the project owner:**

- **What net lifetime value nets off.** `NET_LIFETIME_VALUE_USD` is order revenue minus the
  acquisition campaign's *whole* spend, so a campaign that acquired 100 customers subtracts
  its full spend from each of them. `CAMPAIGN_PERFORMANCE` already computes a cost per
  acquisition. Separately, `TOTAL_SUBSCRIPTION_REVENUE` is computed and then left out of the
  net — and it is `SUM(MRR_USD)`, a *current monthly* figure under a lifetime name. Lifetime
  subscription revenue would need a billing history this platform does not carry.
- **What `SUBSCRIPTION_RETENTION` is a table of.** It groups by lifecycle state *and* derives
  retention from lifecycle state, so every group holds one state and `RETENTION_RATE` can
  only ever be exactly 1.0 or 0.0. `COHORT_SIZE` is one state's slice of the cohort, not the
  cohort. Whether the grain is the cohort or a breakdown by state changes which table gets
  published — and "retained" as "not churned" counts trialling and paused subscriptions,
  which BR-1 treats as non-billing.


- FX coverage is modelled for orders, payments, subscriptions and campaign spend —
  every converted amount in the platform.
- A payment whose order was blocked is silently absent rather than reported, because
  the build inner-joins `ORDER_FACT`.
- `landing_file_manifest` is modeled as a file in the object-storage landing zone, but
  every modeled transformation writes it with `INSERT INTO` from Snowflake, which an
  object-storage ledger cannot support. No DDL is shipped for it, so this repository
  does not quietly assert an answer.
- `RAW_ORDER_ITEMS` and `RAW_SUPPORT_INTERACTIONS` both land and **nothing consumes
  either**. Build Core Support Interaction reads only `RAW_SUPPORT_TICKETS` despite
  its name. Whether line-item and interaction-level facts are wanted is a design
  question.
- `PAYMENT` has no source-amount or applied-rate column, so its USD figure is not
  reproducible from the row alone. `ORDER_FACT` keeps both.

## Limits

No Oracle or Snowflake resources were provisioned and no statement in `sql/` has
been executed against Snowflake. The DDL and task files are artifacts, not
migrations. Airflow connections, warehouse sizing, RAW access grants and secret
management remain deployment work. Never put credentials in model documents or in
this repository.
