# TableQ PostgreSQL schema

The complete 37-table PostgreSQL design from Beyond Entity was applied to `table_q_by_code` on 2026-09-08. The four IndexedDB and two simulator SQLite entities belong to other runtimes.

Connect:

```sh
/Applications/Docker.app/Contents/Resources/bin/docker exec -it tableq-postgres psql -U tableq -d table_q_by_code
```

Inside psql, use `\dt public.*` to list tables and `\d+ public.queue_groups` to inspect a table.

`migrations/0001_beyond_entity_schema.sql` is the initial, transactional migration, already applied. Do not reapply it to this database. It refuses other database names; do not drop existing tables to rerun it. Future changes need a new versioned migration.

Includes 334 columns, 37 primary keys, 70 foreign keys, 44 CHECK constraints, 32 unique rules (five partial unique indexes), seven other indexes, the snapshot revision default, and the deferred command-completion trigger. CHECK expressions come from the canonical Beyond Entity stage guides, including the later owner_token replay-kind extension. Security classification comments document intended protections; they do not implement application authorization, cryptography, logging controls or production role separation.

Verification (no password is embedded):

```sh
/Applications/Docker.app/Contents/Resources/bin/docker exec -i tableq-postgres psql -X -w -U tableq -d table_q_by_code -q < db/tests/schema_smoke.sql
/Applications/Docker.app/Contents/Resources/bin/docker exec -i tableq-postgres psql -X -w -U tableq -d table_q_by_code -At -v ON_ERROR_STOP=1 < db/tests/catalog.sql > /private/tmp/tableq_catalog.json
python3 db/tests/verify_schema.py /private/tmp/tableq_catalog.json
```

Run these commands from the repository root. Smoke tests create fixture rows within a rolled-back transaction. They check invalid coordinates, missing account references, duplicate open sessions, the revision default, rejection of unfinished commands and acceptance after final command completion. Catalog verification checks every column, key mapping, index and security comment against `schema_manifest.json`. These are schema tests, not API, browser, concurrency or end-to-end tests.
