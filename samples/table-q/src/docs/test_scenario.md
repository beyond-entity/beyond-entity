# TableQ manual test scenarios

Beyond Entity project: **Table Q By Codex**. Database: **table_q_by_code** only. This guide is a manual acceptance checklist, not a claim that every scenario or every variation has been tested automatically.

## 1. Start the application

From Terminal:

```sh
cd /Users/yoojongseok/projects/vb/table_q_codex/src
npm ci
npm run setup
npm run seed
npm run dev
```

The existing PostgreSQL container `tableq-postgres` must be running. Setup preserves an existing `.env`; seed preserves an existing seeded administrator. The database schema and the second device-fault migration have already been applied on this PC.

- Development UI: http://127.0.0.1:5174
- API/production UI: http://127.0.0.1:3100 (production UI requires `npm run build`)
- API health: http://127.0.0.1:3100/api/health
- Keep the worker running for delivery, device simulation and offline reconciliation. `npm run dev` starts all three processes; Ctrl+C stops that command's processes.
- Port 3000 is used by an existing process on this PC; TableQ uses 3100 and does not stop that process.
- Sign-in credentials are `SEED_EMAIL` and `SEED_PASSWORD` in private `src/.env`. The password is deliberately not copied into this document.
- Initial **demo** tablet PIN: `246810`. Set a new PIN in store settings when desired.
- Initial demo stores: Gangnam Flagship (GN01), Seongsu Kitchen (SS02), Hannam Dining Room (HN03). Each has a published 12-table layout, policy, open session and registered simulator devices. Their queues start empty.

For a built application with real offline reload support, stop `npm run dev`, then run:

```sh
npm run build
npm start
```

In a second Terminal in `src`, run `npm run worker`. Open http://127.0.0.1:3100 and load the tablet online before disconnecting. The service worker caches the built application and bundled font. It does not cache authenticated API responses.

Use one consistent hostname/port per browser workflow: IndexedDB, session storage and service workers are origin-specific. Device credentials and owner tickets survive reload in the same tab, but are not intended to survive closing all tabs or clearing browser storage. Preserve `.env`; replacing its cryptographic keys makes existing digests/ciphertexts unusable.

## 2. Record results

For each case record: date/build, browser/device, store, steps, expected result, actual result, PASS/FAIL, screenshot, and relevant ticket/call/job ID if troubleshooting. Never include passwords, device/partner/owner tokens or raw location coordinates in shared test evidence.

The automated evidence is recorded separately in implementation_and_test_evidence.md in Beyond Entity. The checklist below remains for your manual review even where an automated happy path has passed.

## T01 — Sign-in and store scope

1. Open `/login`. Try an incorrect password, then use the seeded credentials.
2. Confirm head office shows the three demo stores and aggregate waiting counts.
3. In **Accounts & partners**, create a manager assigned to one store. Save the returned account ID for the disable test.
4. In a separate browser profile, sign in as that manager.
5. Confirm only the granted store appears. Attempt an ungranted store's settings URL or metrics API: access must be denied.
6. As head office, disable the manager by account ID. Refresh the manager's page.

Expected: invalid credentials do not sign in; disabled sessions cease working; manager access does not expand to other stores. Administrator writes are audited. The UI may still show navigation to a restricted administrator function, but its API must deny it.

## T02 — Enroll and unlock the store tablet

1. From head office choose **Manage** for Gangnam Flagship.
2. Select **Open store tablet**. This rotates that device's credential for this browser tab.
3. Enter an incorrect PIN, then `246810` (unless changed).
4. Confirm queue/tables load, the tablet heartbeat becomes online and the layout contains 12 tables.

Expected: PIN alone cannot enroll an unknown browser/device; the existing enrolled tablet must be the open session's owner. Opening the same device in a second tab through settings rotates its credential and invalidates the old tab's credential. Use separate device types or browser profiles when comparing kiosk and tablet.

## T03 — Staff registration and a read-only watch code

1. In tablet **Add group**, choose 2 people, leave Window seat off, and select Arrived already.
2. Select **Add to queue and issue watch code**.
3. Record the ticket and four-digit code; select **Back to queue**.
4. In a separate customer tab open `/w`, enter the code and select **Watch my queue**.

Expected: one group appears; the customer sees the same ticket, party size and groups-ahead count. The watch page has no defer/cancel control. Invalid/expired codes are rejected; code exchange is rate limited. No customer name/phone is collected. A watch code never grants ownership of the ticket.

## T04 — Table eligibility, arrival and queue order

1. Add several groups with different sizes and window preferences. Include an unconfirmed group by clearing Arrived already.
2. In **Queue**, use **Call next eligible**.
3. Confirm the earliest arrived group that fits a free table is called, with a compatible table held.
4. Confirm an unconfirmed group is skipped; use **Confirm arrival** as staff and retry after freeing an appropriate table.
5. Fill the only fitting tables for a larger/window group and verify a later fitting group can be called.

