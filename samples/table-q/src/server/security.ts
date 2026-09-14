import {
  createHmac,
  randomBytes,
  randomInt,
  randomUUID,
  createCipheriv,
  createDecipheriv,
  timingSafeEqual,
} from "node:crypto";
import argon2 from "argon2";
import { one, rows, tx, lock, insert, requireThat, pool } from "./db";
const secret = process.env.APP_SECRET || "";
const key = Buffer.from(process.env.ENCRYPTION_KEY || "", "hex");
if (secret.length < 64 || key.length !== 32)
  throw new Error("Run npm run setup to generate private cryptographic keys");
export const uid = randomUUID,
  token = () => randomBytes(32).toString("base64url"),
  code = () => String(randomInt(10000)).padStart(4, "0");
export const digest = (purpose: string, value: string) =>
  createHmac("sha256", secret)
    .update(purpose + "\0" + value)
    .digest("hex");
export const hashPassword = (s: string) =>
  argon2.hash(s, {
    type: argon2.argon2id,
    memoryCost: 19456,
    timeCost: 2,
    parallelism: 1,
  });
export const verifyPassword = async (hash: string, s: string) => {
  try {
    return await argon2.verify(hash, s);
  } catch {
    return false;
  }
};
export function seal(text: string, aad: string) {
  const nonce = randomBytes(12),
    cipher = createCipheriv("aes-256-gcm", key, nonce);
  cipher.setAAD(Buffer.from(aad));
  const data = Buffer.concat([cipher.update(text, "utf8"), cipher.final()]);
  return {
    ciphertext: data.toString("base64"),
    nonce: nonce.toString("base64"),
    auth_tag: cipher.getAuthTag().toString("base64"),
    key_version: 1,
  };
}
export function unseal(v: any, aad: string) {
  requireThat(String(v.key_version) === "1", "Unknown encryption key", 503);
  const decipher = createDecipheriv(
    "aes-256-gcm",
    key,
    Buffer.from(v.nonce, "base64"),
  );
  decipher.setAAD(Buffer.from(aad));
  decipher.setAuthTag(Buffer.from(v.auth_tag, "base64"));
  return Buffer.concat([
    decipher.update(Buffer.from(v.ciphertext, "base64")),
    decipher.final(),
  ]).toString("utf8");
}
export const encrypt = (s: string, aad: string) => JSON.stringify(seal(s, aad));
export const canonical = (v: any): string =>
  v === null
    ? "null"
    : Array.isArray(v)
      ? "[" + v.map(canonical).join(",") + "]"
      : typeof v === "object"
        ? "{" +
          Object.keys(v)
            .sort()
            .map((k) => JSON.stringify(k) + ":" + canonical(v[k]))
            .join(",") +
          "}"
        : JSON.stringify(v);
export const bearer = (r: any) =>
  (r.headers.authorization || "").replace(/^Bearer /, "");
