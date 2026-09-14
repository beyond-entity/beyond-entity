import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, writeFileSync } from "node:fs";
if (existsSync(".env")) {
  console.log(".env already exists; kept existing settings.");
  process.exit(0);
}
let password = process.env.PGPASSWORD;
if (!password) {
  const env = JSON.parse(
    execFileSync(
      "/Applications/Docker.app/Contents/Resources/bin/docker",
      ["inspect", "tableq-postgres", "--format", "{{json .Config.Env}}"],
      { encoding: "utf8" },
    ),
  );
  password = env
    .find((x) => x.startsWith("POSTGRES_PASSWORD="))
    ?.slice("POSTGRES_PASSWORD=".length);
}
if (!password)
  throw new Error("Set PGPASSWORD or configure .env from .env.example.");
const values = {
  DATABASE_URL: `postgresql://tableq:${encodeURIComponent(password)}@127.0.0.1:5432/table_q_by_code`,
  PORT: "3100",
  HOST: "127.0.0.1",
  APP_ORIGIN: "http://localhost:5174",
  APP_SECRET: randomBytes(32).toString("hex"),
  ENCRYPTION_KEY: randomBytes(32).toString("hex"),
  SEED_EMAIL: "admin@tableq.local",
  SEED_PASSWORD: randomBytes(18).toString("base64url"),
  SIMULATOR_ENABLED: "true",
};
writeFileSync(
  ".env",
  Object.entries(values)
    .map(([k, v]) => `${k}=${v}`)
    .join("\n") + "\n",
  { mode: 0o600 },
);
console.log(
  "Created private .env with local PostgreSQL configuration and generated keys. Login credentials are SEED_EMAIL and SEED_PASSWORD in .env.",
);
