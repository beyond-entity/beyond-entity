import "dotenv/config";
import pg from "pg";
pg.types.setTypeParser(20, (value) => Number(value));
// Reporting explicitly emits UTC timestamp-without-zone buckets.
pg.types.setTypeParser(1114, (value) => value.replace(" ", "T") + "Z");
export type DB = pg.PoolClient;
const url = new URL(process.env.DATABASE_URL || "postgresql://invalid/invalid");
if (url.pathname != "/table_q_by_code")
  throw new Error("DATABASE_URL must target table_q_by_code");
export const pool = new pg.Pool({
  connectionString: url.toString(),
  max: 12,
  connectionTimeoutMillis: 5000,
  statement_timeout: 10000,
  idle_in_transaction_session_timeout: 15000,
});
export const rows = async (c: any, sql: string, args: any[] = []) =>
  (await c.query(sql, args)).rows;
export const one = async (c: any, sql: string, args: any[] = []) =>
  (await rows(c, sql, args))[0];
export async function tx<T>(fn: (c: DB) => Promise<T>): Promise<T> {
  const c = await pool.connect();
  try {
    await c.query("BEGIN");
    const v = await fn(c);
    await c.query("COMMIT");
    return v;
  } catch (e) {
    await c.query("ROLLBACK");
    throw e;
  } finally {
    c.release();
  }
}
export async function insert(
  c: any,
  table: string,
  values: Record<string, any>,
) {
  const keys = Object.keys(values).filter((k) => values[k] !== undefined);
  return one(
    c,
    `INSERT INTO "${table}" (${keys.map((k) => `"${k}"`).join(",")}) VALUES (${keys.map((_, i) => "$" + (i + 1)).join(",")}) RETURNING *`,
    keys.map((k) => values[k]),
  );
}
export const lock = async (c: any, key: string) => {
  await c.query("SELECT pg_advisory_xact_lock(hashtextextended($1,0))", [key]);
};
export class HttpError extends Error {
  constructor(
    public statusCode: number,
    message: string,
  ) {
    super(message);
  }
}
export function requireThat(
  ok: any,
  message: string,
  status = 409,
): asserts ok {
  if (!ok) throw new HttpError(status, message);
}