Expected: no incompatible assignment or double occupancy. Customers' groups-ahead counts include earlier waiting groups competing for a table they could also use, not simply every earlier group. Cached table order preserves row position from the manager's layout.

## T05 — Call, recall, seat, clear and stale actions

1. Call an arrived group and watch its customer screen change to **Now**.
2. Select **Recall**. Check a separate delivery event/job is created without moving the original grace deadline.
3. Select **Seat**, then open **Tables** and clear that exact occupied table.
4. Attempt a stale repeated seat/clear request using an old call/allocation identity.

Expected: call holds a fitting table; seating occupies it; clearing frees it immediately. Old call/allocation actions are rejected and cannot affect a newer occupant. Watch access ends when the ticket is seated or otherwise terminal. Owner access may still read the terminal ticket until expiry.

## T06 — Deferral, cancellation and no-show

1. Call a group and choose **Defer**. Verify it returns to the back of the waiting queue and releases its hold.
2. Cancel a waiting/called group; confirm it leaves the active queue and releases any hold.
3. Call another group and immediately choose **No-show**: expect a grace-period rejection.
4. Wait the configured five-minute grace, then mark No-show.
5. Open store **Figures** for the period.

Expected: deferral history increments; no-show is counted separately from cancellation; seated groups cannot be cancelled. No-show never occurs automatically merely because a network request was delayed.

## T07 — Phone join and arrival confirmation

1. Keep the owner tablet connected and active.
2. Open `/stores` in a customer browser, choose Gangnam Flagship, choose party/window preference and permit geolocation.
3. To test the nearby path on a desktop, use Chrome DevTools → More tools → Sensors → custom location: latitude **37.4979**, longitude **127.0276**, with a fresh accurate reading. These are the seeded store coordinates, not a user's location.
4. Join within the default 300-metre radius. Verify arrival is initially unconfirmed even when entering through the store QR.
5. On the tablet select **Show arrival code**. Within its one-minute lifetime enter it on the owner's customer screen while within 50 metres.
6. Test an out-of-radius position, denied geolocation, stale code, and an owner tablet with no heartbeat for over 30 seconds.

Expected: valid nearby join succeeds and returns owner actions; coordinates are not stored as customer history. Invalid location/code is denied. Remote joins pause when the owner tablet is stale. QR scanning alone does not prove arrival.

## T08 — Kiosk and ticket-printer failure

1. From store settings in a separate tab/profile, choose **Open kiosk**.
2. Choose party size/window preference and check in.
3. Verify arrival is confirmed, a watch code is issued and no owner token is shown.
4. In manager **Devices**, simulate printer **Paper out**. In the kiosk choose **Print / retry ticket**.
5. Restore the printer to **None** and retry the same ticket.

Expected: printing fails visibly while registration remains valid. Retrying the same print job does not create another queue group or simulator effect. The simulator log shows the completed print effect. Browser print output is a local demonstration, not a real hardware integration claim.

## T09 — Durable delivery, retries and device health

1. In manager **Devices**, set the call bell fault to Adapter error or Offline.
2. Call an arrived group. Refresh **Delivery & simulator log**.
3. Observe customer-notification and bell jobs separately, with status and attempt count.
4. Restore the bell before five attempts are exhausted. Keep the API and worker running.
5. Set a simulator device Offline and wait over 30 seconds plus the ten-second check interval. Then restore it.

Expected: failed effects retry with bounded backoff; ordering is maintained within each delivery lane. After exhaustion the job is failed and a new deliberate Recall creates new delivery jobs. A stale device is visible in health and produces an unresponsive fault transition; a later heartbeat records recovery. Simulator deduplication is durable in SQLite across worker restart. Real SMS/bell/printer delivery guarantees are not established by this test.

## T10 — Simulated store outage, reload and automatic replay

1. With an initialized tablet snapshot and an arrived waiting group, select **Simulate connection loss**.
2. Call, seat and clear locally. Confirm the pending-action count becomes three.
3. Reload the same tablet tab. Confirm the local journal/cache and pending count remain.
4. Select **Reconnect store** and keep the worker running.
5. Wait until the pending count clears; verify canonical queue/table state matches the three actions.

Expected: no new remote state appears while the tablet is disconnected; only call/seat/clear remain enabled. Each local operation journals atomically before showing success. Replay follows device sequence and retains original validated physical times, including the original call grace. Reconnect does not replay an already performed local bell signal. Subsequent sessions/cache reloads recover the next sequence from the server cursor.

## T11 — Actual browser network outage (built application)

1. Use the built application at port 3100, not Vite's development server. Open and unlock the tablet online and wait for the snapshot to load.
2. In browser developer tools switch the network to Offline. Reload the tab.
3. Confirm the application shell loads from the service worker and the tablet uses IndexedDB.
4. Call, seat and clear locally.
5. Restore the network. The browser's online event should reconnect and the worker should reconcile the journal automatically.

