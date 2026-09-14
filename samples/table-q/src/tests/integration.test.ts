import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { buildApp, contracts } from "../server/app";
import { pool, one, rows } from "../server/db";
import { seed } from "../server/seed";
import { uid, token, digest } from "../server/security";
import { reconcileBatch } from "../server/sync";
import {
  dispatchOne,
  maintenance,
  recovery,
  detectStaleDevices,
  heartbeat,
} from "../server/delivery";
import { setControl, effectHistory } from "../server/simulator";
let app: any,
  adminCookie: string,
  store: any,
  other: any,
  group: any,
  tablet: any,
  kiosk: any,
  watchCookie: string,
  watchGroup: string,
  watchCode: string;
const touched = new Set<string>(),
  origin = "http://localhost:5174";
const call = async (name: string, b: any = {}, headers: any = {}) => {
  touched.add(name);
  const ct = contracts.find((x) => x.name === name);
  let url = ct.metadata.path.replace(/\{([^}]+)\}/g, (_: any, k: string) => {
    assert.ok(b[k], k);
    return b[k];
  });
  const body = { ...b };
  for (const match of ct.metadata.path.matchAll(/\{([^}]+)\}/g))
    delete body[match[1]];
  if (ct.metadata.method === "GET")
    url +=
      "?" +
      new URLSearchParams(
        Object.fromEntries(
          Object.entries(body).map(([k, v]) => [k, String(v)]),
        ),
      );
  const res = await app.inject({
    method: ct.metadata.method,
    url,
    headers: { origin, ...headers },
    ...(ct.metadata.method === "GET" ? {} : { payload: body }),
  });
  return { status: res.statusCode, body: res.json(), cookies: res.cookies };
};
const ok = (r: any) => {
  assert.equal(r.status, 200, JSON.stringify(r.body));
  return r.body;
};
const ah = () => ({ cookie: adminCookie });
const dh = () => ({
  authorization: "Bearer " + tablet.token,
  "x-tablet-unlock": tablet.unlock,
  "idempotency-key": uid(),
});
before(async () => {
  process.env.SEED_PREFIX = uid().slice(0, 8) + "-";
  process.env.SEED_EMAIL = "integration-" + uid() + "@tableq.local";
  process.env.SEED_PASSWORD = token();
  await seed();
  app = await buildApp();
  const login = await call("sign_in_operator", {
    email: process.env.SEED_EMAIL,
    password: process.env.SEED_PASSWORD,
  });
  ok(login);
  adminCookie =
    "operator_session=" +
    login.cookies.find((x: any) => x.name === "operator_session").value;
  const boot = (
    await app.inject({
      method: "GET",
      url: "/api/admin/bootstrap",
      headers: ah(),
    })
  ).json();
  [store, other] = boot.stores;
  const d = store.devices.find((d: any) => d.device_kind === "tablet");
  const issued = ok(
    await call(
      "rotate_device_credential",
      { store_id: store.store_id, device_id: d.device_id },
      ah(),
    ),
  );
  tablet = { ...d, token: issued.device_token };
  tablet.unlock = ok(
    await call(
      "unlock_store_tablet",
      { pin: "246810" },
      { authorization: "Bearer " + tablet.token },
    ),
  ).unlock_token;
  const k = store.devices.find((d: any) => d.device_kind === "kiosk");
  kiosk = {
    ...k,
    token: ok(
      await call(
        "rotate_device_credential",
        { store_id: store.store_id, device_id: k.device_id },
        ah(),
      ),
    ).device_token,
  };
});
test("all 56 designed HTTP routes are registered; health and authentication work", async () => {
  assert.equal(contracts.filter((x) => x.type === "api_server").length, 56);
  for (const ct of contracts.filter((x) => x.type === "api_server"))
    assert.ok(
      app.hasRoute({
        method: ct.metadata.method,
        url: ct.metadata.path.replace(/\{([^}]+)\}/g, ":$1"),
      }),
      ct.name,
    );
  assert.equal(
    (await app.inject("/api/health")).json().database,
    "table_q_by_code",
  );
  assert.equal(
    (await call("read_store_snapshot_manifest", { store_id: store.store_id }))
      .status,
    401,
  );
  assert.equal(
    (
      await call(
        "read_store_snapshot_manifest",
        { store_id: other.store_id },
        dh(),
      )
    ).status,
    401,
  );
  const cross = await app.inject({
    method: "POST",
    url: "/api/auth/operator-session/logout",
    headers: { cookie: adminCookie, origin: "https://untrusted.example" },
    payload: {},
  });
  assert.equal(cross.statusCode, 403);
});
test("heartbeat, idempotent staff registration and concurrent queue numbering", async () => {
  ok(
    await call(
      "record_device_heartbeat",
      {
        store_id: store.store_id,
        device_id: tablet.device_id,
        heartbeat_sequence: Date.now(),
        device_time: new Date().toISOString(),
        fault_code: "none",
      },
      dh(),
    ),
  );
  const b = {
    store_id: store.store_id,
    party_size: 2,
    wants_window: false,
    arrived: true,
  };
  const h = dh();
  group = ok(await call("register_waiting_group", b, h));
  assert.deepEqual(ok(await call("register_waiting_group", b, h)), group);
  assert.equal(
    (await call("register_waiting_group", { ...b, party_size: 3 }, h)).status,
    409,
  );
  const responses = await Promise.all(
    Array.from({ length: 12 }, () => call("register_waiting_group", b, dh())),
  );
  const ids = responses.map((x) => ok(x).group_id);
  assert.equal(new Set(ids).size, 12);
  const duplicates = await rows(
    pool,
    "SELECT ticket_number,count(*) n FROM queue_groups WHERE store_id=$1 GROUP BY ticket_number HAVING count(*)>1",
    [store.store_id],
  );
  assert.equal(duplicates.length, 0);
});
test("watch-code exchange is read-only, call deduplication, delivery and seating/clear", async () => {
  const codeHeaders = dh();
  const issued = ok(
    await call("issue_watch_code", { group_id: group.group_id }, codeHeaders),
  );
  assert.deepEqual(
    ok(
      await call("issue_watch_code", { group_id: group.group_id }, codeHeaders),
    ),
    issued,
  );
  watchCode = issued.watch_code;
  const context = await call("create_customer_join_context");
  const browser = context.cookies
    .map((c: any) => c.name + "=" + c.value)
    .join("; ");
  const exchange = await call(
    "exchange_watch_code",
    { watch_code: watchCode },
    { cookie: browser, "idempotency-key": uid() },
  );
  ok(exchange);
  watchCookie = exchange.cookies
    .map((c: any) => c.name + "=" + c.value)
    .join("; ");
  const status = ok(
    await call(
      "get_ticket_status",
      { group_id: group.group_id },
      { cookie: watchCookie },
    ),
  );
  assert.equal(status.can_cancel, false);
  assert.equal(
    (
      await call(
        "cancel_waiting_group",
        { group_id: group.group_id },
        { cookie: watchCookie, "idempotency-key": uid() },
      )
    ).status,
    401,
  );
  const snap = ok(
    await call(
      "read_store_snapshot_manifest",
      { store_id: store.store_id },
      dh(),
    ),
  );
  const header = dh();
  const called = ok(
    await call(
      "call_next_group",
      { store_id: store.store_id, expected_state_version: snap.state_version },
      header,
    ),
  );
  assert.equal(called.group_id, group.group_id);
  assert.equal(
    ok(
      await call(
        "call_next_group",
        {
          store_id: store.store_id,
          expected_state_version: snap.state_version,
        },
        header,
      ),
    ).call_id,
    called.call_id,
  );
  await dispatchOne();
  await dispatchOne();
  const jobs = ok(
    await call(
      "read_call_delivery_status",
      { store_id: store.store_id, call_id: called.call_id },
      dh(),
    ),
  );
  assert.equal(jobs.length, 2);
  assert.ok(jobs.every((x: any) => x.job_status === "delivered"));
  ok(
    await call(
      "recall_waiting_group",
      { group_id: group.group_id, expected_call_id: called.call_id },
      dh(),
    ),
  );
  assert.equal(
    (
      await call(
        "mark_group_no_show",
        {
          group_id: group.group_id,
          expected_call_id: called.call_id,
          reason_code: "grace_elapsed",
        },
        dh(),
      )
    ).status,
    409,
  );
  ok(
    await call(
      "seat_called_group",
      { group_id: group.group_id, expected_call_id: called.call_id },
      dh(),
    ),
  );
  assert.equal(
    (
      await call(
        "get_ticket_status",
        { group_id: group.group_id },
        { cookie: watchCookie },
      )
    ).status,
    401,
  );
  const fresh = ok(
    await call(
      "read_store_snapshot_manifest",
      { store_id: store.store_id },
      dh(),
    ),
  );
  const ts = ok(
    await call(
      "read_store_table_snapshot",
      {
        store_id: store.store_id,
        state_version: fresh.state_version,
        sync_snapshot_revision: fresh.sync_snapshot_revision,
      },
      dh(),
    ),
  );
  const occupied = ts.find((t: any) => t.table_status === "occupied");
  ok(
    await call(
      "clear_occupied_table",
      {
        store_id: store.store_id,
        table_id: occupied.table_id,
        expected_allocation_id: occupied.allocation_id,
      },
      dh(),
    ),
  );
  assert.equal(
    (
      await call(
        "clear_occupied_table",
        {
          store_id: store.store_id,
          table_id: occupied.table_id,
          expected_allocation_id: occupied.allocation_id,
        },
        dh(),
      )
    ).status,
    409,
  );
  await recovery();
});
test("phone location gate, owner rights, arrival and kiosk code", async () => {
  const ctx = await call("create_customer_join_context");
  const cookie = ctx.cookies.map((c: any) => c.name + "=" + c.value).join("; ");
  const b = {
    store_id: store.store_id,
    party_size: 2,
    wants_window: false,
    latitude: 0,
    longitude: 0,
    location_accuracy: 5,
    location_time: new Date().toISOString(),
  };
  assert.equal(
    (await call("join_phone_queue", b, { cookie, "idempotency-key": uid() }))
      .status,
    403,
  );
  const owner = ok(
    await call(
      "join_phone_queue",
      { ...b, latitude: store.latitude, longitude: store.longitude },
      { cookie, "idempotency-key": uid() },
    ),
  );
  const h = {
    authorization: "Bearer " + owner.owner_token,
    "idempotency-key": uid(),
  };
  const arrival = ok(
    await call("issue_arrival_challenge", { store_id: store.store_id }, dh()),
  );
  ok(
    await call(
      "confirm_group_arrival",
      {
        group_id: owner.group_id,
        arrival_code: arrival.arrival_code,
        latitude: store.latitude,
        longitude: store.longitude,
      },
      h,
    ),
  );
  ok(
    await call(
      "cancel_waiting_group",
      { group_id: owner.group_id },
      { ...h, "idempotency-key": uid() },
    ),
  );
  const kg = ok(
    await call(
      "join_kiosk_queue",
      { store_id: store.store_id, party_size: 4, wants_window: true },
      { authorization: "Bearer " + kiosk.token, "idempotency-key": uid() },
    ),
  );
  assert.ok(kg.watch_code);
  assert.equal(kg.owner_token, undefined);
});
test("compatible ordered offline call/seat/clear preserves physical times", async () => {
  const snap = ok(
    await call(
      "read_store_snapshot_manifest",
      { store_id: store.store_id },
      dh(),
    ),
  );
  const groups = ok(
    await call(
      "read_store_queue_snapshot",
      {
        store_id: store.store_id,
        state_version: snap.state_version,
        sync_snapshot_revision: snap.sync_snapshot_revision,
      },
      dh(),
    ),
  );
  const ts = ok(
    await call(
      "read_store_table_snapshot",
      {
        store_id: store.store_id,
        state_version: snap.state_version,
        sync_snapshot_revision: snap.sync_snapshot_revision,
      },
      dh(),
    ),
  );
  const g = groups.find(
    (g: any) => g.group_status === "waiting" && g.arrival_confirmed,
  );
  const t = ts
    .filter(
      (t: any) => t.table_status === "free" && t.seat_count >= g.party_size,
    )
    .sort(
      (a: any, b: any) =>
        a.seat_count - b.seat_count ||
        a.table_number.localeCompare(b.table_number),
    )[0];
  const callId = uid(),
    allocation = uid();
  let previous = new Date();
  for (const [i, operation] of ["call", "seat", "clear"].entries()) {
    const at = new Date();
    const b = {
      store_id: store.store_id,
      sync_command_id: uid(),
      device_id: tablet.device_id,
      session_id: snap.session_id,
      authority_epoch: snap.authority_epoch,
      device_sequence: i + 1,
      base_version: snap.state_version + i,
      layout_id: snap.layout_id,
      operation,
      group_id: g.group_id,
      call_id: callId,
      allocation_id: allocation,
      table_id: t.table_id,
      occurred_at: at.toISOString(),
    };
    ok(await call("receive_offline_command", b, dh()));
    await reconcileBatch();
    const result = ok(
      await call(
        "read_offline_command_status",
        {
          store_id: store.store_id,
          session_id: snap.session_id,
          after_sequence: i,
        },
        dh(),
      ),
    );
    assert.equal(result[0].sync_status, "applied", JSON.stringify(result));
    previous = at;
  }
  const alloc = await one(
    pool,
    "SELECT * FROM table_allocations WHERE store_id=$1 AND allocation_id=$2",
    [store.store_id, allocation],
  );
  assert.equal(alloc.released_at.toISOString(), previous.toISOString());
});
test("stale offline physical evidence quarantines a table and requires manager resolution", async () => {
  const snap = ok(
    await call(
      "read_store_snapshot_manifest",
      { store_id: store.store_id },
      dh(),
    ),
  );
  const g = await one(
    pool,
    "SELECT * FROM queue_groups WHERE store_id=$1 AND group_status='waiting' ORDER BY queue_sequence LIMIT 1",
    [store.store_id],
  );
  const t = await one(
    pool,
    "SELECT table_id FROM dining_tables WHERE store_id=$1 LIMIT 1",
    [store.store_id],
  );
  const b = {
    store_id: store.store_id,
    sync_command_id: uid(),
    device_id: tablet.device_id,
    session_id: snap.session_id,
    authority_epoch: snap.authority_epoch,
    device_sequence: 4,
    base_version: snap.state_version - 1,
    layout_id: snap.layout_id,
    operation: "clear",
    group_id: g.group_id,
    call_id: uid(),
    allocation_id: uid(),
    table_id: t.table_id,
    occurred_at: new Date().toISOString(),
  };
  ok(await call("receive_offline_command", b, dh()));
  await reconcileBatch();
  const conflict = await one(
    pool,
    "SELECT * FROM sync_conflicts WHERE store_id=$1 AND sync_command_id=$2",
    [store.store_id, b.sync_command_id],
  );
  assert.ok(conflict);
  const f = await one(
    pool,
    "SELECT * FROM physical_table_facts WHERE store_id=$1 AND sync_command_id=$2",
    [store.store_id, b.sync_command_id],
  );
  assert.equal(f.quarantine_active, true);
  ok(
    await call(
      "resolve_sync_conflict",
      {
        store_id: store.store_id,
        conflict_id: conflict.conflict_id,
        resolution_code: "physical_verified",
      },
      ah(),
    ),
  );
  await reconcileBatch();
});
test("administration publication, policy enforcement, reporting and scoped partner reads", async () => {
  const id = uid();
  ok(
    await call(
      "create_layout_version",
      { store_id: store.store_id, layout_id: id, version_number: 2 },
      ah(),
    ),
  );
  const row = uid();
  ok(
    await call(
      "add_layout_row",
      {
        store_id: store.store_id,
        layout_id: id,
        row_id: row,
        row_number: 1,
        row_label: "New row",
      },
      ah(),
    ),
  );
  ok(
    await call(
      "add_dining_table",
      {
        store_id: store.store_id,
        row_id: row,
        table_id: uid(),
        table_number: "T100",
        row_position: 1,
        seat_count: 4,
        is_window: false,
      },
      ah(),
    ),
  );
  ok(
    await call(
      "publish_layout",
      { store_id: store.store_id, layout_id: id },
      ah(),
    ),
  );
  assert.equal(
    (
      await call(
        "add_layout_row",
        {
          store_id: store.store_id,
          layout_id: id,
          row_id: uid(),
          row_number: 2,
          row_label: "Immutable",
        },
        ah(),
      )
    ).status,
    409,
  );
  const partner = ok(
    await call(
      "issue_partner_credential",
      { partner_id: uid(), partner_name: "Test partner" },
      ah(),
    ),
  );
  const status = ok(
    await call(
      "read_partner_store_status",
      { store_id: store.store_id },
      { authorization: "Bearer " + partner.partner_token },
    ),
  );
  assert.deepEqual(Object.keys(status).sort(), [
    "as_of",
    "data_fresh",
    "store_id",
    "store_status",
    "waiting_count",
  ]);
  const b = {
    store_id: store.store_id,
    from_time: new Date(Date.now() - 86400000).toISOString(),
    to_time: new Date(Date.now() + 1000).toISOString(),
  };
  for (const name of [
    "read_store_period_metrics",
    "read_wait_and_turnover_metrics",
    "read_hourly_store_activity",
    "read_device_fault_metrics",
  ])
    ok(await call(name, b, ah()));
  ok(await call("read_head_office_store_overview", {}, ah()));
  ok(
    await call("read_store_device_health", { store_id: store.store_id }, dh()),
  );
  const qr = uid();
  ok(
    await call(
      "rotate_store_join_qr",
      { store_id: store.store_id, qr_id: qr },
      ah(),
    ),
  );
  ok(await call("resolve_join_qr", { qr_id: qr }));
  ok(await call("find_stores", { query: "Gangnam" }));
});
test("device timeout/recovery, simulator retry and stable print effect deduplication", async () => {
  const printer = store.devices.find((d: any) => d.device_kind === "printer");
  await pool.query(
    "UPDATE device_health SET last_seen_at=now()-interval '1 minute' WHERE store_id=$1 AND device_id=$2",
    [store.store_id, tablet.device_id],
  );
  await detectStaleDevices();
  const fault = await one(
    pool,
    "SELECT * FROM device_fault_events WHERE store_id=$1 AND device_id=$2 AND fault_code='unresponsive'",
    [store.store_id, tablet.device_id],
  );
  assert.ok(fault);
  ok(
    await call(
      "record_device_heartbeat",
      {
        store_id: store.store_id,
        device_id: tablet.device_id,
        heartbeat_sequence: Date.now(),
        device_time: new Date().toISOString(),
        fault_code: "none",
      },
      dh(),
    ),
  );
  const printBody = { job_id: uid(), group_id: group.group_id };
  const print = async () =>
    app.inject({
      method: "POST",
      url: "/api/simulator/print",
      headers: dh(),
      payload: printBody,
    });
  const first = await print();
  assert.equal(first.statusCode, 200);
  const second = await print();
  assert.equal(second.json().receipt_event_id, first.json().receipt_event_id);
  setControl(printer.device_id, { fault_code: "paper_out", offline: false });
  const failed = await app.inject({
    method: "POST",
    url: "/api/simulator/print",
    headers: dh(),
    payload: { ...printBody, job_id: uid() },
  });
  assert.equal(failed.statusCode, 503);
  setControl(printer.device_id, { fault_code: "none", offline: false });
});
test("remaining administrator workflows enforce grants and immutable policy controls", async () => {
  const newStore = uid();
  ok(
    await call(
      "create_store",
      {
        store_id: newStore,
        store_code: "TEST-" + uid().slice(0, 8),
        store_name: "New Test Restaurant",
        address: "Test address",
        time_zone: "Asia/Seoul",
        latitude: 37.5,
        longitude: 127,
        contact_phone: "01000000000",
        contact_email: "test@example.test",
      },
      ah(),
    ),
  );
  const template = uid();
  ok(
    await call(
      "create_hq_policy_template",
      {
        template_id: template,
        version_number: 2,
        join_radius_metres: 300,
        arrival_radius_metres: 50,
        call_grace_seconds: 300,
        allow_join_override: true,
        allow_arrival_override: false,
        allow_grace_override: false,
      },
      ah(),
    ),
  );
  const policy = uid();
  const p = {
    store_id: other.store_id,
    policy_id: policy,
    template_id: template,
    version_number: 2,
    join_radius_metres: 250,
    arrival_radius_metres: 50,
    call_grace_seconds: 300,
  };
  ok(await call("publish_effective_store_policy", p, ah()));
  assert.equal(
    (
      await call(
        "publish_effective_store_policy",
        { ...p, policy_id: uid(), version_number: 3, call_grace_seconds: 20 },
        ah(),
      )
    ).status,
    403,
  );
  ok(
    await call(
      "set_store_opening_period",
      {
        store_id: newStore,
        period_id: uid(),
        weekday: 1,
        opens_minute: 600,
        closes_minute: 1200,
      },
      ah(),
    ),
  );
  const manager = uid(),
    email = "manager-" + uid() + "@example.test",
    password = token();
  ok(
    await call(
      "create_manager_account",
      {
        store_id: store.store_id,
        account_id: manager,
        email,
        display_name: "Test Manager",
        initial_password: password,
      },
      ah(),
    ),
  );
  const login = await call("sign_in_operator", { email, password });
  ok(login);
  const cookie = "operator_session=" + login.cookies[0].value;
  assert.equal(
    (
      await call(
        "read_store_period_metrics",
        {
          store_id: other.store_id,
          from_time: new Date(Date.now() - 10000).toISOString(),
          to_time: new Date().toISOString(),
        },
        { cookie },
      )
    ).status,
    403,
  );
  assert.equal(
    ok(await call("read_head_office_store_overview", {}, { cookie })).length,
    1,
  );
  ok(await call("disable_operator_account", { account_id: manager }, ah()));
  assert.equal(
    (await call("read_head_office_store_overview", {}, { cookie })).status,
    401,
  );
  ok(
    await call(
      "register_store_device",
      {
        store_id: newStore,
        device_id: uid(),
        device_kind: "printer",
        device_label: "Test new printer",
      },
      ah(),
    ),
  );
  ok(
    await call(
      "set_tablet_store_pin",
      { store_id: newStore, new_pin: "135790" },
      ah(),
    ),
  );
  ok(
    await call(
      "set_store_waitlist_state",
      { store_id: newStore, waitlist_state: "waitlist_closed" },
      ah(),
    ),
  );
  ok(
    await call(
      "close_operating_session",
      { store_id: other.store_id, session_id: other.session.session_id },
      ah(),
    ),
  );
  ok(
    await call(
      "open_operating_session",
      {
        store_id: other.store_id,
        session_id: uid(),
        owner_device_id: other.session.owner_device_id,
        layout_id: other.session.layout_id,
        policy_id: policy,
        business_date: new Date().toISOString().slice(0, 10),
      },
      ah(),
    ),
  );
});
test("deferral, no-show, delivery receipt validation and secret cleanup", async () => {
  let snap = ok(
    await call(
      "read_store_snapshot_manifest",
      { store_id: store.store_id },
      dh(),
    ),
  );
  const result = ok(
    await call(
      "call_next_group",
      { store_id: store.store_id, expected_state_version: snap.state_version },
      dh(),
    ),
  );
  ok(
    await call(
      "defer_called_group",
      { group_id: result.group_id, expected_call_id: result.call_id },
      dh(),
    ),
  );
  snap = ok(
    await call(
      "read_store_snapshot_manifest",
      { store_id: store.store_id },
      dh(),
    ),
  );
  const next = ok(
    await call(
      "call_next_group",
      { store_id: store.store_id, expected_state_version: snap.state_version },
      dh(),
    ),
  );
  // Advance only this fixture call's review deadline while preserving the modeled time constraint.
  await pool.query(
    "UPDATE group_calls SET called_at=now()-interval '6 minutes',review_due_at=now()-interval '1 minute' WHERE store_id=$1 AND call_id=$2",
    [store.store_id, next.call_id],
  );
  ok(
    await call(
      "mark_group_no_show",
      {
        group_id: next.group_id,
        expected_call_id: next.call_id,
        reason_code: "grace_elapsed",
      },
      dh(),
    ),
  );
  const b = {
    store_id: store.store_id,
    job_id: uid(),
    attempt_id: uid(),
    source_event_id: uid(),
    receipt_status: "delivered",
    reported_at: new Date().toISOString(),
  };
  assert.equal((await call("acknowledge_delivery", b)).status, 401);
  await maintenance();
  await recovery();
  ok(await call("sign_out_operator", {}, ah()));
  assert.equal(
    (await call("read_head_office_store_overview", {}, ah())).status,
    401,
  );
});

