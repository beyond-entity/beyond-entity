# Implementation and test evidence

Recorded 2026-09-08 for Beyond Entity project Table Q By Codex.

## Implemented local sample

Source root: `/Users/yoojongseok/projects/vb/table_q_codex/src`.
React/TypeScript browser application, Fastify/Node API, a separate Node worker, PostgreSQL database `table_q_by_code`, Dexie/IndexedDB browser cache and journal, and SQLite simulator effect journals are implemented. All 56 modeled HTTP routes have explicit handlers. Shared general processors are functions; five schedulers execute in the worker; eight webapp tasks execute in the browser. They are not additional HTTP servers.

The 37 PostgreSQL tables and both schema migrations are applied on this PC. Four IndexedDB and two SQLite entities have runtime storage definitions. API responses pass through browser context before atomic IndexedDB persistence. Snapshot row ordering and server-assisted recovery of the next device sequence are included. Device fault transition uniqueness includes fault_code, allowing timeout and recovery against one heartbeat sequence.

## Source evidence

| Scope | Source |
| --- | --- |
| HTTP bindings, validation and public projections | src/server/app.ts |
| Authentication, scoped permissions, Argon2id, HMAC and AEAD | src/server/security.ts |
| Queue transitions, transactions, idempotency and secret replay | src/server/queue.ts |
| Administration, policies, immutable layouts and reports | src/server/admin.ts |
| Offline reconciliation, ordering and quarantine | src/server/sync.ts |
| Delivery, retry, device health and scheduled work | src/server/delivery.ts; src/server/worker.ts |
| Durable simulated effects | src/server/simulator.ts |
| Customer, kiosk, tablet, HQ and manager screens | src/web/main.tsx |
| Browser cache, snapshot handoff and offline journal | src/web/offline.ts; src/web/api.ts |

## Verification

- `npm test`: **10/10 passed**, real PostgreSQL integration with isolated organizations cleaned after tests. Covers authentication, wrong-store and CSRF denial, queue concurrency, idempotency including encrypted watch-code replay, customer permissions/location gates, offline reconciliation and conflict handling, administration, reports, device faults, delivery and cleanup.
- `npm run test:browser`: **3/3 passed**, installed Chrome. Covers HQ/tablet/watch/manual offline journey, customer search/kiosk, and built-app real network outage with cached reload and automatic reconciliation.
- `npm run build`: TypeScript and production browser/PWA build passed.
- Screenshots and execution coverage are under ignored `src/data/`. Coverage records identify exercised handlers, not exhaustive branch coverage.

Native processor implementation status records describe the local sample. Test status TEST_PASSED_WITH_WARNING means these shared integration/browser suites passed, while per-processor exhaustive failure timing, hardware/provider qualification and manual product acceptance remain outstanding. A modeled SQL transformation is a lineage specification; application code binds its data and enforces rules explicitly. Tests do not prove every individual transformation independently.

## Run and manual acceptance

Run npm from `src/`: `npm ci`, `npm run setup`, `npm run seed`, `npm run dev`. UI port 5174; API port 3100. The generated local credentials are in private `src/.env`; do not publish secrets in this project. For real offline reload, build and run `npm start` plus `npm run worker`, then open port 3100. Browser storage belongs to one origin.

Use `test_scenario.md` for manual acceptance. Its scenarios are pending user execution; automated tests do not mark all manual steps passed. Real SMS, printer and bell services are simulated. Production TLS/hosting, stress capacity, retention qualification, exhaustive crash timing and final UI sign-off remain unverified. Staff must verify no unuploaded local work before closing a session. Browser owner/device credentials survive same-tab reload but not clearing session storage or closing the tab.