Expected: the same pending actions survive real offline reload. No API request is issued inside the IndexedDB commit transaction. First-ever offline access without an initialized snapshot is not supported; browser storage eviction is not guaranteed recoverable.

## T12 — Synchronization conflict and manager review

1. With a saved tablet snapshot, simulate disconnection and perform local call/seat/clear.
2. Before reconnecting, change the canonical queue from another authorized route/device so the saved base version no longer matches. Do not rotate the original tablet credential merely to create the conflict; doing so changes authentication as well.
3. Reconnect. Check that the first incompatible command blocks the application cursor and the tablet shows manager review is required.
4. Open manager **Overview → Offline review**. Inspect actual physical occupancy; clear canonical occupancy through its normal operation when appropriate, then confirm reviewed.

Expected: physical seat/clear evidence is preserved and affected tables are quarantined. Ordinary calling must not allocate quarantined tables. Resolution cannot release a later occupant by applying an old clear or resurrect a cancelled ticket. Rejected/manager-resolved commands allow the contiguous cursor to advance; no latest-timestamp automatic merge is used. This is an advanced manual scenario; use the automated conflict test if a second authorized mutation source is inconvenient.

## T13 — Layout, policy, store and session administration

1. Register a new store in head office; verify it appears without editing source code.
2. In its settings create a draft layout, add rows/tables, and publish. Duplicate table numbers within the layout must block publication; published layouts cannot be edited.
3. Create a shared policy template, marking some fields fixed. Publish a store policy with allowed overrides; attempt to override a fixed field.
4. Add opening periods and register a tablet/device. Assign a tablet PIN.
5. Open a session with a published layout and policy. Verify an existing open session continues using its pinned versions after newer versions are published.
6. Drain the active queue/tables, resolve all server sync conflicts, and confirm the owner tablet is connected with zero local pending actions before closing the session.

Expected: scoped writes are audited; immutable versions remain unchanged; fixed policy overrides are rejected. Closing with known active queue/occupancy/sync work is blocked. Operators must also confirm the tablet has no unuploaded work; the server cannot infer an unseen local journal during a network partition.

## T14 — QR posters and rotation

1. In head office **QR codes**, inspect the real QR and store name/code.
2. Scan/open the URL; verify it resolves to the correct store join screen.
3. Print the poster using the browser print dialog.
4. Regenerate and verify the old QR URL is rejected and the new one works.

Expected: QR codes encode actual join URLs; they are not decorative mock patterns. Rotation never changes arrival confirmation by itself. QR scan analytics and alternative poster export sizes are not part of this implementation baseline.

## T15 — Reporting and partner privacy

1. Complete some joins, calls, deferrals, no-shows, seating and clearing actions, plus a device fault/recovery.
2. Open **Figures**, choose a period and inspect counts, mean wait, UTC hourly activity and fault transitions.
3. In head office **Accounts & partners**, issue a partner credential. Keep the token private.
4. Use a REST client for `GET /api/partners/v1/stores/{store_id}/status`, with `Authorization: Bearer <partner token>`.
5. Inspect response fields; test another organization's store and exceed the 60-request/minute partner limit.

Expected: no customer identifiers, individual party data or table layout in partner output. Response includes store_id, store_status, waiting_count, as_of and data_fresh. Reports distinguish joined cohorts and event periods; hourly activity is not historical queue-depth stock. Empty hours are displayed as zero. Fault transitions are not uptime percentages.

## T16 — Replays, concurrency and restart checks

Run the automated API suite (`npm test`) for repeatable checks of concurrent registrations, identical/different-body idempotency reuse, scope denial, immutable publication, call/allocation guards and offline conflicts. Repeating a completed request with the same Idempotency-Key must replay its typed result; changing arguments with the same key is rejected. Newly issued secrets have short encrypted replay windows and do not gain longer lifetime through replay.

For a manual worker restart: call a group, stop only the worker, observe queued work, restart it and verify eventual processing. Real network timeout/crash timing beyond the automated cases remains a manual exploration, not a claimed exhaustive failure test. Do not clear the database or replace `.env` between these steps.

## Automated checks available

```sh
cd /Users/yoojongseok/projects/vb/table_q_codex/src
npm test
npm run build
# Start npm run dev in another Terminal; Chrome must be installed.
npm run test:browser
```

API tests use temporary, isolated organizations in table_q_by_code and clean their PostgreSQL rows afterward. Browser tests create isolated demo organizations, take screenshots into src/data, and clean their database rows. Simulator SQLite logs may retain test effect evidence. Do not run test suites while recording a pristine demo log if those extra simulator entries would be confusing. Exact current pass counts and remaining qualification limits belong in implementation_and_test_evidence.md.
