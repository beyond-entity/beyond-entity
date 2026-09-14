import { one, rows, insert, tx, lock, requireThat, pool } from "./db";
import {
  operator,
  audit,
  uid,
  token,
  digest,
  hashPassword,
  verifyPassword,
  encrypt,
  canonical,
  unseal,
} from "./security";
import { event, session } from "./queue";
export async function put(
  c: any,
  table: string,
  key: Record<string, any>,
  values: Record<string, any>,
) {
  const keys = Object.keys(key);
  await lock(c, "resource:" + table + canonical(key));
  const old = await one(
    c,
    `SELECT * FROM ${table} WHERE ${keys.map((k, i) => k + "=$" + (i + 1)).join(" AND ")}`,
    Object.values(key),
  );
  if (old) {
    for (const [k, v] of Object.entries(values)) {
      if (k.endsWith("_ciphertext")) {
        if (!v && !old[k]) continue;
        requireThat(
          v &&
            old[k] &&
            unseal(JSON.parse(old[k]), k) ===
              unseal(JSON.parse(v as string), k),
          "Resource ID reused with different contact data",
        );
      } else if (k !== "created_at" && k !== "registered_at")
        requireThat(
          canonical(old[k]) === canonical(v),
          "Resource ID reused with different data: " + k,
        );
    }
    return { row: old, created: false };
  }
  return { row: await insert(c, table, { ...key, ...values }), created: true };
}
export async function admin(name: string, r: any, b: any) {
  return tx(async (c) => {
    const hq = [
      "create_store",
      "create_manager_account",
      "create_hq_policy_template",
      "issue_partner_credential",
      "disable_operator_account",
    ].includes(name);
    const a = await operator(
      r,
      c,
      name === "create_store" ? undefined : b.store_id,
      hq,
    );
    const st = b.store_id;
    let result: any = {},
      resource = st || b.account_id || b.template_id || b.partner_id;
    let changed = true;
    const create = async (table: string, key: any, values: any) => {
      const v = await put(c, table, key, values);
      changed = v.created;
      return v.row;
    };
    switch (name) {
      case "create_store": {
        requireThat(
          b.store_code?.length <= 30 &&
            b.store_name?.trim() &&
            b.address?.trim(),
          "Store code, name and address required",
          400,
        );
        try {
          new Intl.DateTimeFormat("en", { timeZone: b.time_zone });
        } catch {
          requireThat(false, "Invalid IANA time zone", 400);
        }
        const contacts: any = {};
        for (const k of ["phone", "email"])
          contacts["contact_" + k + "_ciphertext"] = b["contact_" + k]
            ? encrypt(b["contact_" + k], "contact_" + k + "_ciphertext")
            : null;
        await create(
          "stores",
          { store_id: st },
          {
            organization_id: a.organization_id,
            store_code: b.store_code,
            store_name: b.store_name,
            address: b.address,
            time_zone: b.time_zone,
            latitude: b.latitude,
            longitude: b.longitude,
            store_status: "closed",
            created_at: new Date(),
            ...contacts,
          },
        );
        result = { store_id: st };
        break;
      }
      case "create_layout_version":
        await create(
          "layout_versions",
          { store_id: st, layout_id: b.layout_id },
          {
            version_number: b.version_number,
            layout_status: "draft",
            created_at: new Date(),
          },
        );
        result = { layout_id: b.layout_id };
        resource = b.layout_id;
        break;
      case "add_layout_row": {
        const l = await one(
          c,
          "SELECT * FROM layout_versions WHERE store_id=$1 AND layout_id=$2 FOR UPDATE",
          [st, b.layout_id],
        );
        requireThat(l?.layout_status === "draft", "Layout is immutable");
        await create(
          "layout_rows",
          { store_id: st, row_id: b.row_id },
          {
            layout_id: b.layout_id,
            row_number: b.row_number,
            row_label: b.row_label,
          },
        );
        result = { row_id: b.row_id };
        resource = b.row_id;
        break;
      }
      case "add_dining_table": {
        const l = await one(
          c,
          "SELECT l.* FROM layout_versions l JOIN layout_rows r USING(store_id,layout_id) WHERE r.store_id=$1 AND r.row_id=$2 FOR UPDATE OF l",
          [st, b.row_id],
        );
        requireThat(l?.layout_status === "draft", "Layout is immutable");
        await create(
          "dining_tables",
          { store_id: st, table_id: b.table_id },
          {
            row_id: b.row_id,
            table_number: b.table_number,
            row_position: b.row_position,
            seat_count: b.seat_count,
            is_window: b.is_window,
            order_qr_enabled: false,
          },
        );
        result = { table_id: b.table_id };
        resource = b.table_id;
        break;
      }
      case "publish_layout": {
        const l = await one(
          c,
          "SELECT * FROM layout_versions WHERE store_id=$1 AND layout_id=$2 FOR UPDATE",
          [st, b.layout_id],
        );
        requireThat(
          l && ["draft", "published"].includes(l.layout_status),
          "Invalid layout",
        );
        const ts = await rows(
          c,
          "SELECT t.* FROM dining_tables t JOIN layout_rows r USING(store_id,row_id) WHERE r.store_id=$1 AND r.layout_id=$2",
          [st, b.layout_id],
        );
        requireThat(
          ts.length &&
            new Set(ts.map((t: any) => t.table_number)).size === ts.length,
          "Layout requires uniquely numbered tables",
        );
        changed = l.layout_status === "draft";
        await c.query(
          "UPDATE layout_versions SET layout_status='published' WHERE store_id=$1 AND layout_id=$2",
          [st, b.layout_id],
        );
        result = { layout_id: b.layout_id, layout_status: "published" };
        resource = b.layout_id;
        break;
      }
      case "create_hq_policy_template":
        await create(
          "hq_policy_templates",
          { organization_id: a.organization_id, template_id: b.template_id },
          {
            version_number: b.version_number,
            join_radius_metres: b.join_radius_metres,
            arrival_radius_metres: b.arrival_radius_metres,
            call_grace_seconds: b.call_grace_seconds,
            allow_join_override: b.allow_join_override,
            allow_arrival_override: b.allow_arrival_override,
            allow_grace_override: b.allow_grace_override,
            created_at: new Date(),
          },
        );
        result = { template_id: b.template_id };
        break;
      case "publish_effective_store_policy": {
        const t = await one(
          c,
          "SELECT * FROM hq_policy_templates WHERE organization_id=$1 AND template_id=$2",
          [a.organization_id, b.template_id],
        );
        requireThat(t, "Unknown policy template");
        for (const [field, flag] of [
          ["join_radius_metres", "allow_join_override"],
          ["arrival_radius_metres", "allow_arrival_override"],
          ["call_grace_seconds", "allow_grace_override"],
        ])
          requireThat(
            t[flag] || b[field] === t[field],
            "Head office fixed policy: " + field,
            403,
          );
        await create(
          "store_policy_versions",
          { store_id: st, policy_id: b.policy_id },
          {
            source_template_id: b.template_id,
            version_number: b.version_number,
            join_radius_metres: b.join_radius_metres,
            arrival_radius_metres: b.arrival_radius_metres,
            call_grace_seconds: b.call_grace_seconds,
            max_party_size: 8,
            max_deferrals: null,
            created_at: new Date(),
          },
        );
        result = { policy_id: b.policy_id };
        resource = b.policy_id;
        break;
      }
      case "set_store_opening_period":
        await create(
          "store_opening_periods",
          { store_id: st, period_id: b.period_id },
          {
            weekday: b.weekday,
            opens_minute: b.opens_minute,
            closes_minute: b.closes_minute,
          },
        );
        result = { period_id: b.period_id };
        resource = b.period_id;
        break;
      case "rotate_store_join_qr": {
        await lock(c, "qr:" + st);
        const prior = await one(
          c,
          "SELECT * FROM store_join_qr_versions WHERE store_id=$1 AND qr_id=$2",
          [st, b.qr_id],
        );
        if (prior) {
          requireThat(!prior.revoked_at, "QR already revoked");
          changed = false;
        } else {
          await c.query(
            "UPDATE store_join_qr_versions SET revoked_at=now() WHERE store_id=$1 AND revoked_at IS NULL",
            [st],
          );
          await insert(c, "store_join_qr_versions", {
            store_id: st,
            qr_id: b.qr_id,
            created_at: new Date(),
          });
        }
        result = { qr_id: b.qr_id };
        resource = b.qr_id;
        break;
      }
      case "create_manager_account": {
        requireThat(
          b.initial_password.length >= 12 && /^\S+@\S+\.\S+$/.test(b.email),
          "Email and 12-character password required",
          400,
        );
        await lock(c, "account:" + b.account_id);
        const prior = await one(
          c,
          "SELECT * FROM operator_accounts WHERE account_id=$1",
          [b.account_id],
        );
        if (prior) {
          requireThat(
            prior.organization_id === a.organization_id &&
              prior.login_digest ===
                digest("login", b.email.trim().toLowerCase()) &&
              prior.display_name === b.display_name &&
              (await verifyPassword(
                prior.password_verifier,
                b.initial_password,
              )),
            "Account ID already used",
          );
          requireThat(
            await one(
              c,
              "SELECT 1 FROM operator_store_grants WHERE store_id=$1 AND account_id=$2",
              [st, b.account_id],
            ),
            "Account grant differs",
          );
          changed = false;
        } else {
          await insert(c, "operator_accounts", {
            account_id: b.account_id,
            organization_id: a.organization_id,
            login_digest: digest("login", b.email.trim().toLowerCase()),
            email_ciphertext: encrypt(b.email, "email"),
            display_name: b.display_name,
            password_verifier: await hashPassword(b.initial_password),
            account_role: "manager",
            created_at: new Date(),
          });
          await insert(c, "operator_store_grants", {
            store_id: st,
            account_id: b.account_id,
            granted_at: new Date(),
          });
        }
        result = { account_id: b.account_id };
        resource = b.account_id;
        break;
      }
      case "disable_operator_account": {
        requireThat(
          b.account_id !== a.account_id,
          "Cannot disable your active account",
        );
        const target = await one(
          c,
          "SELECT * FROM operator_accounts WHERE account_id=$1 AND organization_id=$2",
          [b.account_id, a.organization_id],
        );
        requireThat(
          target?.account_role === "manager",
          "Only manager accounts can be disabled",
        );
        await c.query(
          "UPDATE operator_accounts SET disabled_at=now() WHERE account_id=$1",
          [b.account_id],
        );
        await c.query(
          "UPDATE operator_sessions SET revoked_at=now() WHERE account_id=$1 AND revoked_at IS NULL",
          [b.account_id],
        );
        result = { account_id: b.account_id, disabled: true };
        break;
      }
      case "register_store_device":
        await create(
          "store_devices",
          { store_id: st, device_id: b.device_id },
          {
            device_kind: b.device_kind,
            device_label: b.device_label,
            registered_at: new Date(),
          },
        );
        result = { device_id: b.device_id };
        resource = b.device_id;
        break;
      case "rotate_device_credential": {
        requireThat(
          await one(
            c,
            "SELECT 1 FROM store_devices WHERE store_id=$1 AND device_id=$2 AND revoked_at IS NULL",
            [st, b.device_id],
          ),
          "Device not enrolled",
        );
        await lock(c, "device:" + b.device_id);
        await c.query(
          "UPDATE device_credentials SET revoked_at=now() WHERE store_id=$1 AND device_id=$2 AND revoked_at IS NULL",
          [st, b.device_id],
        );
        const raw = token(),
          expiry = new Date(Date.now() + 30 * 86400000);
        await insert(c, "device_credentials", {
          store_id: st,
          credential_id: uid(),
          device_id: b.device_id,
          token_hash: digest("device", raw),
          created_at: new Date(),
          expires_at: expiry,
        });
        result = {
          device_id: b.device_id,
          device_token: raw,
          expires_at: expiry,
        };
        resource = b.device_id;
        break;
      }
      case "set_tablet_store_pin":
        requireThat(
          /^\d{6,12}$/.test(b.new_pin),
          "PIN must contain 6–12 digits",
          400,
        );
        await c.query(
          "INSERT INTO store_pin_verifiers VALUES($1,$2,now()) ON CONFLICT(store_id) DO UPDATE SET pin_verifier=EXCLUDED.pin_verifier,rotated_at=EXCLUDED.rotated_at",
          [st, await hashPassword(b.new_pin)],
        );
        result = { store_id: st };
        break;
      case "issue_partner_credential": {
        const prior = await one(
          c,
          "SELECT * FROM partner_credentials WHERE partner_id=$1",
          [b.partner_id],
        );
        requireThat(
          !prior || prior.organization_id === a.organization_id,
          "Partner belongs to another organization",
          403,
        );
        const raw = token(),
          expiry = new Date(Date.now() + 30 * 86400000);
        if (prior)
          await c.query(
            "UPDATE partner_credentials SET token_hash=$2,partner_name=$3,expires_at=$4,revoked_at=NULL WHERE partner_id=$1",
            [b.partner_id, digest("partner", raw), b.partner_name, expiry],
          );
        else
          await insert(c, "partner_credentials", {
            partner_id: b.partner_id,
            organization_id: a.organization_id,
            partner_name: b.partner_name,
            token_hash: digest("partner", raw),
            created_at: new Date(),
            expires_at: expiry,
          });
        result = {
          partner_id: b.partner_id,
          partner_token: raw,
          expires_at: expiry,
        };
        break;
      }
      case "set_store_waitlist_state":
        requireThat(
          ["open", "waitlist_closed", "closed"].includes(b.waitlist_state),
          "Invalid store state",
          400,
        );
        await c.query("UPDATE stores SET store_status=$2 WHERE store_id=$1", [
          st,
          b.waitlist_state,
        ]);
        result = { store_status: b.waitlist_state };
        break;
      case "open_operating_session": {
        await lock(c, "open:" + st);
        const existing = await one(
          c,
          "SELECT * FROM operating_sessions WHERE store_id=$1 AND session_id=$2",
          [st, b.session_id],
        );
        if (existing) {
          for (const k of ["owner_device_id", "layout_id", "policy_id"])
            requireThat(existing[k] === b[k], "Session ID reused");
          requireThat(!existing.closed_at, "Session already closed");
          changed = false;
        } else {
          requireThat(
            await one(
              c,
              "SELECT 1 FROM store_devices WHERE store_id=$1 AND device_id=$2 AND device_kind='tablet' AND revoked_at IS NULL",
              [st, b.owner_device_id],
            ),
            "Owner tablet not available",
          );
          requireThat(
            await one(
              c,
              "SELECT 1 FROM layout_versions WHERE store_id=$1 AND layout_id=$2 AND layout_status='published'",
              [st, b.layout_id],
            ),
            "Published layout required",
          );
          requireThat(
            await one(
              c,
              "SELECT 1 FROM store_policy_versions WHERE store_id=$1 AND policy_id=$2",
              [st, b.policy_id],
            ),
            "Policy not found",
          );
          const s = await insert(c, "operating_sessions", {
            store_id: st,
            session_id: b.session_id,
            business_date: b.business_date,
            layout_id: b.layout_id,
            policy_id: b.policy_id,
            owner_device_id: b.owner_device_id,
            authority_epoch: 1,
            next_queue_sequence: 1,
            next_ticket_number: 1,
            last_event_sequence: 0,
            state_version: 0,
            opened_at: new Date(),
          });
          await event(c, s, null, "session_opened", null, null, a);
        }
        result = { session_id: b.session_id, authority_epoch: 1 };
        resource = b.session_id;
        break;
      }
      case "close_operating_session": {
        await lock(c, "open:" + st);
        const old = await one(
          c,
          "SELECT * FROM operating_sessions WHERE store_id=$1 AND session_id=$2 FOR UPDATE",
          [st, b.session_id],
        );
        requireThat(old, "Session not found", 404);
        if (old.closed_at) {
          changed = false;
          result = { session_id: b.session_id };
          break;
        }
        const s = await session(c, st);
        requireThat(s.session_id === b.session_id, "Session changed");
        const pending = await one(
          c,
          "SELECT (SELECT count(*) FROM queue_groups WHERE store_id=$1 AND session_id=$2 AND group_status IN ('waiting','called','seated'))+(SELECT count(*) FROM physical_table_facts WHERE store_id=$1 AND quarantine_active)+(SELECT count(*) FROM device_sync_commands WHERE store_id=$1 AND session_id=$2 AND sync_status IN ('received','conflict')) AS n",
          [st, b.session_id],
        );
        requireThat(
          Number(pending.n) === 0,
          "Drain queue, tables and sync conflicts before closing",
        );
        await event(c, s, null, "session_closed", null, null, a);
        await c.query(
          "UPDATE operating_sessions SET closed_at=now() WHERE store_id=$1 AND session_id=$2",
          [st, s.session_id],
        );
        result = { session_id: b.session_id };
        resource = b.session_id;
        break;
      }
      case "resolve_sync_conflict": {
        requireThat(
          [
            "acknowledged",
            "physical_verified",
            "discarded_after_review",
          ].includes(b.resolution_code),
          "Select a reviewed resolution",
          400,
        );
        const s = await session(c, st);
        const conflict = await one(
          c,
          "SELECT * FROM sync_conflicts WHERE store_id=$1 AND conflict_id=$2 FOR UPDATE",
          [st, b.conflict_id],
        );
        requireThat(conflict, "Conflict not found", 404);
        if (conflict.conflict_status === "resolved") {
          changed = false;
          result = { conflict_id: b.conflict_id };
          break;
        }
        const facts = await rows(
          c,
          "SELECT * FROM physical_table_facts WHERE store_id=$1 AND sync_command_id=$2",
          [st, conflict.sync_command_id],
        );
        for (const f of facts)
          requireThat(
            !(await one(
              c,
              "SELECT 1 FROM table_allocations WHERE store_id=$1 AND table_id=$2 AND released_at IS NULL",
              [st, f.table_id],
            )),
            "Inspect and clear canonical occupancy first",
          );
        await c.query(
          "UPDATE sync_conflicts SET conflict_status='resolved',resolved_at=now(),resolution_code=$3,resolver_account_id=$4 WHERE store_id=$1 AND conflict_id=$2",
          [st, b.conflict_id, b.resolution_code, a.account_id],
        );
        await c.query(
          "UPDATE physical_table_facts SET quarantine_active=false WHERE store_id=$1 AND sync_command_id=$2",
          [st, conflict.sync_command_id],
        );
        await c.query(
          "UPDATE device_sync_commands SET sync_status='rejected',resolved_at=now(),reason_code=$3 WHERE store_id=$1 AND sync_command_id=$2",
          [st, conflict.sync_command_id, b.resolution_code],
        );
        await c.query(
          "UPDATE operating_sessions SET sync_snapshot_revision=sync_snapshot_revision+1 WHERE store_id=$1 AND session_id=$2",
          [st, s.session_id],
        );
        await event(c, s, null, "conflict_resolved", null, null, a);
        result = { conflict_id: b.conflict_id };
        resource = b.conflict_id;
        break;
      }
      default:
        throw new Error("Unregistered administrator operation " + name);
    }
    if (changed) await audit(c, a, st || null, name, resource);
    return result;
  });
}
