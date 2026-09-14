import { pool } from "./db";
import {
  dispatchOne,
  recovery,
  purgeExpired,
  detectStaleDevices,
  simulateHeartbeats,
} from "./delivery";
import { reconcileBatch } from "./sync";
let stopping = false;
const timers: NodeJS.Timeout[] = [];
function every(ms: number, fn: () => Promise<any>) {
  let busy = false;
  const run = async () => {
    if (busy || stopping) return;
    busy = true;
    try {
      await fn();
    } catch (e: any) {
      console.error("Worker operation failed:", e.code || e.name);
    } finally {
      busy = false;
    }
  };
  void run();
  timers.push(setInterval(run, ms));
}
every(1000, async () => {
  for (let i = 0; i < 8; i++) if (!(await dispatchOne())) break;
});
every(2000, reconcileBatch);
every(5000, recovery);
every(10000, simulateHeartbeats);
every(10000, detectStaleDevices);
every(60000, purgeExpired);
console.log(
  "TableQ worker running: delivery, recovery, offline reconciliation and device simulation.",
);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, async () => {
    stopping = true;
    timers.forEach(clearInterval);
    await pool.end();
    process.exit(0);
  });
