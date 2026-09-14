import { DatabaseSync } from "node:sqlite";
import { mkdirSync, readFileSync, writeFileSync, renameSync } from "node:fs";
import { uid, digest, canonical } from "./security";
import { requireThat } from "./db";
mkdirSync("data", { recursive: true });
const db = new DatabaseSync("data/simulators.sqlite");
db.exec("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;");
for (const table of ["device_effect_journal", "notification_effect_journal"])
  db.exec(
    `CREATE TABLE IF NOT EXISTS ${table}(job_id TEXT PRIMARY KEY,store_id TEXT NOT NULL,group_id TEXT NOT NULL,effect_kind TEXT NOT NULL,request_digest TEXT NOT NULL,effect_status TEXT NOT NULL CHECK(effect_status IN ('accepted','completed','failed')),accepted_at TEXT NOT NULL,completed_at TEXT,receipt_event_id TEXT NOT NULL)`,
  );
export function controls(): Record<string, any> {
  try {
    return JSON.parse(readFileSync("data/simulator-controls.json", "utf8"));
  } catch {
    return {};
  }
}
export function setControl(id: string, control: any) {
  requireThat(
    ["none", "paper_out", "jam", "adapter_error"].includes(control.fault_code),
    "Invalid fault",
    400,
  );
  const all = controls();
  all[id] = { fault_code: control.fault_code, offline: !!control.offline };
  writeFileSync("data/simulator-controls.tmp", JSON.stringify(all), {
    mode: 0o600,
  });
  renameSync("data/simulator-controls.tmp", "data/simulator-controls.json");
}
export function simulatedEffect(job: any, kind?: string) {
  requireThat(
    process.env.SIMULATOR_ENABLED === "true",
    "Simulator disabled",
    503,
  );
  const table =
    job.channel === "customer_notification"
      ? "notification_effect_journal"
      : "device_effect_journal";
  const request = {
    job_id: job.job_id,
    store_id: job.store_id,
    group_id: job.group_id,
    kind: kind || job.channel,
  };
  const hash = digest("effect", canonical(request));
  db.exec("BEGIN IMMEDIATE");
  try {
    let row: any = db
      .prepare(`SELECT * FROM ${table} WHERE job_id=?`)
      .get(job.job_id);
    if (row) {
      requireThat(
        row.request_digest === hash,
        "Simulator job payload mismatch",
      );
      db.exec("COMMIT");
      return row;
    }
    const ctl = controls()[job.target_device_id];
    requireThat(
      !ctl?.offline && (!ctl?.fault_code || ctl.fault_code === "none"),
      "Simulator device unavailable",
      503,
    );
    const now = new Date().toISOString();
    row = {
      ...request,
      request_digest: hash,
      effect_status: "completed",
      accepted_at: now,
      completed_at: now,
      receipt_event_id: uid(),
    };
    db.prepare(`INSERT INTO ${table} VALUES(?,?,?,?,?,?,?,?,?)`).run(
      job.job_id,
      job.store_id,
      job.group_id,
      request.kind,
      hash,
      "completed",
      now,
      now,
      row.receipt_event_id,
    );
    db.exec("COMMIT");
    return row;
  } catch (e) {
    db.exec("ROLLBACK");
    throw e;
  }
}
export function effectHistory(store: string) {
  return ["device_effect_journal", "notification_effect_journal"].flatMap((t) =>
    db
      .prepare(
        `SELECT job_id,effect_kind,effect_status,accepted_at,completed_at FROM ${t} WHERE store_id=? ORDER BY accepted_at DESC LIMIT 50`,
      )
      .all(store),
  );
}