export function signed(value: any) {
  const raw = Buffer.from(JSON.stringify(value)).toString("base64url");
  return raw + "." + digest("signed", raw);
}
export function unsign(s: string) {
  const [raw, mac] = s.split(".");
  const expected = digest("signed", raw || "");
  requireThat(
    mac?.length === expected.length &&
      timingSafeEqual(Buffer.from(mac), Buffer.from(expected)),
    "Invalid signed context",
    401,
  );
  let v;
  try {
    v = JSON.parse(Buffer.from(raw, "base64url").toString());
  } catch {
    requireThat(false, "Invalid context", 401);
  }
  requireThat(v.exp > Date.now(), "Context expired", 401);
  return v;
}
export const cookieOptions = {
  httpOnly: true,
  sameSite: "strict" as const,
  secure: (process.env.APP_ORIGIN || "").startsWith("https:"),
  path: "/",
};
export async function rate(scope: string, limit: number) {
  const allowed = await tx(async (c) => {
    await lock(c, "rate:" + scope);
    const start = new Date(Math.floor(Date.now() / 60000) * 60000);
    const d = digest("rate", scope);
    const r = await one(
      c,
      `INSERT INTO api_rate_windows VALUES ($1,$2,1,$3) ON CONFLICT(scope_digest,window_start) DO UPDATE SET request_count=api_rate_windows.request_count+1 RETURNING request_count`,
      [d, start, new Date(start.getTime() + 120000)],
    );
    return r.request_count <= limit;
  });
  requireThat(allowed, "Too many requests; try again shortly", 429);
}
export async function operator(
  r: any,
  c: any = pool,
  store?: string,
  hq = false,
) {
  const session = r.cookies.operator_session;
  requireThat(session, "Sign in required", 401);
  const a = await one(
    c,
    `SELECT a.*, s.operator_session_id FROM operator_sessions s JOIN operator_accounts a USING(account_id) WHERE s.token_hash=$1 AND s.revoked_at IS NULL AND s.expires_at>now() AND a.disabled_at IS NULL`,
    [digest("operator", session)],
  );
  requireThat(a, "Session expired", 401);
  requireThat(
    !hq || a.account_role === "head_office",
    "Head office permission required",
    403,
  );
  if (store) {
    const st = await one(
      c,
      "SELECT organization_id FROM stores WHERE store_id=$1",
      [store],
    );
    requireThat(
      st?.organization_id === a.organization_id,
      "Store access denied",
      403,
    );
    if (a.account_role !== "head_office")
      requireThat(
        await one(
          c,
          "SELECT 1 FROM operator_store_grants WHERE store_id=$1 AND account_id=$2 AND revoked_at IS NULL",
          [store, a.account_id],
        ),
        "Store access denied",
        403,
      );
  }
  return a;
}
export async function device(
  r: any,
  c: any = pool,
  store?: string,
  unlocked = false,
) {
  const raw = bearer(r);
  requireThat(raw, "Device enrollment required", 401);
  const d = await one(
    c,
    `SELECT d.* FROM device_credentials c JOIN store_devices d USING(store_id,device_id) WHERE c.token_hash=$1 AND c.revoked_at IS NULL AND c.expires_at>now() AND d.revoked_at IS NULL`,
    [digest("device", raw)],
  );
  requireThat(
    d && (!store || d.store_id === store),
    "Invalid device credential",
    401,
  );
  if (unlocked) {
    requireThat(d.device_kind === "tablet", "Tablet required", 403);
    const v = unsign(r.headers["x-tablet-unlock"] || "");
    const pin = await one(
      c,
      "SELECT rotated_at FROM store_pin_verifiers WHERE store_id=$1",
      [d.store_id],
    );
    requireThat(
      v.device === d.device_id &&
        v.credential === digest("device", raw) &&
        v.pin === pin?.rotated_at.toISOString(),
      "Unlock tablet again",
      401,
    );
    const s = await one(
      c,
      "SELECT * FROM operating_sessions WHERE store_id=$1 AND closed_at IS NULL",
      [d.store_id],
    );
    requireThat(
      s && s.owner_device_id === d.device_id && s.authority_epoch === v.epoch,
      "Tablet is not current authority",
      403,
    );
  }
  return d;
}
export async function staff(r: any, c: any, store: string) {
  return device(r, c, store, true);
}
export async function ticket(r: any, c: any, group: string, owner = false) {
  const raw = bearer(r) || r.cookies["watch_" + group];
  const a = await one(
    c,
    `SELECT * FROM ticket_access_grants WHERE group_id=$1 AND token_hash=$2 AND revoked_at IS NULL AND expires_at>now()`,
    [group, digest("ticket", raw || "")],
  );
  requireThat(
    a && (!owner || a.access_scope === "owner"),
    "Ticket access denied",
    401,
  );
  return a;
}
export async function audit(
  c: any,
  a: any,
  store: string | null,
  action: string,
  id: string,
) {
  await insert(c, "administrative_audit_events", {
    admin_event_id: uid(),
    organization_id: a.organization_id,
    actor_account_id: a.account_id,
    store_id: store,
    action_code: action,
    resource_id: id,
    occurred_at: new Date(),
  });
}
