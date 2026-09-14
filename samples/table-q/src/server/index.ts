import { buildApp } from "./app";
import { pool } from "./db";
const app = await buildApp();
await app.listen({
  port: Number(process.env.PORT || 3100),
  host: process.env.HOST || "127.0.0.1",
});
console.log(`TableQ server: http://localhost:${process.env.PORT || 3100}`);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, async () => {
    await app.close();
    await pool.end();
    process.exit(0);
  });
