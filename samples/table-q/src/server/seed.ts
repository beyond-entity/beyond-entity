import { pool, tx, one, insert, requireThat } from "./db";
import { uid, digest, encrypt, hashPassword } from "./security";
export async function seed() {
  requireThat(
    (process.env.SEED_PASSWORD || "").length >= 16,
    "Configure SEED_PASSWORD with at least 16 characters",
    400,
  );
  return tx(async (c) => {
    const email = (
      process.env.SEED_EMAIL || "admin@tableq.local"
    ).toLowerCase();
    const existing = await one(
      c,
      "SELECT account_id FROM operator_accounts WHERE login_digest=$1",
      [digest("login", email)],
    );
    if (existing) return { existing: true };
    const org = uid(),
      account = uid();
    await insert(c, "organizations", {
      organization_id: org,
      organization_name: "TableQ Dining Company",
      created_at: new Date(),
    });
    await insert(c, "operator_accounts", {
      account_id: account,
      organization_id: org,
      login_digest: digest("login", email),
      email_ciphertext: encrypt(email, "email"),
      display_name: "TableQ Head Office",
      password_verifier: await hashPassword(process.env.SEED_PASSWORD!),
      account_role: "head_office",
      created_at: new Date(),
    });
    const template = uid();
    await insert(c, "hq_policy_templates", {
      organization_id: org,
      template_id: template,
      version_number: 1,
      join_radius_metres: 300,
      arrival_radius_metres: 50,
      call_grace_seconds: 300,
      allow_join_override: true,
      allow_arrival_override: true,
      allow_grace_override: false,
      created_at: new Date(),
    });
    for (const [i, name] of [
      "Gangnam Flagship",
      "Seongsu Kitchen",
      "Hannam Dining Room",
    ].entries()) {
      const st = uid(),
        layout = uid(),
        policy = uid(),
        tablet = uid();
      await insert(c, "stores", {
        store_id: st,
        organization_id: org,
        store_code:
          (process.env.SEED_PREFIX || "") + ["GN01", "SS02", "HN03"][i],
        store_name: name,
        address: [
          "12 Gangnam-daero, Seoul",
          "24 Seongsui-ro, Seoul",
          "18 Itaewon-ro, Seoul",
        ][i],
        time_zone: "Asia/Seoul",
        latitude: [37.4979, 37.5445, 37.5345][i],
        longitude: [127.0276, 127.0557, 126.9946][i],
        store_status: "open",
        created_at: new Date(),
      });
      await insert(c, "layout_versions", {
        store_id: st,
        layout_id: layout,
        version_number: 1,
        layout_status: "published",
        created_at: new Date(),
      });
      for (let row = 1; row <= 3; row++) {
        const rid = uid();
        await insert(c, "layout_rows", {
          store_id: st,
          row_id: rid,
          layout_id: layout,
          row_number: row,
          row_label:
            row === 1 ? "Window side" : row === 2 ? "Main floor" : "Back room",
        });
        for (let col = 1; col <= 4; col++)
          await insert(c, "dining_tables", {
            store_id: st,
            table_id: uid(),
            row_id: rid,
            table_number: "T" + ((row - 1) * 4 + col),
            row_position: col,
            seat_count: [2, 4, 4, 6][col - 1],
            is_window: row === 1,
            order_qr_enabled: false,
          });
      }
      await insert(c, "store_policy_versions", {
        store_id: st,
        policy_id: policy,
        source_template_id: template,
        version_number: 1,
        join_radius_metres: 300,
        arrival_radius_metres: 50,
        call_grace_seconds: 300,
        max_party_size: 8,
        created_at: new Date(),
      });
      for (const kind of ["tablet", "kiosk", "printer", "call_bell"])
        await insert(c, "store_devices", {
          store_id: st,
          device_id: kind === "tablet" ? tablet : uid(),
          device_kind: kind,
          device_label:
            kind === "tablet" ? "Main store tablet" : kind.replace("_", " "),
          registered_at: new Date(),
        });
      await insert(c, "store_pin_verifiers", {
        store_id: st,
        pin_verifier: await hashPassword("246810"),
        rotated_at: new Date(),
      });
      await insert(c, "store_join_qr_versions", {
        store_id: st,
        qr_id: uid(),
        created_at: new Date(),
      });
      await insert(c, "operating_sessions", {
        store_id: st,
        session_id: uid(),
        business_date: new Date().toLocaleDateString("en-CA", {
          timeZone: "Asia/Seoul",
        }),
        layout_id: layout,
        policy_id: policy,
        owner_device_id: tablet,
        authority_epoch: 1,
        next_queue_sequence: 1,
        next_ticket_number: 1,
        last_event_sequence: 0,
        state_version: 0,
        opened_at: new Date(),
      });
      for (let weekday = 0; weekday < 7; weekday++)
        await insert(c, "store_opening_periods", {
          store_id: st,
          period_id: uid(),
          weekday,
          opens_minute: 660,
          closes_minute: 1320,
        });
    }
    return { created: true };
  });
}
if (process.argv[1]?.endsWith("/seed.ts")) {
  try {
    console.log(await seed());
    console.log(
      "Demo stores ready. Read SEED_EMAIL/SEED_PASSWORD from private .env. Initial demo tablet PIN: 246810.",
    );
  } finally {
    await pool.end();
  }
}
