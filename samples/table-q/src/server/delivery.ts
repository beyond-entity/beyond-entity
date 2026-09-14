import { tx, one, rows, insert, pool, requireThat } from "./db";
import { uid, digest, canonical } from "./security";
import { simulatedEffect, controls } from "./simulator";
export async function heartbeat(c: any, d: any, b: any) {
  requireThat(
    Number.isSafeInteger(b.heartbeat_sequence) &&
      b.heartbeat_sequence >= 0 &&
      ["none", "paper_out", "jam", "adapter_error"].includes(b.fault_code),
    "Invalid heartbeat",
    400,
  );
  const previous = await one(
    c,
    "SELECT * FROM device_health WHERE store_id=$1 AND device_id=$2 FOR UPDATE",
    [d.store_id, d.device_id],
  );
  if (previous && previous.heartbeat_sequence >= b.heartbeat_sequence) {
    requireThat(
      previous.heartbeat_sequence > b.heartbeat_sequence ||
        (previous.fault_code === b.fault_code &&
          previous.device_time.toISOString() ===
            new Date(b.device_time).toISOString()),
      "Heartbeat payload changed",
    );
    return { server_time: previous.last_seen_at };
  }
  const now = new Date();
  await c.query(
    "INSERT INTO device_health VALUES($1,$2,$3,$4,$5,$6,'online') ON CONFLICT(store_id,device_id) DO UPDATE SET heartbeat_sequence=EXCLUDED.heartbeat_sequence,last_seen_at=EXCLUDED.last_seen_at,device_time=EXCLUDED.device_time,fault_code=EXCLUDED.fault_code,connectivity_status='online'",
    [
      d.store_id,
      d.device_id,
      b.heartbeat_sequence,
      now,
      b.device_time,
      b.fault_code,
    ],
  );
  if (
    (previous?.connectivity_status === "stale"
      ? "unresponsive"
      : previous?.fault_code || "none") !== b.fault_code
  )
    await insert(c, "device_fault_events", {
      store_id: d.store_id,
      fault_event_id: uid(),
      device_id: d.device_id,
      heartbeat_sequence: b.heartbeat_sequence,
      previous_fault_code:
        previous?.connectivity_status === "stale"
          ? "unresponsive"
          : previous?.fault_code || "none",
      fault_code: b.fault_code,
      received_at: now,
    });
  return { server_time: now };
}
export async function acknowledge(b: any) {
  return tx(async (c) => {
    const j = await one(
      c,
      "SELECT * FROM delivery_jobs WHERE store_id=$1 AND job_id=$2 FOR UPDATE",
      [b.store_id, b.job_id],
    );
    requireThat(j, "Unknown delivery", 404);
    const a = await one(
      c,
      "SELECT * FROM delivery_attempts WHERE store_id=$1 AND job_id=$2 AND attempt_id=$3",
      [b.store_id, b.job_id, b.attempt_id],
    );
    requireThat(a, "Unknown attempt", 404);
    const source =
        j.channel === "call_bell"
          ? "device_simulator"
          : "notification_simulator",
      hash = digest("receipt", b.source_event_id);
    const prev = await one(
      c,
      "SELECT * FROM delivery_receipts WHERE source_kind=$1 AND source_event_digest=$2",
      [source, hash],
    );
    if (prev) {
      requireThat(
        prev.job_id === b.job_id &&
          prev.attempt_id === b.attempt_id &&
          prev.receipt_status === b.receipt_status,
        "Receipt payload changed",
      );
      return { applied: prev.applied };
    }
    const live = await one(
      c,
      "SELECT 1 FROM group_calls WHERE store_id=$1 AND call_id=$2 AND call_status='active'",
      [j.store_id, j.call_id],
    );
    const apply =
      !!live &&
      a.attempt_number === j.attempt_count &&
      ["leased", "accepted", "retry_wait"].includes(j.job_status);
    await insert(c, "delivery_receipts", {
      store_id: j.store_id,
      receipt_id: uid(),
      job_id: j.job_id,
      attempt_id: a.attempt_id,
      source_kind: source,
      source_event_digest: hash,
      receipt_status: b.receipt_status,
      reported_at: b.reported_at,
      received_at: new Date(),
      applied: apply,
    });
    if (apply)
      await c.query(
        "UPDATE delivery_jobs SET job_status=$3,delivered_at=CASE WHEN $3='delivered' THEN now() ELSE NULL END,lease_token=NULL,lease_until=NULL WHERE store_id=$1 AND job_id=$2",
        [
          j.store_id,
          j.job_id,
          b.receipt_status === "delivered" ? "delivered" : "failed",
        ],
      );
    return { applied: apply };
  });
}
export async function dispatchOne() {
  const job = await tx(async (c) => {
    const j = await one(
      c,
      `SELECT j.* FROM delivery_jobs j WHERE j.job_status IN ('queued','retry_wait') AND j.next_attempt_at<=now() AND NOT EXISTS(SELECT 1 FROM delivery_jobs earlier WHERE earlier.store_id=j.store_id AND earlier.lane_key=j.lane_key AND earlier.event_sequence<j.event_sequence AND earlier.job_status IN ('queued','retry_wait','leased','accepted','uncertain')) ORDER BY j.next_attempt_at FOR UPDATE OF j SKIP LOCKED LIMIT 1`,
    );
    if (!j) return;
    const live = await one(
      c,
      "SELECT 1 FROM group_calls c JOIN operating_sessions s ON s.store_id=c.store_id AND s.session_id=$3 WHERE c.store_id=$1 AND c.call_id=$2 AND c.call_status='active' AND s.closed_at IS NULL",
      [j.store_id, j.call_id, j.session_id],
    );
    if (!live || j.expires_at <= new Date()) {
      await c.query(
        "UPDATE delivery_jobs SET job_status=$3 WHERE store_id=$1 AND job_id=$2",
        [j.store_id, j.job_id, live ? "expired" : "obsolete"],
      );
      return;
    }
    const lease = uid(),
      attempt = uid();
    await c.query(
      "UPDATE delivery_jobs SET job_status='leased',attempt_count=attempt_count+1,lease_token=$3,lease_until=now()+interval '30 seconds' WHERE store_id=$1 AND job_id=$2",
      [j.store_id, j.job_id, lease],
    );
    await insert(c, "delivery_attempts", {
      store_id: j.store_id,
      attempt_id: attempt,
      job_id: j.job_id,
      attempt_number: j.attempt_count + 1,
      lease_token: lease,
      started_at: new Date(),
      outcome: "started",
    });
    return {
      ...j,
      lease_token: lease,
      attempt_id: attempt,
      attempt_count: j.attempt_count + 1,
    };
  });
  if (!job) return false;
  try {
    const current = await one(
      pool,
      "SELECT 1 FROM delivery_jobs j JOIN group_calls c USING(store_id,call_id) WHERE j.store_id=$1 AND j.job_id=$2 AND j.lease_token=$3 AND j.lease_until>now() AND c.call_status='active'",
      [job.store_id, job.job_id, job.lease_token],
    );
    requireThat(current, "Delivery became obsolete");
    const effect = simulatedEffect(job);
    await tx(async (c) => {
      await c.query(
        "UPDATE delivery_attempts SET finished_at=now(),outcome='delivered',provider_request_id=$3 WHERE store_id=$1 AND attempt_id=$2",
        [job.store_id, job.attempt_id, effect.receipt_event_id],
      );
    });
    await acknowledge({
      store_id: job.store_id,
      job_id: job.job_id,
      attempt_id: job.attempt_id,
      source_event_id: effect.receipt_event_id,
      receipt_status: "delivered",
      reported_at: effect.completed_at,
    });
  } catch {
    await tx(async (c) => {
      await c.query(
        "UPDATE delivery_attempts SET finished_at=now(),outcome='retryable_failure',error_code='simulator_unavailable' WHERE store_id=$1 AND attempt_id=$2",
        [job.store_id, job.attempt_id],
      );
      await c.query(
        "UPDATE delivery_jobs SET job_status=$4,lease_token=NULL,lease_until=NULL,next_attempt_at=now()+($5*interval '1 second'),terminal_reason=CASE WHEN $4='failed' THEN 'retry_exhausted' ELSE NULL END WHERE store_id=$1 AND job_id=$2 AND lease_token=$3",
        [
          job.store_id,
          job.job_id,
          job.lease_token,
          job.attempt_count >= 5 ? "failed" : "retry_wait",
          Math.min(60, 2 ** job.attempt_count),
        ],
      );
    });
  }
  return true;
}
export async function recovery() {
  await tx(async (c) => {
    await c.query(
      "UPDATE delivery_attempts a SET outcome='unknown',finished_at=now() FROM delivery_jobs j WHERE j.store_id=a.store_id AND j.job_id=a.job_id AND j.lease_token=a.lease_token AND j.job_status='leased' AND j.lease_until<now() AND a.outcome='started'",
    );
    await c.query(
      "UPDATE delivery_jobs SET job_status=CASE WHEN attempt_count>=5 THEN 'failed' ELSE 'retry_wait' END,lease_token=NULL,lease_until=NULL,next_attempt_at=now() WHERE job_status='leased' AND lease_until<now()",
    );
    await c.query(
      "UPDATE delivery_jobs j SET job_status='obsolete',lease_token=NULL,lease_until=NULL FROM group_calls c WHERE j.store_id=c.store_id AND j.call_id=c.call_id AND c.call_status<>'active' AND j.job_status IN ('queued','retry_wait','accepted','leased')",
    );
  });
}
export async function purgeExpired() {
  await tx(async (c) => {
    await c.query("DELETE FROM command_secret_replays WHERE expires_at<=now()");
    await c.query("DELETE FROM api_rate_windows WHERE expires_at<=now()");
  });
}
export async function detectStaleDevices() {
  await tx(async (c) => {
    const stale = await rows(
      c,
      "SELECT * FROM device_health WHERE connectivity_status='online' AND last_seen_at<now()-interval '30 seconds' FOR UPDATE",
    );
    for (const d of stale) {
      await insert(c, "device_fault_events", {
        store_id: d.store_id,
        fault_event_id: uid(),
        device_id: d.device_id,
        heartbeat_sequence: d.heartbeat_sequence,
        previous_fault_code: d.fault_code,
        fault_code: "unresponsive",
        received_at: new Date(),
      });
      await c.query(
        "UPDATE device_health SET connectivity_status='stale' WHERE store_id=$1 AND device_id=$2",
        [d.store_id, d.device_id],
      );
    }
  });
}
export async function maintenance() {
  await purgeExpired();
  await detectStaleDevices();
}
export async function simulateHeartbeats() {
  if (process.env.SIMULATOR_ENABLED !== "true") return;
  const all = controls();
  for (const d of await rows(
    pool,
    "SELECT * FROM store_devices WHERE device_kind<>'tablet' AND revoked_at IS NULL",
  )) {
    const ctl = all[d.device_id];
    if (ctl?.offline) continue;
    await tx(async (c) => {
      await c.query(
        "SELECT 1 FROM store_devices WHERE store_id=$1 AND device_id=$2 FOR UPDATE",
        [d.store_id, d.device_id],
      );
      await heartbeat(c, d, {
        heartbeat_sequence: Date.now(),
        device_time: new Date(),
        fault_code: ctl?.fault_code || "none",
      });
    });
  }
}
