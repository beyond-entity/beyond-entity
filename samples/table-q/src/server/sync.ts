import { tx, one, rows, insert, requireThat, lock, pool } from "./db";
import { device, digest, canonical, uid } from "./security";
import { session, callGroup, transition, clearTable } from "./queue";
export async function receiveOffline(r: any, b: any) {
  return tx(async (c) => {
    const d = await device(r, c, b.store_id);
    requireThat(
      d.device_kind === "tablet" && d.device_id === b.device_id,
      "Wrong device",
      403,
    );
    requireThat(
      ["call", "seat", "clear"].includes(b.operation) &&
        Number.isSafeInteger(b.device_sequence) &&
        b.device_sequence > 0,
      "Invalid offline operation",
      400,
    );
    const at = new Date(b.occurred_at);
    requireThat(Number.isFinite(at.getTime()), "Invalid occurrence time", 400);
    const s = await session(c, b.store_id);
    requireThat(
      await one(
        c,
        "SELECT 1 FROM operating_sessions WHERE store_id=$1 AND session_id=$2",
        [b.store_id, b.session_id],
      ),
      "Unknown source session",
    );
    const hash = digest("offline", canonical(b));
    await lock(c, "sync:" + b.device_id + b.session_id);
    const prior = await one(
      c,
      "SELECT * FROM device_sync_commands WHERE store_id=$1 AND (sync_command_id=$2 OR (device_id=$3 AND session_id=$4 AND authority_epoch=$5 AND device_sequence=$6))",
      [
        b.store_id,
        b.sync_command_id,
        b.device_id,
        b.session_id,
        b.authority_epoch,
        b.device_sequence,
      ],
    );
    if (prior) {
      requireThat(
        prior.command_digest === hash &&
          prior.sync_command_id === b.sync_command_id,
        "Offline sequence/payload mismatch",
      );
      return {
        sync_command_id: prior.sync_command_id,
        sync_status: prior.sync_status,
      };
    }
    await c.query(
      "INSERT INTO device_sync_cursors VALUES($1,$2,$3,$4,0,0,now()) ON CONFLICT DO NOTHING",
      [b.store_id, b.device_id, b.session_id, b.authority_epoch],
    );
    const cursor = await one(
      c,
      "SELECT * FROM device_sync_cursors WHERE store_id=$1 AND device_id=$2 AND session_id=$3 AND authority_epoch=$4 FOR UPDATE",
      [b.store_id, b.device_id, b.session_id, b.authority_epoch],
    );
    requireThat(
      b.device_sequence === cursor.last_received_sequence + 1,
      "Offline sequence gap",
    );
    requireThat(
      await one(
        c,
        "SELECT 1 FROM queue_groups WHERE store_id=$1 AND group_id=$2 AND session_id=$3",
        [b.store_id, b.group_id, b.session_id],
      ),
      "Unknown offline group",
    );
    requireThat(
      await one(
        c,
        "SELECT 1 FROM dining_tables WHERE store_id=$1 AND table_id=$2",
        [b.store_id, b.table_id],
      ),
      "Unknown offline table",
    );
    const stale =
      s.session_id !== b.session_id ||
      s.authority_epoch !== b.authority_epoch ||
      s.owner_device_id !== b.device_id;
    const status = stale
      ? b.operation === "call"
        ? "rejected"
        : "conflict"
      : "received";
    const row = await insert(c, "device_sync_commands", {
      ...b,
      command_digest: hash,
      sync_status: status,
      received_at: new Date(),
      resolved_at: status === "rejected" ? new Date() : null,
      reason_code: stale ? "obsolete_authority" : null,
    });
    if (b.operation !== "call") {
      await insert(c, "physical_table_facts", {
        store_id: b.store_id,
        fact_id: uid(),
        sync_command_id: b.sync_command_id,
        session_id: b.session_id,
        table_id: b.table_id,
        group_id: b.group_id,
        fact_kind: b.operation === "seat" ? "seated" : "cleared",
        occurred_at: at,
        recorded_at: new Date(),
        quarantine_active: true,
      });
      await c.query(
        "UPDATE operating_sessions SET sync_snapshot_revision=sync_snapshot_revision+1 WHERE store_id=$1 AND session_id=$2",
        [s.store_id, s.session_id],
      );
    }
    if (status === "conflict") await conflict(c, s, row, "obsolete_authority");
    await c.query(
      "UPDATE device_sync_cursors SET last_received_sequence=$5,updated_at=now() WHERE store_id=$1 AND device_id=$2 AND session_id=$3 AND authority_epoch=$4",
      [
        b.store_id,
        b.device_id,
        b.session_id,
        b.authority_epoch,
        b.device_sequence,
      ],
    );
    return { sync_command_id: b.sync_command_id, sync_status: status };
  });
}
async function conflict(c: any, s: any, b: any, reason: string) {
  await insert(c, "sync_conflicts", {
    store_id: b.store_id,
    conflict_id: uid(),
    sync_command_id: b.sync_command_id,
    server_version: s.state_version,
    reason_code: reason,
    conflict_status: "open",
    created_at: new Date(),
  });
  await c.query(
    "UPDATE device_sync_commands SET sync_status='conflict',reason_code=$3 WHERE store_id=$1 AND sync_command_id=$2",
    [b.store_id, b.sync_command_id, reason],
  );
}
export async function reconcileBatch() {
  const cursors = await rows(
    pool,
    "SELECT * FROM device_sync_cursors WHERE last_received_sequence>last_resolved_sequence LIMIT 30",
  );
  for (const cursor of cursors)
    await tx(async (c) => {
      const s = await one(
        c,
        "SELECT * FROM operating_sessions WHERE store_id=$1 AND session_id=$2 FOR UPDATE",
        [cursor.store_id, cursor.session_id],
      );
      if (!s) return;
      const policy = await one(
        c,
        "SELECT * FROM store_policy_versions WHERE store_id=$1 AND policy_id=$2",
        [s.store_id, s.policy_id],
      );
      Object.assign(s, policy);
      const cur = await one(
        c,
        "SELECT * FROM device_sync_cursors WHERE store_id=$1 AND device_id=$2 AND session_id=$3 AND authority_epoch=$4 FOR UPDATE",
        [
          cursor.store_id,
          cursor.device_id,
          cursor.session_id,
          cursor.authority_epoch,
        ],
      );
      const b = await one(
        c,
        "SELECT * FROM device_sync_commands WHERE store_id=$1 AND device_id=$2 AND session_id=$3 AND authority_epoch=$4 AND device_sequence=$5",
        [
          cur.store_id,
          cur.device_id,
          cur.session_id,
          cur.authority_epoch,
          cur.last_resolved_sequence + 1,
        ],
      );
      if (!b || b.sync_status === "conflict") return;
      if (b.sync_status === "received") {
        await c.query("SAVEPOINT reconcile_action");
        try {
          requireThat(
            !s.closed_at &&
              s.owner_device_id === b.device_id &&
              s.authority_epoch === b.authority_epoch &&
              s.layout_id === b.layout_id,
            "Authority changed",
          );
          requireThat(
            s.state_version === b.base_version,
            "Canonical state changed",
          );
          const g = await one(
            c,
            "SELECT * FROM queue_groups WHERE store_id=$1 AND group_id=$2",
            [s.store_id, b.group_id],
          );
          const at = new Date(b.occurred_at);
          const preceding = await one(
            c,
            "SELECT occurred_at FROM device_sync_commands WHERE store_id=$1 AND device_id=$2 AND session_id=$3 AND authority_epoch=$4 AND device_sequence=$5",
            [
              b.store_id,
              b.device_id,
              b.session_id,
              b.authority_epoch,
              b.device_sequence - 1,
            ],
          );
          requireThat(
            at >= s.opened_at &&
              at >= g.joined_at &&
              at <= b.received_at &&
              (!preceding || at >= preceding.occurred_at),
            "Invalid physical clock",
          );
          const actor = { device_id: b.device_id };
          if (b.operation === "call") await callGroup(c, s, actor, b, at, b);
          if (b.operation === "seat") {
            const call = await one(
              c,
              "SELECT c.*,a.allocation_id,a.table_id FROM group_calls c JOIN table_allocations a USING(store_id,call_id) WHERE c.store_id=$1 AND c.call_id=$2",
              [s.store_id, b.call_id],
            );
            requireThat(
              call &&
                call.table_id === b.table_id &&
                call.allocation_id === b.allocation_id &&
                at >= call.called_at,
              "Physical seat disagrees with hold",
            );
            await transition(
              c,
              s,
              g,
              "seat",
              { expected_call_id: b.call_id },
              actor,
              at,
            );
          }
          if (b.operation === "clear")
            await clearTable(
              c,
              s,
              { table_id: b.table_id, expected_allocation_id: b.allocation_id },
              actor,
              at,
            );
          await c.query(
            "UPDATE device_sync_commands SET sync_status='applied',resolved_at=now(),result_version=$3 WHERE store_id=$1 AND sync_command_id=$2",
            [s.store_id, b.sync_command_id, s.state_version],
          );
          await c.query(
            "UPDATE physical_table_facts SET quarantine_active=false WHERE store_id=$1 AND sync_command_id=$2",
            [s.store_id, b.sync_command_id],
          );
          await c.query(
            "UPDATE operating_sessions SET sync_snapshot_revision=sync_snapshot_revision+1 WHERE store_id=$1 AND session_id=$2",
            [s.store_id, s.session_id],
          );
        } catch (e: any) {
          await c.query("ROLLBACK TO SAVEPOINT reconcile_action");
          if (!e.statusCode) throw e;
          await conflict(c, s, b, e.message);
          return;
        }
      }
      await c.query(
        "UPDATE device_sync_cursors SET last_resolved_sequence=$5,updated_at=now() WHERE store_id=$1 AND device_id=$2 AND session_id=$3 AND authority_epoch=$4",
        [
          cur.store_id,
          cur.device_id,
          cur.session_id,
          cur.authority_epoch,
          b.device_sequence,
        ],
      );
    });
}