after(async () => {
  writeFileSync(
    "data/integration-coverage.json",
    JSON.stringify(
      { time: new Date().toISOString(), exercised: [...touched] },
      null,
      2,
    ),
  );
  if (app) {
    const a = await one(
      pool,
      "SELECT * FROM operator_accounts WHERE login_digest=$1",
      [digest("login", process.env.SEED_EMAIL!)],
    );
    const stores = await rows(
      pool,
      "SELECT store_id FROM stores WHERE organization_id=$1",
      [a.organization_id],
    );
    const accounts = await rows(
      pool,
      "SELECT account_id FROM operator_accounts WHERE organization_id=$1",
      [a.organization_id],
    );
    const manifest = JSON.parse(
      readFileSync("../db/schema_manifest.json", "utf8"),
    );
    const remaining = new Set<string>(Object.keys(manifest.tables));
    while (remaining.size) {
      const removable = [...remaining].filter(
        (t) =>
          !manifest.constraints.some(
            (c: any) =>
              c.type === "f" &&
              c.parent === t &&
              c.table !== t &&
              remaining.has(c.table),
          ),
      );
      assert.ok(removable.length, "Schema dependency cycle");
      for (const table of removable) {
        const columns = manifest.tables[table].map((x: any) => x.name);
        if (table === "administrative_audit_events")
          await pool.query(
            "DELETE FROM administrative_audit_events WHERE organization_id=$1",
            [a.organization_id],
          );
        else if (columns.includes("store_id"))
          await pool.query(
            `DELETE FROM "${table}" WHERE store_id=ANY($1::uuid[])`,
            [stores.map((s: any) => s.store_id)],
          );
        else if (columns.includes("organization_id"))
          await pool.query(`DELETE FROM "${table}" WHERE organization_id=$1`, [
            a.organization_id,
          ]);
        else if (columns.includes("account_id"))
          await pool.query(
            `DELETE FROM "${table}" WHERE account_id=ANY($1::uuid[])`,
            [accounts.map((a: any) => a.account_id)],
          );
        remaining.delete(table);
      }
    }
    await app.close();
  }
  await pool.end();
});
