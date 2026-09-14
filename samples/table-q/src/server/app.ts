import Fastify from "fastify";
import cookie from "@fastify/cookie";
import statics from "@fastify/static";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import {
  pool,
  tx,
  one,
  rows,
  insert,
  lock,
  requireThat,
  HttpError,
} from "./db";
import {
  operator,
  device,
  staff,
  ticket,
  uid,
  token,
  code,
  digest,
  verifyPassword,
  hashPassword,
  cookieOptions,
  signed,
  unsign,
  rate,
  bearer,
} from "./security";
import {
  command,
  join,
  callGroup,
  transition,
  clearTable,
  ticketStatus,
  issueCode,
  event,
  session,
  distance,
  tables,
} from "./queue";
import { admin } from "./admin";
import { receiveOffline } from "./sync";
import { heartbeat, acknowledge } from "./delivery";
import {
  controls,
  setControl,
  effectHistory,
  simulatedEffect,
} from "./simulator";
export const contracts: any[] = JSON.parse(
  readFileSync(
    new URL("../contracts/beyond-entity.json", import.meta.url),
    "utf8",
  ),
);
const byName = new Map(contracts.map((x) => [x.name, x]));
const admins = new Set([
  "create_store",
  "create_layout_version",
  "add_layout_row",
  "add_dining_table",
  "publish_layout",
  "publish_effective_store_policy",
  "rotate_store_join_qr",
  "create_manager_account",
  "register_store_device",
  "rotate_device_credential",
  "create_hq_policy_template",
  "set_store_opening_period",
  "resolve_sync_conflict",
  "open_operating_session",
  "close_operating_session",
  "set_tablet_store_pin",
  "disable_operator_account",
  "set_store_waitlist_state",
  "issue_partner_credential",
]);
async function projection(name: string, b: any, ctx: any = {}) {
  const contract = byName.get(name);
  let sql = contract.transformations
    .filter((x: any) => x.operation_type === "SELECT")
    .at(-1).referring_raw_code;
  const params: any[] = [];
  let prefix = "";
  if (sql.includes(name + " p")) {
    const context = {
      l_authorized: true,
      l_store_id: b.store_id || null,
      l_organization_id: ctx.organization_id || null,
      l_device_id: ctx.device_id || null,
      store_id: b.store_id || null,
      call_id: b.call_id || null,
      ...ctx,
    };
    prefix =
      `WITH ${name} AS (SELECT ` +
      Object.entries(context)
        .map(([k, v]) => {
          params.push(v);
          return (
            "$" +
            params.length +
            "::" +
            (k === "l_authorized"
              ? "boolean"
              : k.endsWith("_id")
                ? "uuid"
                : "text") +
            " AS " +
            k
          );
        })
        .join(",") +
      ") ";
  }
  if (name === "read_wait_and_turnover_metrics")
    sql += " AND e.occurred_at>=g.joined_at";
  sql = sql.replace(/(?<!:):([a-z_]+)/g, (_: string, k: string) => {
    requireThat(b[k] !== undefined, "Missing parameter " + k, 400);
    params.push(b[k]);
    return "$" + params.length;
  });
  return rows(pool, prefix + sql, params);
}
async function storeReader(r: any, store: string) {
  if (r.cookies.operator_session) return operator(r, pool, store);
  return device(r, pool, store);
}
async function handle(name: string, r: any, b: any, reply: any): Promise<any> {
  if (admins.has(name)) return admin(name, r, b);
  switch (name) {
    case "sign_in_operator": {
      await rate("login-ip:" + r.ip, 20);
      await rate("login:" + b.email.toLowerCase(), 10);
      const a = await one(
        pool,
        "SELECT * FROM operator_accounts WHERE login_digest=$1 AND disabled_at IS NULL",
        [digest("login", b.email.trim().toLowerCase())],
      );
      requireThat(
        a && (await verifyPassword(a.password_verifier, b.password)),
        "Invalid email or password",
        401,
      );
      const raw = token(),
        expires = new Date(Date.now() + 8 * 3600000);
      await insert(pool, "operator_sessions", {
        operator_session_id: uid(),
        account_id: a.account_id,
        token_hash: digest("operator", raw),
        created_at: new Date(),
        expires_at: expires,
      });
      reply.setCookie("operator_session", raw, { ...cookieOptions, expires });
      return {
        account_id: a.account_id,
        account_role: a.account_role,
        display_name: a.display_name,
        expires_at: expires,
      };
    }
    case "sign_out_operator": {
      const a = await operator(r);
      await pool.query(
        "UPDATE operator_sessions SET revoked_at=now() WHERE operator_session_id=$1",
        [a.operator_session_id],
      );
      reply.clearCookie("operator_session", cookieOptions);
      return { signed_out: true };
    }
    case "unlock_store_tablet": {
      const d = await device(r);
      await rate("pin:" + d.device_id, 10);
      const p = await one(
        pool,
        "SELECT * FROM store_pin_verifiers WHERE store_id=$1",
        [d.store_id],
      );
      requireThat(
        d.device_kind === "tablet" &&
          p &&
          (await verifyPassword(p.pin_verifier, b.pin)),
        "Incorrect tablet PIN",
        401,
      );
      const s = await one(
        pool,
        "SELECT * FROM operating_sessions WHERE store_id=$1 AND closed_at IS NULL",
        [d.store_id],
      );
      requireThat(
        s?.owner_device_id === d.device_id,
        "Device is not session owner",
        403,
      );
      return {
        unlock_token: signed({
          device: d.device_id,
          credential: digest("device", bearer(r)),
          pin: p.rotated_at.toISOString(),
          epoch: s.authority_epoch,
          exp: Date.now() + 12 * 3600000,
        }),
        store_id: d.store_id,
      };
    }
    case "create_customer_join_context": {
      let context = r.cookies.browser_join;
      try {
        if (context) unsign(context);
      } catch {
        context = null;
      }
      if (!context)
        context = signed({ actor: token(), exp: Date.now() + 86400000 });
      reply.setCookie("browser_join", context, {
        ...cookieOptions,
        maxAge: 86400,
      });
      reply.setCookie("browser_limit", context, {
        ...cookieOptions,
        maxAge: 86400,
      });
      return { ready: true };
    }
    case "find_stores":
      return projection(name, { query: "%" + b.query + "%" });
    case "resolve_join_qr": {
      const result = await projection(name, b);
      requireThat(result.length, "QR code no longer valid", 404);
      return result[0];
    }
    case "register_waiting_group":
      return command(name, r, b, (c, s, a) => join(c, s, b, a, "staff"));
    case "join_kiosk_queue":
      return command(
        name,
        r,
        b,
        (c, s, a) => join(c, s, b, a, "kiosk"),
        async (c: any, store: string) => {
          const d = await device(r, c, store);
          requireThat(
            d.device_kind === "kiosk",
            "Enrolled kiosk required",
            403,
          );
          return d;
        },
      );
    case "join_phone_queue": {
      await rate("phone:" + r.ip, 30);
      return command(
        name,
        r,
        b,
        (c, s, a) => join(c, s, b, a, "phone"),
        async () => ({ actor_id: unsign(r.cookies.browser_join || "").actor }),
      );
    }
    case "get_ticket_status":
      return ticketStatus(r, b);
    case "call_next_group":
      return command(name, r, b, async (c, s, a) => {
        requireThat(
          s.state_version === b.expected_state_version,
          "Queue changed; refresh",
        );
        return callGroup(c, s, a);
      });
    case "clear_occupied_table":
      return command(name, r, b, (c, s, a) => clearTable(c, s, b, a));
    case "seat_called_group":
    case "recall_waiting_group":
    case "defer_called_group":
    case "cancel_waiting_group":
    case "mark_group_no_show": {
      const action = (
        {
          seat_called_group: "seat",
          recall_waiting_group: "recall",
          defer_called_group: "defer",
          cancel_waiting_group: "cancel",
          mark_group_no_show: "no-show",
        } as any
      )[name];
      return command(
        name,
        r,
        b,
        (c, s, a, g) => transition(c, s, g, action, b, a),
        async (c: any, store: string) => {
          if (["defer", "cancel"].includes(action)) {
            try {
              return await ticket(r, c, b.group_id, true);
            } catch (e: any) {
              if (e.statusCode !== 401) throw e;
            }
          }
          return staff(r, c, store);
        },
      );
    }
    case "issue_watch_code":
      return command(name, r, b, async (c, s, a, g) => ({
        group_id: g.group_id,
        ...(await issueCode(c, g)),
      }));
    case "exchange_watch_code": {
      const context = unsign(r.cookies.browser_limit || "");
      await rate("watch-ip:" + r.ip, 30);
      await rate("watch-browser:" + context.actor, 10);
      const found = await one(
        pool,
        "SELECT w.*,g.group_status FROM watch_codes w JOIN queue_groups g USING(store_id,group_id) WHERE w.code_digest=$1 AND w.revoked_at IS NULL AND w.expires_at>now() AND g.group_status IN ('waiting','called')",
        [digest("watch", b.watch_code)],
      );
      requireThat(found, "Invalid or expired watch code", 404);
      const result = await command(
        name,
        r,
        { ...b, group_id: found.group_id, store_id: found.store_id },
        async (c, s, a, g) => {
          const count = await one(
            c,
            "SELECT count(*) n FROM ticket_access_grants WHERE store_id=$1 AND group_id=$2 AND access_scope='watch' AND revoked_at IS NULL AND expires_at>now()",
            [s.store_id, g.group_id],
          );
          requireThat(Number(count.n) < 5, "Watch limit reached", 429);
          const raw = token();
          await insert(c, "ticket_access_grants", {
            store_id: s.store_id,
            access_id: uid(),
            group_id: g.group_id,
            token_hash: digest("ticket", raw),
            access_scope: "watch",
            created_at: new Date(),
            expires_at: found.expires_at,
          });
          return {
            group_id: g.group_id,
            watch_token: raw,
            expires_at: found.expires_at,
            access_scope: "watch",
          };
        },
        async () => ({ actor_id: context.actor + found.watch_code_id }),
      );
      reply.setCookie("watch_" + found.group_id, result.watch_token, {
        ...cookieOptions,
        expires: new Date(result.expires_at),
      });
      const { watch_token, ...out } = result;
      return out;
    }
    case "issue_arrival_challenge":
      return command(name, r, b, async (c, s) => {
        const value = code(),
          expires = new Date(Date.now() + 60000);
        await c.query(
          "UPDATE arrival_challenges SET expires_at=now() WHERE store_id=$1 AND session_id=$2 AND expires_at>now()",
          [s.store_id, s.session_id],
        );
        await insert(c, "arrival_challenges", {
          store_id: s.store_id,
          challenge_id: uid(),
          session_id: s.session_id,
          code_digest: digest("arrival", value),
          valid_from: new Date(),
          expires_at: expires,
        });
        return { arrival_code: value, expires_at: expires };
      });
    case "confirm_group_arrival":
      return command(
        name,
        r,
        b,
        async (c, s, a, g) => {
          requireThat(
            g.group_status === "waiting",
            "Only waiting groups can confirm arrival",
          );
          if (!a.device_id) {
            requireThat(
              await one(
                c,
                "SELECT 1 FROM arrival_challenges WHERE store_id=$1 AND session_id=$2 AND code_digest=$3 AND expires_at>now()",
                [s.store_id, s.session_id, digest("arrival", b.arrival_code)],
              ),
              "Arrival code expired or invalid",
              403,
            );
            const st = await one(
              c,
              "SELECT latitude,longitude FROM stores WHERE store_id=$1",
              [s.store_id],
            );
            requireThat(
              Number.isFinite(b.latitude) &&
                Number.isFinite(b.longitude) &&
                distance(b.latitude, b.longitude, st.latitude, st.longitude) <=
                  s.arrival_radius_metres,
              "Confirm arrival near the store",
              403,
            );
          }
          if (!g.arrival_confirmed_at) {
            await c.query(
              "UPDATE queue_groups SET arrival_confirmed_at=now() WHERE store_id=$1 AND group_id=$2",
              [s.store_id, g.group_id],
            );
            await event(
              c,
              s,
              g,
              "arrival_confirmed",
              g.group_status,
              g.group_status,
              a,
            );
          }
          return {
            group_id: g.group_id,
            arrival_confirmed: true,
            state_version: s.state_version,
          };
        },
        async (c: any, store: string) => {
          try {
            return await ticket(r, c, b.group_id, true);
          } catch {
            return staff(r, c, store);
          }
        },
      );
    case "record_device_heartbeat":
      return tx(async (c) => {
        const d = await device(r, c, b.store_id);
        requireThat(d.device_id === b.device_id, "Wrong heartbeat device", 403);
        await c.query(
          "SELECT 1 FROM store_devices WHERE store_id=$1 AND device_id=$2 FOR UPDATE",
          [d.store_id, d.device_id],
        );
        return heartbeat(c, d, b);
      });
    case "receive_offline_command":
      return receiveOffline(r, b);
    case "read_offline_command_status": {
      const d = await device(r, pool, b.store_id);
      return projection(name, b, { l_device_id: d.device_id });
    }
    case "read_store_snapshot_manifest": {
      await storeReader(r, b.store_id);
      const s = (await projection(name, b))[0];
      if (!s) return null;
      const cur = await one(
        pool,
        "SELECT coalesce(max(last_received_sequence),0)+1 AS next_device_sequence FROM device_sync_cursors WHERE store_id=$1 AND device_id=$2 AND session_id=$3 AND authority_epoch=$4",
        [b.store_id, s.owner_device_id, s.session_id, s.authority_epoch],
      );
      return { ...s, next_device_sequence: cur.next_device_sequence };
    }
    case "read_store_queue_snapshot":
    case "read_store_table_snapshot": {
      await storeReader(r, b.store_id);
      return tx(async (c) => {
        const s = await session(c, b.store_id);
        requireThat(
          s.state_version === b.state_version &&
            s.sync_snapshot_revision === b.sync_snapshot_revision,
          "Snapshot changed; retry from manifest",
        );
        if (name === "read_store_table_snapshot")
          return (await tables(c, s)).map((t: any) => ({
            table_id: t.table_id,
            table_number: t.table_number,
            row_number: t.row_number,
            row_position: t.row_position,
            seat_count: t.seat_count,
            is_window: t.is_window,
            allocation_id: t.allocation_id || null,
            table_status: t.table_status,
          }));
        return rows(
          c,
          "SELECT g.group_id,g.queue_sequence,g.ticket_number,g.party_size,g.wants_window,(g.arrival_confirmed_at IS NOT NULL) AS arrival_confirmed,g.group_status,c.call_id,a.allocation_id,a.table_id FROM queue_groups g LEFT JOIN group_calls c ON c.store_id=g.store_id AND c.group_id=g.group_id AND c.call_status IN ('active','seated') LEFT JOIN table_allocations a ON a.store_id=c.store_id AND a.call_id=c.call_id AND a.released_at IS NULL WHERE g.store_id=$1 AND g.session_id=$2 AND g.group_status IN ('waiting','called','seated') ORDER BY g.queue_sequence",
          [s.store_id, s.session_id],
        );
      });
    }
    case "read_store_device_health":
      await storeReader(r, b.store_id);
      return projection(name, b);
    case "read_call_delivery_status":
      await storeReader(r, b.store_id);
      return projection(name, b, { l_auth_store_id: b.store_id });
    case "read_partner_store_status": {
      const p = await one(
        pool,
        "SELECT * FROM partner_credentials WHERE token_hash=$1 AND revoked_at IS NULL AND expires_at>now()",
        [digest("partner", bearer(r))],
      );
      requireThat(p, "Invalid partner credential", 401);
      await rate("partner:" + p.partner_id, 60);
      const result = await projection(name, b, {
        l_organization_id: p.organization_id,
      });
      requireThat(result.length, "Store access denied", 403);
      return result[0];
    }
    case "read_head_office_store_overview": {
      const a = await operator(r);
      const all = await projection(name, b, {
        l_organization_id: a.organization_id,
      });
      if (a.account_role === "head_office") return all;
      const grants = await rows(
        pool,
        "SELECT store_id FROM operator_store_grants WHERE account_id=$1 AND revoked_at IS NULL",
        [a.account_id],
      );
      return all.filter((s: any) =>
        grants.some((g: any) => g.store_id === s.store_id),
      );
    }
    case "read_store_period_metrics":
    case "read_wait_and_turnover_metrics":
    case "read_hourly_store_activity":
    case "read_device_fault_metrics":
      await operator(r, pool, b.store_id);
      requireThat(
        new Date(b.to_time) > new Date(b.from_time) &&
          new Date(b.to_time).getTime() - new Date(b.from_time).getTime() <=
            366 * 86400000,
        "Choose a period of at most one year",
        400,
      );
      return projection(name, b);
    case "acknowledge_delivery": {
      requireThat(
        process.env.SIMULATOR_ENABLED === "true" &&
          bearer(r) === digest("simulator-auth", "receipts"),
        "Simulator authentication required",
        401,
      );
      requireThat(
        ["delivered", "failed"].includes(b.receipt_status),
        "Invalid receipt",
        400,
      );
      return acknowledge(b);
    }
    case "stream_ticket_invalidations": {
      await ticket(r, pool, b.group_id);
      reply.hijack();
      reply.raw.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-store",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      });
      let last = "",
        busy = false;
      const tick = async () => {
        if (busy) return;
        busy = true;
        try {
          const value = await ticketStatus(r, b);
          const text = JSON.stringify(value);
          if (text !== last) {
            reply.raw.write(`event: ticket\ndata: ${text}\n\n`);
            last = text;
          } else reply.raw.write(": heartbeat\n\n");
        } catch {
          reply.raw.write("event: expired\ndata: {}\n\n");
          reply.raw.end();
        } finally {
          busy = false;
        }
      };
      void tick();
      const timer = setInterval(tick, 2000);
      reply.raw.on("close", () => clearInterval(timer));
      return;
    }
    default:
      throw new Error("Missing handler " + name);
  }
}
export async function buildApp() {
  const app = Fastify({ logger: false, bodyLimit: 65536, trustProxy: false });
  await app.register(cookie);
  app.addHook("onRequest", async (r, reply) => {
    if (r.url.startsWith("/api")) reply.header("Cache-Control", "no-store");
    if (!["GET", "HEAD", "OPTIONS"].includes(r.method)) {
      const origin = r.headers.origin;
      const allowed = [
        process.env.APP_ORIGIN,
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
      ];
      requireThat(
        !origin || allowed.includes(origin),
        "Cross-origin mutation denied",
        403,
      );
      if (r.cookies.operator_session)
        requireThat(
          !!origin || r.headers["x-tableq-client"] === "cli",
          "Origin required for cookie mutation",
          403,
        );
    }
  });
  app.setErrorHandler((e: any, r, reply) => {
    const status =
      e.statusCode ||
      (["23505", "23503", "23514", "22P02"].includes(e.code) ? 409 : 500);
    if (status === 500) console.error("Request failed", e.code || e.name);
    reply
      .code(status)
      .send({
        error:
          status === 500
            ? "Internal server error"
            : e.validation
              ? "Invalid request fields"
              : e.code
                ? "Database constraint rejected this operation"
                : e.message,
      });
  });
  app.get("/api/health", async () => {
    const d = await one(pool, "SELECT current_database() AS database");
    return { status: "ok", database: d.database };
  });
  for (const ct of contracts.filter((x) => x.type === "api_server")) {
    const method = ct.metadata.method;
    const url = ct.metadata.path.replace(/\{([^}]+)\}/g, ":$1");
    const pathFields = [...ct.metadata.path.matchAll(/\{([^}]+)\}/g)].map(
      (m: any) => m[1],
    );
    const fields = ct.input.filter(
      (a: any) =>
        !pathFields.includes(a.column_name) &&
        ![
          "authorization",
          "idempotency_key",
          "operator_session_cookie",
          "watch_session_cookie",
          "browser_limit_cookie",
          "browser_join_cookie",
          "last_event_id",
        ].includes(a.column_name),
    );
    const properties: any = {};
    const required: string[] = [];
    for (const a of fields) {
      const k = a.column_name;
      let type = a.data_type.toLowerCase().includes("number")
        ? "number"
        : a.data_type.toLowerCase() === "boolean"
          ? "boolean"
          : "string";
      properties[k] = { type };
      if (type === "string") {
        properties[k].maxLength = k.includes("password") ? 256 : 1024;
        if (k.endsWith("_id")) properties[k].pattern = "^[0-9a-fA-F-]{36}$";
      }
      if (a.is_not_null) required.push(k);
      else properties[k].type = [type, "null"];
    }
    const schema: any = {};
    if (fields.length)
      schema[method === "GET" ? "querystring" : "body"] = {
        type: "object",
        properties,
        required,
        additionalProperties: false,
      };
    app.route({
      method,
      url,
      schema,
      handler: async (r, reply) =>
        handle(
          ct.name,
          r,
          { ...(r.query as any), ...(r.body as any), ...(r.params as any) },
          reply,
        ),
    });
  }
  app.get("/api/admin/bootstrap", async (r) => {
    const a = await operator(r);
    const stores = await rows(
      pool,
      "SELECT st.* FROM stores st WHERE organization_id=$1 AND ($2='head_office' OR EXISTS(SELECT 1 FROM operator_store_grants g WHERE g.store_id=st.store_id AND g.account_id=$3 AND g.revoked_at IS NULL)) ORDER BY store_code",
      [a.organization_id, a.account_role, a.account_id],
    );
    for (const s of stores) {
      delete s.contact_phone_ciphertext;
      delete s.contact_email_ciphertext;
      s.devices = await rows(
        pool,
        "SELECT device_id,device_kind,device_label FROM store_devices WHERE store_id=$1 AND revoked_at IS NULL",
        [s.store_id],
      );
      s.layouts = await rows(
        pool,
        "SELECT * FROM layout_versions WHERE store_id=$1 ORDER BY version_number",
        [s.store_id],
      );
      s.policies = await rows(
        pool,
        "SELECT * FROM store_policy_versions WHERE store_id=$1 ORDER BY version_number",
        [s.store_id],
      );
      s.qr = await one(
        pool,
        "SELECT qr_id FROM store_join_qr_versions WHERE store_id=$1 AND revoked_at IS NULL",
        [s.store_id],
      );
      s.session = await one(
        pool,
        "SELECT * FROM operating_sessions WHERE store_id=$1 AND closed_at IS NULL",
        [s.store_id],
      );
    }
    return {
      account: { display_name: a.display_name, account_role: a.account_role },
      stores,
      templates: await rows(
        pool,
        "SELECT * FROM hq_policy_templates WHERE organization_id=$1 ORDER BY version_number",
        [a.organization_id],
      ),
    };
  });
  app.get("/api/admin/stores/:store_id/configuration", async (r: any) => {
    await operator(r, pool, r.params.store_id);
    return {
      rows: await rows(
        pool,
        "SELECT * FROM layout_rows WHERE store_id=$1 ORDER BY row_number",
        [r.params.store_id],
      ),
      tables: await rows(
        pool,
        "SELECT * FROM dining_tables WHERE store_id=$1 ORDER BY table_number",
        [r.params.store_id],
      ),
      conflicts: await rows(
        pool,
        "SELECT * FROM sync_conflicts WHERE store_id=$1 AND conflict_status='open' ORDER BY created_at",
        [r.params.store_id],
      ),
      periods: await rows(
        pool,
        "SELECT * FROM store_opening_periods WHERE store_id=$1 ORDER BY weekday",
        [r.params.store_id],
      ),
    };
  });
  app.get("/api/simulator/:store_id", async (r: any) => {
    await operator(r, pool, r.params.store_id);
    requireThat(
      process.env.SIMULATOR_ENABLED === "true",
      "Simulator disabled",
      404,
    );
    const ds = await rows(
      pool,
      "SELECT device_id FROM store_devices WHERE store_id=$1",
      [r.params.store_id],
    );
    const ctl = controls();
    return {
      effects: effectHistory(r.params.store_id),
      controls: Object.fromEntries(
        ds.map((d: any) => [
          d.device_id,
          ctl[d.device_id] || { fault_code: "none", offline: false },
        ]),
      ),
      jobs: await rows(
        pool,
        "SELECT job_id,channel,job_status,attempt_count,created_at,terminal_reason FROM delivery_jobs WHERE store_id=$1 ORDER BY created_at DESC LIMIT 50",
        [r.params.store_id],
      ),
    };
  });
  app.put("/api/simulator/:store_id/:device_id", async (r: any) => {
    await operator(r, pool, r.params.store_id);
    requireThat(
      process.env.SIMULATOR_ENABLED === "true",
      "Simulator disabled",
      404,
    );
    requireThat(
      await one(
        pool,
        "SELECT 1 FROM store_devices WHERE store_id=$1 AND device_id=$2",
        [r.params.store_id, r.params.device_id],
      ),
      "Unknown device",
      404,
    );
    setControl(r.params.device_id, r.body);
    return { saved: true };
  });
  app.post("/api/simulator/print", async (r: any) => {
    const d = await device(r);
    requireThat(
      ["kiosk", "tablet"].includes(d.device_kind),
      "Print permission denied",
      403,
    );
    const b = r.body;
    const g = await one(
      pool,
      "SELECT * FROM queue_groups WHERE store_id=$1 AND group_id=$2",
      [d.store_id, b.group_id],
    );
    requireThat(g, "Unknown ticket", 404);
    const printer = await one(
      pool,
      "SELECT device_id FROM store_devices WHERE store_id=$1 AND device_kind='printer' AND revoked_at IS NULL ORDER BY device_id LIMIT 1",
      [d.store_id],
    );
    requireThat(printer, "Printer unavailable", 503);
    return simulatedEffect(
      {
        job_id: b.job_id,
        store_id: d.store_id,
        group_id: b.group_id,
        channel: "ticket_print",
        target_device_id: printer.device_id,
      },
      "ticket_print",
    );
  });
  const dist = path.resolve("dist");
  if (existsSync(dist)) {
    await app.register(statics, { root: dist });
    app.setNotFoundHandler((r, reply) =>
      r.url.startsWith("/api")
        ? reply.code(404).send({ error: "Not found" })
        : reply.sendFile("index.html"),
    );
  }
  return app;
}
