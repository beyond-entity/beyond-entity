import {
  pool,
  one,
  rows,
  insert,
  tx,
  lock,
  requireThat,
  HttpError,
} from "./db";
import {
  uid,
  token,
  code,
  digest,
  canonical,
  seal,
  unseal,
  staff,
  device,
  ticket,
  unsign,
  rate,
} from "./security";
export const eligible = (g: any, t: any) =>
  t.seat_count >= g.party_size && (!g.wants_window || t.is_window);
export function distance(lat: number, lon: number, a: number, b: number) {
  const r = Math.PI / 180;
  const x =
    Math.sin(((a - lat) * r) / 2) ** 2 +
    Math.cos(lat * r) * Math.cos(a * r) * Math.sin(((b - lon) * r) / 2) ** 2;
  return 6371000 * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}
export async function session(c: any, store: string) {
  const s = await one(
    c,
    `SELECT s.*,p.join_radius_metres,p.arrival_radius_metres,p.call_grace_seconds,p.max_party_size,p.max_deferrals FROM operating_sessions s JOIN store_policy_versions p USING(store_id,policy_id) WHERE s.store_id=$1 AND s.closed_at IS NULL FOR UPDATE OF s`,
    [store],
  );
  requireThat(s, "No open operating session");
  return s;
}
export async function tables(c: any, s: any, ignore?: any) {
  return rows(
    c,
    `SELECT t.*,r.row_number,a.allocation_id,a.call_id,a.allocation_status,CASE WHEN EXISTS(SELECT 1 FROM physical_table_facts f WHERE f.store_id=t.store_id AND f.table_id=t.table_id AND f.quarantine_active AND NOT EXISTS(SELECT 1 FROM device_sync_commands dc WHERE dc.store_id=f.store_id AND dc.sync_command_id=f.sync_command_id AND dc.device_id=$3 AND dc.session_id=$4 AND dc.authority_epoch=$5 AND dc.device_sequence >= $6 AND dc.sync_status='received')) THEN 'quarantined' WHEN a.allocation_status='held' THEN 'held' WHEN a.allocation_status='occupied' THEN 'occupied' ELSE 'free' END AS table_status FROM dining_tables t JOIN layout_rows r USING(store_id,row_id) LEFT JOIN table_allocations a ON a.store_id=t.store_id AND a.table_id=t.table_id AND a.released_at IS NULL WHERE t.store_id=$1 AND r.layout_id=$2 ORDER BY r.row_number,t.row_position`,
    [
      s.store_id,
      s.layout_id,
      ignore?.device_id || null,
      ignore?.session_id || null,
      ignore?.authority_epoch || null,
      ignore?.device_sequence || null,
    ],
  );
}
export async function event(
  c: any,
  s: any,
  g: any,
  type: string,
  previous: string | null,
  next: string | null,
  actor: any = {},
  extra: any = {},
) {
  const updated = await one(
    c,
    "UPDATE operating_sessions SET last_event_sequence=last_event_sequence+1,state_version=state_version+1 WHERE store_id=$1 AND session_id=$2 RETURNING last_event_sequence,state_version",
    [s.store_id, s.session_id],
  );
  Object.assign(s, updated);
  return insert(c, "queue_events", {
    store_id: s.store_id,
    event_id: uid(),
    session_id: s.session_id,
    event_sequence: s.last_event_sequence,
    group_id: g?.group_id || null,
    actor_device_id: actor.device_id || null,
    actor_kind: actor.device_id
      ? "store_device"
      : actor.account_id
        ? "manager"
        : actor.access_id
          ? "customer"
          : "system",
    event_type: type,
    previous_status: previous,
    next_status: next,
    occurred_at: new Date(),
    recorded_at: new Date(),
    ...extra,
  });
}
export async function revoke(c: any, g: any) {
  await c.query(
    "UPDATE watch_codes SET revoked_at=now() WHERE store_id=$1 AND group_id=$2 AND revoked_at IS NULL",
    [g.store_id, g.group_id],
  );
  await c.query(
    "UPDATE ticket_access_grants SET revoked_at=now() WHERE store_id=$1 AND group_id=$2 AND access_scope='watch' AND revoked_at IS NULL",
    [g.store_id, g.group_id],
  );
}
export async function issueCode(c: any, g: any) {
  requireThat(
    ["waiting", "called"].includes(g.group_status),
    "Ticket is no longer waiting",
  );
  await c.query(
    "UPDATE watch_codes SET revoked_at=now() WHERE expires_at<=now() AND revoked_at IS NULL",
  );
  await c.query(
    "UPDATE watch_codes SET revoked_at=now() WHERE store_id=$1 AND group_id=$2 AND revoked_at IS NULL",
    [g.store_id, g.group_id],
  );
  await c.query(
    "UPDATE ticket_access_grants SET revoked_at=now() WHERE store_id=$1 AND group_id=$2 AND access_scope='watch' AND revoked_at IS NULL",
    [g.store_id, g.group_id],
  );
  const busy = new Set(
    (
      await rows(
        c,
        "SELECT code_digest FROM watch_codes WHERE revoked_at IS NULL",
      )
    ).map((x: any) => x.code_digest),
  );
  requireThat(busy.size < 10000, "Watch code capacity exhausted", 503);
  let value;
  do {
    value = code();
  } while (busy.has(digest("watch", value)));
  const expires = new Date(Date.now() + 12 * 3600000);
  await insert(c, "watch_codes", {
    store_id: g.store_id,
    watch_code_id: uid(),
    group_id: g.group_id,
    code_digest: digest("watch", value),
    issued_at: new Date(),
    expires_at: expires,
  });
  return { watch_code: value, expires_at: expires };
}
export async function enqueue(c: any, s: any, g: any, call: any, e: any) {
  const bell = await one(
    c,
    "SELECT device_id FROM store_devices WHERE store_id=$1 AND device_kind='call_bell' AND revoked_at IS NULL ORDER BY device_id LIMIT 1",
    [s.store_id],
  );
  for (const channel of ["customer_notification", "call_bell"])
    await insert(c, "delivery_jobs", {
      store_id: s.store_id,
      job_id: uid(),
      session_id: s.session_id,
      event_id: e.event_id,
      group_id: g.group_id,
      call_id: call.call_id,
      target_device_id: channel === "call_bell" ? bell?.device_id : null,
      channel,
      lane_key: channel + ":" + g.group_id,
      event_sequence: e.event_sequence,
      job_status: channel === "call_bell" && !bell ? "failed" : "queued",
      attempt_count: 0,
      next_attempt_at: new Date(),
      expires_at: call.review_due_at,
      terminal_reason:
        channel === "call_bell" && !bell ? "missing_bell_device" : null,
      created_at: new Date(),
    });
}
export async function callGroup(
  c: any,
  s: any,
  actor: any,
  forced?: any,
  at = new Date(),
  ids: any = {},
) {
  const ts = await tables(c, s, forced),
    gs = await rows(
      c,
      "SELECT * FROM queue_groups WHERE store_id=$1 AND session_id=$2 AND group_status='waiting' AND arrival_confirmed_at IS NOT NULL ORDER BY queue_sequence",
      [s.store_id, s.session_id],
    );
  let g, t;
  for (const candidate of gs) {
    const fit = ts
      .filter((t: any) => t.table_status === "free" && eligible(candidate, t))
      .sort(
        (a: any, b: any) =>
          a.seat_count - b.seat_count ||
          a.table_number.localeCompare(b.table_number),
      );
    if (fit.length) {
      g = candidate;
      t = fit[0];
      break;
    }
  }
  requireThat(g && t, "No arrived group fits an available table");
  if (forced)
    requireThat(
      g.group_id === forced.group_id && t.table_id === forced.table_id,
      "Offline call does not match earliest eligible pair",
    );
  const count = await one(
    c,
    "SELECT coalesce(max(call_number),0)+1 AS n FROM group_calls WHERE store_id=$1 AND group_id=$2",
    [s.store_id, g.group_id],
  );
  const call = await insert(c, "group_calls", {
    store_id: s.store_id,
    call_id: ids.call_id || uid(),
    group_id: g.group_id,
    call_number: count.n,
    call_status: "active",
    called_at: at,
    review_due_at: new Date(at.getTime() + s.call_grace_seconds * 1000),
    last_notified_at: at,
    recall_count: 0,
  });
  const alloc = await insert(c, "table_allocations", {
    store_id: s.store_id,
    allocation_id: ids.allocation_id || uid(),
    table_id: t.table_id,
    call_id: call.call_id,
    allocation_status: "held",
    held_at: at,
  });
  await c.query(
    "UPDATE queue_groups SET group_status='called' WHERE store_id=$1 AND group_id=$2",
    [s.store_id, g.group_id],
  );
  const e = await event(c, s, g, "called", "waiting", "called", actor, {
    call_id: call.call_id,
    allocation_id: alloc.allocation_id,
    occurred_at: at,
  });
  if (!forced) await enqueue(c, s, g, call, e);
  return {
    group_id: g.group_id,
    ticket_code: "A-" + String(g.ticket_number).padStart(3, "0"),
    call_id: call.call_id,
    assigned_table: t.table_number,
    called_at: at,
    review_due_at: call.review_due_at,
    group_status: "called",
    state_version: s.state_version,
  };
}
export async function transition(
  c: any,
  s: any,
  g: any,
  action: string,
  b: any,
  actor: any,
  at = new Date(),
) {
  const old = g.group_status;
  const call = await one(
    c,
    "SELECT * FROM group_calls WHERE store_id=$1 AND group_id=$2 AND call_status='active'",
    [s.store_id, g.group_id],
  );
  if (action !== "cancel")
    requireThat(
      call && call.call_id === b.expected_call_id && old === "called",
      "Call changed; refresh this ticket",
    );
  if (action === "cancel")
    requireThat(
      ["waiting", "called"].includes(old),
      "Only waiting or called groups can cancel",
    );
  const alloc =
    call &&
    (await one(
      c,
      "SELECT * FROM table_allocations WHERE store_id=$1 AND call_id=$2",
      [s.store_id, call.call_id],
    ));
  if (action === "recall") {
    await c.query(
      "UPDATE group_calls SET recall_count=recall_count+1,last_notified_at=$3 WHERE store_id=$1 AND call_id=$2",
      [s.store_id, call.call_id, at],
    );
    const e = await event(c, s, g, "recalled", old, old, actor, {
      call_id: call.call_id,
      allocation_id: alloc.allocation_id,
    });
    await enqueue(c, s, g, call, e);
    return {
      group_id: g.group_id,
      call_id: call.call_id,
      recall_count: call.recall_count + 1,
      group_status: old,
      state_version: s.state_version,
    };
  }
  if (action === "defer")
    requireThat(
      s.max_deferrals === null || g.deferral_count < s.max_deferrals,
      "Deferral limit reached",
    );
  if (action === "no-show")
    requireThat(at >= call.review_due_at, "Call grace period has not elapsed");
  const next = (
    {
      seat: "seated",
      defer: "waiting",
      cancel: "cancelled",
      "no-show": "no_show",
    } as any
  )[action];
  requireThat(next, "Unknown action", 400);
  if (alloc) {
    await c.query(
      "UPDATE table_allocations SET allocation_status=$3,seated_at=CASE WHEN $3='occupied' THEN $4 ELSE seated_at END,released_at=CASE WHEN $3='released' THEN $4 ELSE NULL END WHERE store_id=$1 AND allocation_id=$2",
      [
        s.store_id,
        alloc.allocation_id,
        action === "seat" ? "occupied" : "released",
        at,
      ],
    );
  }
  if (call)
    await c.query(
      "UPDATE group_calls SET call_status=$3,closed_at=$4 WHERE store_id=$1 AND call_id=$2",
      [s.store_id, call.call_id, action === "defer" ? "deferred" : next, at],
    );
  const sequence =
    action === "defer" ? s.next_queue_sequence : g.queue_sequence;
  await c.query(
    "UPDATE queue_groups SET group_status=$3,queue_sequence=$4,deferral_count=deferral_count+$5,ended_at=$6 WHERE store_id=$1 AND group_id=$2",
    [
      s.store_id,
      g.group_id,
      next,
      sequence,
      action === "defer" ? 1 : 0,
      ["cancelled", "no_show"].includes(next) ? at : null,
    ],
  );
  if (action === "defer")
    await c.query(
      "UPDATE operating_sessions SET next_queue_sequence=next_queue_sequence+1 WHERE store_id=$1 AND session_id=$2",
      [s.store_id, s.session_id],
    );
  if (action !== "defer") await revoke(c, g);
  await event(
    c,
    s,
    g,
    action === "defer" ? "deferred" : next,
    old,
    next,
    actor,
    {
      call_id: call?.call_id || null,
      allocation_id: alloc?.allocation_id || null,
      occurred_at: at,
      previous_queue_sequence: g.queue_sequence,
      next_queue_sequence: sequence,
    },
  );
  return {
    group_id: g.group_id,
    group_status: next,
    state_version: s.state_version,
    call_id: call?.call_id,
  };
}
export async function clearTable(
  c: any,
  s: any,
  b: any,
  actor: any,
  at = new Date(),
) {
  const a = await one(
    c,
    "SELECT a.*,g.group_id FROM table_allocations a JOIN group_calls g USING(store_id,call_id) WHERE a.store_id=$1 AND a.table_id=$2 AND a.allocation_id=$3 AND a.allocation_status='occupied' AND a.released_at IS NULL",
    [s.store_id, b.table_id, b.expected_allocation_id],
  );
  requireThat(a, "Table allocation changed");
  requireThat(at >= a.seated_at, "Clear predates seating");
  await c.query(
    "UPDATE table_allocations SET allocation_status='released',released_at=$3 WHERE store_id=$1 AND allocation_id=$2",
    [s.store_id, a.allocation_id, at],
  );
  await c.query(
    "UPDATE queue_groups SET group_status='completed',ended_at=$3 WHERE store_id=$1 AND group_id=$2",
    [s.store_id, a.group_id, at],
  );
  await event(c, s, a, "cleared", "seated", "completed", actor, {
    call_id: a.call_id,
    allocation_id: a.allocation_id,
    occurred_at: at,
  });
  return { table_status: "free", state_version: s.state_version };
}
const resultMap: Record<string, string> = {
  group_id: "result_group_id",
  ticket_code: "result_ticket_code",
  group_status: "result_group_status",
  arrival_confirmed: "result_arrival_confirmed",
  state_version: "result_state_version",
  call_id: "result_call_id",
  assigned_table: "result_assigned_table",
  called_at: "result_called_at",
  review_due_at: "result_review_due_at",
  recall_count: "result_recall_count",
  table_status: "result_table_status",
  expires_at: "result_expires_at",
  access_scope: "result_access_scope",
};
export async function command(
  name: string,
  r: any,
  b: any,
  fn: (c: any, s: any, actor: any, g: any) => Promise<any>,
  auth?: any,
) {
  return tx(async (c) => {
    let g =
      b.group_id &&
      (await one(c, "SELECT * FROM queue_groups WHERE group_id=$1", [
        b.group_id,
      ]));
    const store = b.store_id || g?.store_id;
    requireThat(store, "Unknown store or ticket", 404);
    const actor = auth ? await auth(c, store, g) : await staff(r, c, store);
    const actorId = actor.device_id || actor.access_id || actor.actor_id;
    requireThat(actorId, "Missing command identity", 401);
    const key = r.headers["idempotency-key"];
    requireThat(
      typeof key === "string" && /^[\x21-\x7E]{16,128}$/.test(key),
      "Idempotency-Key must contain 16–128 printable ASCII characters",
      400,
    );
    const ad = digest("actor", actorId),
      kd = digest("command-key", key),
      rd = digest("request", canonical({ name, b }));
    await lock(c, "command:" + store + ad + name + kd);
    await lock(c, "watch-allocator");
    const prior = await one(
      c,
      "SELECT * FROM command_receipts WHERE store_id=$1 AND actor_digest=$2 AND operation_name=$3 AND key_digest=$4",
      [store, ad, name, kd],
    );
    if (prior) {
      requireThat(
        prior.request_digest === rd,
        "Idempotency key reused with different arguments",
      );
      requireThat(
        prior.command_status === "succeeded",
        "Incomplete prior command",
        503,
      );
      const out: any = {};
      for (const [k, v] of Object.entries(resultMap))
        if (prior[v] !== null) out[k] = prior[v];
      const secret = await one(
        c,
        "SELECT * FROM command_secret_replays WHERE store_id=$1 AND command_id=$2 AND expires_at>now()",
        [store, prior.command_id],
      );
      if (secret) {
        const live = await one(
          c,
          "SELECT 1 FROM queue_groups WHERE store_id=$1 AND group_id=$2 AND group_status IN ('waiting','called')",
          [store, prior.result_group_id],
        );
        if (prior.result_group_id)
          requireThat(live, "Secret is no longer live", 410);
        out[secret.secret_kind] = unseal(
          secret,
          store +
            prior.command_id +
            secret.secret_kind +
            secret.expires_at.toISOString(),
        );
      } else if (
        [
          "join_phone_queue",
          "join_kiosk_queue",
          "issue_watch_code",
          "exchange_watch_code",
          "issue_arrival_challenge",
        ].includes(name)
      )
        throw new HttpError(410, "Secret replay expired; explicitly reissue");
      return out;
    }
    const s = await session(c, store);
    if (g) {
      requireThat(
        g.session_id === s.session_id,
        "Ticket belongs to a closed session",
      );
      g = await one(
        c,
        "SELECT * FROM queue_groups WHERE store_id=$1 AND group_id=$2",
        [store, g.group_id],
      );
    }
    if (actor.device_id && actor.device_kind === "tablet")
      requireThat(
        s.owner_device_id === actor.device_id,
        "Tablet is not session owner",
        403,
      );
    const cid = uid();
    await insert(c, "command_receipts", {
      store_id: store,
      command_id: cid,
      session_id: s.session_id,
      actor_digest: ad,
      operation_name: name,
      key_digest: kd,
      request_digest: rd,
      command_status: "processing",
      authority_epoch: s.authority_epoch,
      created_at: new Date(),
    });
    const out = await fn(c, s, actor, g);
    const fields: any = {};
    for (const [k, v] of Object.entries(resultMap))
      if (out[k] !== undefined) fields[v] = out[k];
    const ks = Object.keys(fields);
    await c.query(
      `UPDATE command_receipts SET command_status='succeeded',completed_at=now(),replay_until=now()+interval '24 hours',http_status=200${ks.map((k, i) => ", " + k + "=$" + (i + 3)).join("")} WHERE store_id=$1 AND command_id=$2`,
      [store, cid, ...Object.values(fields)],
    );
    for (const kind of [
      "watch_code",
      "watch_token",
      "arrival_code",
      "owner_token",
    ])
      if (out[kind]) {
        const expiry = new Date(
          Math.min(
            Date.now() + 120000,
            new Date(out.expires_at || Date.now() + 120000).getTime(),
          ),
        );
        const encrypted = seal(
          out[kind],
          store + cid + kind + expiry.toISOString(),
        );
        await insert(c, "command_secret_replays", {
          store_id: store,
          command_id: cid,
          secret_kind: kind,
          ...encrypted,
          created_at: new Date(),
          expires_at: expiry,
        });
      }
    return out;
  });
}
export async function join(c: any, s: any, b: any, actor: any, source: string) {
  requireThat(
    Number.isInteger(b.party_size) &&
      b.party_size >= 1 &&
      b.party_size <= s.max_party_size,
    "Party size must be within policy",
    400,
  );
  requireThat(
    (await tables(c, s)).some((t: any) => eligible(b, t)),
    "No table fits this party",
  );
  const st = await one(c, "SELECT * FROM stores WHERE store_id=$1", [
    s.store_id,
  ]);
  requireThat(st.store_status === "open", "Waitlist is closed");
  if (source === "phone") {
    const health = await one(
      c,
      "SELECT * FROM device_health WHERE store_id=$1 AND device_id=$2",
      [s.store_id, s.owner_device_id],
    );
    requireThat(
      health && Date.now() - health.last_seen_at.getTime() < 30000,
      "Store tablet is offline; remote joins paused",
      503,
    );
    requireThat(
      Number.isFinite(b.latitude) &&
        Number.isFinite(b.longitude) &&
        Math.abs(b.latitude) <= 90 &&
        Math.abs(b.longitude) <= 180 &&
        b.location_accuracy >= 0 &&
        b.location_accuracy <= 100 &&
        Math.abs(Date.now() - new Date(b.location_time).getTime()) <= 60000,
      "Fresh accurate location required",
      400,
    );
    requireThat(
      distance(b.latitude, b.longitude, st.latitude, st.longitude) <=
        s.join_radius_metres,
      "You are outside the joining radius",
      403,
    );
  }
  const g = await insert(c, "queue_groups", {
    store_id: s.store_id,
    group_id: uid(),
    session_id: s.session_id,
    ticket_number: s.next_ticket_number,
    queue_sequence: s.next_queue_sequence,
    party_size: b.party_size,
    wants_window: !!b.wants_window,
    join_source: source,
    group_status: "waiting",
    arrival_confirmed_at:
      source === "kiosk" || (source === "staff" && b.arrived)
        ? new Date()
        : null,
    joined_at: new Date(),
    deferral_count: 0,
  });
  await c.query(
    "UPDATE operating_sessions SET next_ticket_number=next_ticket_number+1,next_queue_sequence=next_queue_sequence+1 WHERE store_id=$1 AND session_id=$2",
    [s.store_id, s.session_id],
  );
  await event(c, s, g, "joined", null, "waiting", actor);
  const out: any = {
    group_id: g.group_id,
    ticket_code: "A-" + String(g.ticket_number).padStart(3, "0"),
    group_status: "waiting",
    arrival_confirmed: !!g.arrival_confirmed_at,
    state_version: s.state_version,
  };
  if (source === "phone") {
    out.owner_token = token();
    out.expires_at = new Date(Date.now() + 12 * 3600000);
    await insert(c, "ticket_access_grants", {
      store_id: s.store_id,
      access_id: uid(),
      group_id: g.group_id,
      token_hash: digest("ticket", out.owner_token),
      access_scope: "owner",
      created_at: new Date(),
      expires_at: out.expires_at,
    });
  }
  if (source === "kiosk") Object.assign(out, await issueCode(c, g));
  return out;
}
export async function ticketStatus(r: any, b: any) {
  return tx(async (c) => {
    const a = await ticket(r, c, b.group_id);
    const g = await one(
      c,
      "SELECT * FROM queue_groups WHERE store_id=$1 AND group_id=$2",
      [a.store_id, b.group_id],
    );
    const s = await one(
      c,
      "SELECT * FROM operating_sessions WHERE store_id=$1 AND session_id=$2",
      [a.store_id, g.session_id],
    );
    const ts = await tables(c, s);
    const competitors = await rows(
      c,
      "SELECT * FROM queue_groups WHERE store_id=$1 AND session_id=$2 AND group_status='waiting' AND queue_sequence<$3",
      [a.store_id, g.session_id, g.queue_sequence],
    );
    const call = await one(
      c,
      "SELECT c.*,t.table_number FROM group_calls c JOIN table_allocations a USING(store_id,call_id) JOIN dining_tables t USING(store_id,table_id) WHERE c.store_id=$1 AND c.group_id=$2 AND c.call_status='active'",
      [a.store_id, g.group_id],
    );
    return {
      ticket_code: "A-" + String(g.ticket_number).padStart(3, "0"),
      group_status: g.group_status,
      party_size: g.party_size,
      groups_ahead: competitors.filter((x: any) =>
        ts.some((t: any) => eligible(g, t) && eligible(x, t)),
      ).length,
      arrival_confirmed: !!g.arrival_confirmed_at,
      joined_at: g.joined_at,
      assigned_table: call?.table_number || null,
      called_at: call?.called_at || null,
      call_id: call?.call_id || null,
      can_defer: a.access_scope === "owner" && g.group_status === "called",
      can_cancel:
        a.access_scope === "owner" &&
        ["waiting", "called"].includes(g.group_status),
    };
  });
}
