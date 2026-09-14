# TableQ

React/TypeScript application, Fastify API, PostgreSQL-backed queue and a separate Node worker. Source contracts come from Beyond Entity project **Table Q By Codex**. The application uses only `table_q_by_code`.

## Run on this PC

Node 24.4+ and the existing `tableq-postgres` Docker container are required.

```sh
cd /Users/yoojongseok/projects/vb/table_q_codex/src
npm ci
npm run setup
npm run seed
npm run dev
```

Open **http://127.0.0.1:5174**. API: **http://127.0.0.1:3100/api/health**. Port 3000 belongs to an existing application and is left alone.

The private `.env` contains `SEED_EMAIL` and the generated `SEED_PASSWORD`. Initial demo tablet PIN: **246810**. Head office → Manage a store → Open store tablet → enter the PIN. Use a separate tab/profile for the kiosk or customer. Opening a device from settings rotates its credential; older tabs using that device must be enrolled again.

`setup` preserves an existing `.env` and can obtain the existing PostgreSQL password from the local container without printing it. `seed` is non-destructive and leaves an existing seeded administrator unchanged. Keep `.env` and its cryptographic keys; do not commit or regenerate it against existing data. Demo stores start with empty queues and 12-table layouts.

## Built app and real offline reloads

Stop `npm run dev` first if it is using port 3100.

```sh
npm run build
npm start
```

In a second Terminal in this directory:

```sh
npm run worker
```

Open **http://127.0.0.1:3100**. The built app includes a service worker and locally bundled Archivo font. Load/unlock a tablet online before testing a real offline reload. Browser data is scoped to origin; do not switch ports mid-scenario. Development mode supports the simulated outage switch, while the built app supports cached page reloads during actual outages.

The server binds to loopback by default. Physical phones on another machine need deliberate HTTPS/origin/network configuration; localhost geolocation and service-worker behavior does not imply a ready remote deployment.

## Source map

- `server/app.ts`: all 56 designed HTTP routes, validated request bindings and supplemental UI/simulator endpoints.
- `server/queue.ts`: queue rules, session transactions, command deduplication/replay, call/hold/seat/clear and outbox enqueue.
- `server/security.ts`: scoped accounts/devices/tickets, secure-cookie settings, Argon2id, HMAC, AEAD and shared rate limits.
- `server/admin.ts`: accounts, stores, immutable layouts/policies, devices, session administration and conflict review.
- `server/sync.ts`: immutable offline intake, ordered reconciliation and quarantine.
- `server/delivery.ts`, `server/worker.ts`, `server/simulator.ts`: delivery leases/retries/receipts, scheduled recovery, heartbeats and SQLite simulator effects.
- `web/main.tsx`, `web/offline.ts`: customer/kiosk/tablet/head-office/manager screens and explicit API → browser context → IndexedDB handoffs.
- `contracts/beyond-entity.json`: MCP-exported design lineage; runtime code binds parameters and guards explicitly rather than executing processor-name SQL as physical tables.
- `../db/migrations/0001_beyond_entity_schema.sql`: applied initial PostgreSQL schema.
- `db/migrations/0002_device_fault_transition_identity.sql`: applied correction allowing timeout/recovery transitions associated with the same last heartbeat.
- `docs/test_scenario.md`: manual acceptance guide, also saved in Beyond Entity as `test_scenario.md`.

No automatic migration runs on server startup. Both migrations are already applied on this PC; do not reapply raw initial DDL to existing tables. Future schema changes need a new migration and matching Beyond Entity update.

## Verify

```sh
npm test
npm run build
# Run npm run dev separately before the browser suite.
npm run test:browser
```

Browser tests use installed Chrome. PostgreSQL integration tests create and clean isolated organizations. Test screenshots and simulator files live under ignored `data/`; Playwright reports are ignored too.

This is a local sample implementation. Browser watch updates use SSE with polling fallback. Delivery effects are persisted simulators, not contracted SMS or real printer/bell integrations. Security labels in PostgreSQL remain metadata; application controls enforce scoped access and secret handling. Production retention, remote hosting/TLS, external-provider guarantees, stress capacity, exhaustive crash timing and final product sign-off are not established by these tests. Before closing a session, staff must confirm the owner tablet has no unuploaded local work as well as draining canonical state.
