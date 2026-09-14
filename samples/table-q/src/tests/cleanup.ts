import { readFileSync } from "node:fs";
import { pool, one, rows, tx } from "../server/db";
export async function cleanupAccount(account: string) {
  const a = await one(
    pool,
    "SELECT organization_id FROM operator_accounts WHERE account_id=$1",
    [account],
  );
  if (!a) return;
  await tx(async (c) => {
    const stores = await rows(
      c,
      "SELECT store_id FROM stores WHERE organization_id=$1",
      [a.organization_id],
    );
    const accounts = await rows(
      c,
      "SELECT account_id FROM operator_accounts WHERE organization_id=$1",
      [a.organization_id],
    );
    const manifest = JSON.parse(
      readFileSync("../db/schema_manifest.json", "utf8"),
    );
    const remaining = new Set<string>(Object.keys(manifest.tables));
    while (remaining.size) {
      const ready = [...remaining].filter(
        (t) =>
          !manifest.constraints.some(
            (x: any) =>
              x.type === "f" &&
              x.parent === t &&
              x.table !== t &&
              remaining.has(x.table),
          ),
      );
      if (!ready.length) throw new Error("Dependency cycle");
      for (const table of ready) {
        const columns = manifest.tables[table].map((x: any) => x.name);
        if (
          table === "administrative_audit_events" ||
          (!columns.includes("store_id") && columns.includes("organization_id"))
        )
          await c.query(`DELETE FROM "${table}" WHERE organization_id=$1`, [
            a.organization_id,
          ]);
        else if (columns.includes("store_id"))
          await c.query(
            `DELETE FROM "${table}" WHERE store_id=ANY($1::uuid[])`,
            [stores.map((s: any) => s.store_id)],
          );
        else if (columns.includes("account_id"))
          await c.query(
            `DELETE FROM "${table}" WHERE account_id=ANY($1::uuid[])`,
            [accounts.map((a: any) => a.account_id)],
          );
        remaining.delete(table);
      }
    }
  });
}
