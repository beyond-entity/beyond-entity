import React, { useEffect, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useNavigate,
  useParams,
} from "react-router-dom";
import QRCode from "qrcode";
import { api, put, auth, location, ApiError } from "./api";
import {
  cached,
  saveTabletSnapshot,
  journalOfflineAction,
  syncJournal,
  pending,
  fits,
} from "./offline";
import "@fontsource/archivo/400.css";
import "@fontsource/archivo/600.css";
import "@fontsource/archivo/800.css";
import "./style.css";
type Field = {
  name: string;
  label: string;
  type?: string;
  value?: any;
  options?: any[];
  required?: boolean;
};
const title = (s: string) =>
  s.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
function useWork() {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const work = async (fn: () => Promise<any>) => {
    setBusy(true);
    setError("");
    try {
      return await fn();
    } catch (e: any) {
      setError(e.message || "Unable to complete this action");
      return null;
    } finally {
      setBusy(false);
    }
  };
  return { error, setError, busy, work };
}
function Notice({ children }: { children: any }) {
  return children ? (
    <div role="alert" className="notice">
      {children}
    </div>
  ) : null;
}
function Brand() {
  return (
    <Link className="brand" to="/">
      Table<span>Q</span>
      <i>●</i>
    </Link>
  );
}
function Shell({
  children,
  section = "Head office",
  store,
  actions,
}: {
  children: any;
  section?: string;
  store?: string;
  actions?: any;
}) {
  return (
    <>
      <header className="top">
        <Brand />
        <div className="top-label">
          {section}
          <b>{store || "Restaurant waitlist platform"}</b>
        </div>
        <div className="top-actions">
          {actions}
          <Link to="/hq">Head office ↗</Link>
        </div>
      </header>
      {children}
      <footer>
        TABLEQ <span>ONE QUEUE. A BETTER WAIT.</span>
        <Link to="/stores">Customer view ↗</Link>
      </footer>
    </>
  );
}
function Mobile({
  children,
  back = "/stores",
}: {
  children: any;
  back?: string;
}) {
  return (
    <div className="mobile">
      <header>
        <Brand />
        <Link to={back}>← Back</Link>
      </header>
      {children}
      <footer>YOUR TABLE IS WORTH THE WAIT.</footer>
    </div>
  );
}
function Section({
  label,
  title: heading,
  children,
  aside,
}: {
  label?: string;
  title: string;
  children?: any;
  aside?: any;
}) {
  return (
    <div className="section-head">
      <div>
        <div className="eyebrow">{label}</div>
        <h1>{heading}</h1>
        {children}
      </div>
      {aside}
    </div>
  );
}
function FieldForm({
  fields,
  onSubmit,
  button = "Save",
  busy = false,
}: {
  fields: Field[];
  onSubmit: (b: any) => Promise<any>;
  button?: string;
  busy?: boolean;
}) {
  return (
    <form
      className="fields"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const data = new FormData(form);
        const b: any = {};
        for (const f of fields)
          b[f.name] =
            f.type === "checkbox"
              ? data.get(f.name) === "on"
              : f.type === "number"
                ? Number(data.get(f.name))
                : data.get(f.name);
        await onSubmit(b);
      }}
    >
      {fields.map((f) => (
        <label key={f.name}>
          {f.type === "checkbox" ? (
            <>
              <input name={f.name} type="checkbox" defaultChecked={f.value} />
              {f.label}
            </>
          ) : (
            <>
              <span>{f.label}</span>
              {f.options ? (
                <select name={f.name} defaultValue={f.value} required>
                  {f.options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  name={f.name}
                  type={f.type || "text"}
                  defaultValue={f.value}
                  required={f.required !== false}
                  step={f.type === "number" ? "any" : undefined}
                />
              )}
            </>
          )}
        </label>
      ))}
      <button disabled={busy}>{busy ? "Saving…" : button}</button>
    </form>
  );
}
function Stats({ items }: { items: [string, any][] }) {
  return (
    <div className="stats">
      {items.map(([label, value]) => (
        <div key={label}>
          <span className="eyebrow">{label}</span>
          <strong>{value ?? "—"}</strong>
        </div>
      ))}
    </div>
  );
}
function Party({
  value,
  setValue,
}: {
  value: number;
  setValue: (n: number) => void;
}) {
  return (
    <div className="party" aria-label="Party size">
      {Array.from({ length: 8 }, (_, i) => (
        <button
          type="button"
          className={value === i + 1 ? "selected" : "secondary"}
          key={i}
          onClick={() => setValue(i + 1)}
        >
          {i + 1}
        </button>
      ))}
    </div>
  );
}
function Home() {
  return (
    <Shell section="Welcome">
      <main className="landing">
        <div className="eyebrow">A LITTLE LESS WAITING</div>
        <h1>
          Good food.
          <br />
          Better waiting.
        </h1>
        <p>
          One queue, from your first hello
          <br />
          to your seat at the table.
        </p>
        <div className="actions">
          <Link className="button" to="/stores">
            Find a restaurant ↗
          </Link>
          <Link className="button secondary" to="/w">
            I have a watch code
          </Link>
        </div>
        <div className="landing-rule">
          <span>01 / CUSTOMER</span>
          <Link to="/hq">Store & head office access →</Link>
        </div>
      </main>
    </Shell>
  );
}
function Login() {
  const { error, busy, work } = useWork(),
    navigate = useNavigate();
  return (
    <Shell section="Sign in">
      <main className="login-layout">
        <div>
          <div className="eyebrow">TABLEQ FOR RESTAURANTS</div>
          <h1>
            Every store.
            <br />
            One clear view.
          </h1>
          <p>
            Keep the queue moving, from the first
            <br />
            check-in to the last table cleared.
          </p>
        </div>
        <div className="panel">
          <h2>Welcome back.</h2>
          <p className="muted">
            Sign in to your head-office or manager account.
          </p>
          <Notice>{error}</Notice>
          <FieldForm
            busy={busy}
            button="Sign in →"
            fields={[
              { name: "email", label: "Email", type: "email" },
              { name: "password", label: "Password", type: "password" },
            ]}
            onSubmit={(b) =>
              work(async () => {
                await api("/api/auth/operator-sessions", b);
                navigate("/hq");
              })
            }
          />
        </div>
      </main>
    </Shell>
  );
}
function QR({ value }: { value: string }) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    void QRCode.toDataURL(value, {
      width: 320,
      margin: 2,
      errorCorrectionLevel: "M",
    }).then(setSrc);
  }, [value]);
  return src ? (
    <img className="qr" src={src} alt={"QR code for " + value} />
  ) : null;
}
function HeadOffice() {
  const [data, setData] = useState<any>(),
    [overview, setOverview] = useState<any[]>([]),
    [tab, setTab] = useState("Stores"),
    [result, setResult] = useState<any>(null);
  const { error, busy, work } = useWork(),
    nav = useNavigate();
  const refresh = async () => {
    try {
      const d = await api("/api/admin/bootstrap");
      setData(d);
      setOverview(await api("/api/admin/stores/overview"));
    } catch (e: any) {
      if (e.status === 401) nav("/login");
      else throw e;
    }
  };
  useEffect(() => {
    void work(refresh);
    const t = setInterval(() => void refresh().catch(() => {}), 10000);
    return () => clearInterval(t);
  }, []);
  if (!data)
    return (
      <Shell>
        <main>
          <Notice>{error}</Notice>
          <p>Loading your restaurants…</p>
        </main>
      </Shell>
    );
  const stores = data.stores;
  return (
    <Shell
      actions={
        <button
          className="text-button"
          onClick={() =>
            work(async () => {
              await api("/api/auth/operator-session/logout", {});
              nav("/login");
            })
          }
        >
          Sign out
        </button>
      }
    >
      <main>
        <Section
          label={data.account.display_name}
          title="The bigger picture."
          aside={<span className="pill">● Live overview</span>}
        >
          <p className="muted">Every store, every queue — at a glance.</p>
        </Section>
        <nav className="tabs">
          {["Stores", "QR codes", "Accounts & partners", "Policies"].map(
            (x) => (
              <button
                className={tab === x ? "active" : ""}
                key={x}
                onClick={() => {
                  setTab(x);
                  setResult(null);
                }}
              >
                {x}
              </button>
            ),
          )}
        </nav>
        <Notice>{error}</Notice>
        {tab === "Stores" && (
          <>
            <Stats
              items={[
                ["Restaurants", stores.length],
                [
                  "Groups waiting",
                  overview.reduce((n, s) => n + Number(s.waiting_count), 0),
                ],
                [
                  "Stores open",
                  stores.filter((s: any) => s.store_status === "open").length,
                ],
              ]}
            />
            <div className="panel table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Store</th>
                    <th>Status</th>
                    <th>Waiting</th>
                    <th>Store tablet</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {stores.map((s: any) => {
                    const o = overview.find((o) => o.store_id === s.store_id);
                    return (
                      <tr key={s.store_id}>
                        <td>
                          <b>{s.store_name}</b>
                          <small>
                            {s.store_code} · {s.address}
                          </small>
                        </td>
                        <td>
                          <span className="pill">{title(s.store_status)}</span>
                        </td>
                        <td className="number">{o?.waiting_count || 0}</td>
                        <td>
                          {o?.owner_last_seen_at &&
                          Date.now() -
                            new Date(o.owner_last_seen_at).getTime() <
                            30000
                            ? "● Online"
                            : "○ No recent heartbeat"}
                        </td>
                        <td>
                          <Link to={"/settings/" + s.store_id}>Manage →</Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <details className="panel">
              <summary>Register a restaurant</summary>
              <FieldForm
                busy={busy}
                fields={[
                  { name: "store_code", label: "Store code" },
                  { name: "store_name", label: "Restaurant name" },
                  { name: "address", label: "Street address" },
                  {
                    name: "time_zone",
                    label: "Time zone",
                    value: "Asia/Seoul",
                  },
                  {
                    name: "latitude",
                    label: "Latitude",
                    type: "number",
                    value: 37.4979,
                  },
                  {
                    name: "longitude",
                    label: "Longitude",
                    type: "number",
                    value: 127.0276,
                  },
                  {
                    name: "contact_phone",
                    label: "Business phone",
                    required: false,
                  },
                  {
                    name: "contact_email",
                    label: "Business email",
                    type: "email",
                    required: false,
                  },
                ]}
                onSubmit={(b) =>
                  work(async () => {
                    await put("/api/admin/stores/" + crypto.randomUUID(), b);
                    await refresh();
                  })
                }
              />
            </details>
          </>
        )}
        {tab === "QR codes" && (
          <div className="qr-grid">
            {stores.map((s: any) => (
              <div className="panel poster" key={s.store_id}>
                <Brand />
                <h2>
                  Scan to join
                  <br />
                  the queue.
                </h2>
                <p>
                  We'll keep your place.
                  <br />
                  You enjoy the neighbourhood.
                </p>
                {s.qr && (
                  <>
                    <QR value={window.location.origin + "/q/" + s.qr.qr_id} />
                    <small>
                      {s.store_name} · {s.store_code}
                    </small>
                  </>
                )}
                <div className="actions no-print">
                  <button className="secondary" onClick={() => window.print()}>
                    Print poster
                  </button>
                  <button
                    onClick={() =>
                      work(async () => {
                        await put(
                          `/api/admin/stores/${s.store_id}/join-qr/${crypto.randomUUID()}`,
                          {},
                        );
                        await refresh();
                      })
                    }
                  >
                    Regenerate
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        {tab === "Accounts & partners" && (
          <div className="columns">
            <div className="panel">
              <h2>Store manager</h2>
              <FieldForm
                busy={busy}
                button="Create manager"
                fields={[
                  {
                    name: "store_id",
                    label: "Store",
                    options: stores.map((s: any) => ({
                      value: s.store_id,
                      label: s.store_name,
                    })),
                  },
                  { name: "email", label: "Email", type: "email" },
                  { name: "display_name", label: "Full name" },
                  {
                    name: "initial_password",
                    label: "Initial password (12+ characters)",
                    type: "password",
                  },
                ]}
                onSubmit={(b) =>
                  work(async () =>
                    setResult(
                      await put(
                        "/api/admin/accounts/" + crypto.randomUUID(),
                        b,
                      ),
                    ),
                  )
                }
              />
              <h3>Disable manager</h3>
              <FieldForm
                fields={[{ name: "account_id", label: "Manager account ID" }]}
                button="Disable account"
                onSubmit={(b) =>
                  work(async () =>
                    setResult(
                      await api(
                        `/api/admin/accounts/${b.account_id}/disable`,
                        {},
                      ),
                    ),
                  )
                }
              />
            </div>
            <div className="panel">
              <h2>Partner read access</h2>
              <p>Provides store status and aggregate waiting counts only.</p>
              <FieldForm
                button="Issue credential"
                fields={[{ name: "partner_name", label: "Partner name" }]}
                onSubmit={(b) =>
                  work(async () =>
                    setResult(
                      await put(
                        "/api/admin/partners/" +
                          crypto.randomUUID() +
                          "/credential",
                        b,
                      ),
                    ),
                  )
                }
              />
              {result && (
                <div className="secret">
                  <b>Save this result securely</b>
                  <pre>{JSON.stringify(result, null, 2)}</pre>
                  <button className="secondary" onClick={() => setResult(null)}>
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
        {tab === "Policies" && (
          <div className="columns">
            <div className="panel">
              <h2>Shared policy templates</h2>
              {data.templates.map((p: any) => (
                <div className="rule-row" key={p.template_id}>
                  <b>Version {p.version_number}</b>
                  <span>
                    Join {p.join_radius_metres}m · Arrival{" "}
                    {p.arrival_radius_metres}m · Grace {p.call_grace_seconds}s
                  </span>
                </div>
              ))}
            </div>
            <div className="panel">
              <h2>Publish a template</h2>
              <FieldForm
                fields={[
                  {
                    name: "version_number",
                    label: "Version",
                    type: "number",
                    value:
                      Math.max(
                        0,
                        ...data.templates.map((p: any) => p.version_number),
                      ) + 1,
                  },
                  {
                    name: "join_radius_metres",
                    label: "Join radius (m)",
                    type: "number",
                    value: 300,
                  },
                  {
                    name: "arrival_radius_metres",
                    label: "Arrival radius (m)",
                    type: "number",
                    value: 50,
                  },
                  {
                    name: "call_grace_seconds",
                    label: "Call grace (seconds)",
                    type: "number",
                    value: 300,
                  },
                  {
                    name: "allow_join_override",
                    label: "Allow store join-radius override",
                    type: "checkbox",
                    value: true,
                  },
                  {
                    name: "allow_arrival_override",
                    label: "Allow store arrival-radius override",
                    type: "checkbox",
                    value: true,
                  },
                  {
                    name: "allow_grace_override",
                    label: "Allow store grace override",
                    type: "checkbox",
                  },
                ]}
                onSubmit={(b) =>
                  work(async () => {
                    await put(
                      "/api/admin/policy-templates/" + crypto.randomUUID(),
                      b,
                    );
                    await refresh();
                  })
                }
              />
            </div>
          </div>
        )}
      </main>
    </Shell>
  );
}
function Settings() {
  const { store: storeId } = useParams(),
    [data, setData] = useState<any>(),
    [config, setConfig] = useState<any>(),
    [health, setHealth] = useState<any[]>([]),
    [tab, setTab] = useState("Overview"),
    [sim, setSim] = useState<any>(),
    [metrics, setMetrics] = useState<any>(),
    [layout, setLayout] = useState("");
  const { work, error, busy } = useWork(),
    nav = useNavigate();
  const refresh = async () => {
    const d = await api("/api/admin/bootstrap");
    setData(d);
    const s = d.stores.find((s: any) => s.store_id === storeId);
    if (!s) throw new Error("Store not accessible");
    setConfig(await api(`/api/admin/stores/${storeId}/configuration`));
    setHealth(await api(`/api/store/${storeId}/device-health`));
    if (!layout) setLayout(s.layouts.at(-1)?.layout_id || "");
  };
  useEffect(() => {
    void work(refresh);
  }, [storeId]);
  const s = data?.stores.find((s: any) => s.store_id === storeId);
  if (!s || !config)
    return (
      <Shell>
        <main>
          <Notice>{error}</Notice>Loading store…{" "}
          <Link to="/login">Sign in</Link>
        </main>
      </Shell>
    );
  const enroll = async (kind: string) => {
    const d = s.devices.find((d: any) => d.device_kind === kind);
    if (!d) throw new Error("Register this device first");
    const result = await api(
      `/api/admin/stores/${storeId}/devices/${d.device_id}/credential`,
      {},
    );
    sessionStorage.setItem(
      "tableq-device",
      JSON.stringify({
        token: result.device_token,
        device_id: d.device_id,
        store_id: storeId,
        kind,
      }),
    );
    nav("/" + (kind === "tablet" ? "tablet" : "kiosk") + "/" + storeId);
  };
  const save = async (fn: () => Promise<any>) =>
    work(async () => {
      await fn();
      await refresh();
    });
  return (
    <Shell section="Store settings" store={s.store_name}>
      <main>
        <Section
          label={s.store_code + " / " + s.address}
          title={s.store_name}
          aside={
            <div className="actions">
              <button onClick={() => work(() => enroll("tablet"))}>
                Open store tablet ↗
              </button>
              <button
                className="secondary"
                onClick={() => work(() => enroll("kiosk"))}
              >
                Open kiosk ↗
              </button>
            </div>
          }
        />
        <nav className="tabs">
          {["Overview", "Layout", "Policies & hours", "Devices", "Figures"].map(
            (t) => (
              <button
                className={tab === t ? "active" : ""}
                key={t}
                onClick={() => {
                  setTab(t);
                  if (t === "Devices")
                    void work(async () =>
                      setSim(await api("/api/simulator/" + storeId)),
                    );
                }}
              >
                {t}
              </button>
            ),
          )}
        </nav>
        <Notice>{error}</Notice>
        {tab === "Overview" && (
          <div className="columns">
            <div className="panel">
              <h2>Operating session</h2>
              <p>
                {s.session
                  ? "Session open · " + s.session.business_date
                  : "No open session"}
              </p>
              <FieldForm
                fields={[
                  {
                    name: "waitlist_state",
                    label: "Store status",
                    value: s.store_status,
                    options: ["open", "waitlist_closed", "closed"].map((x) => ({
                      value: x,
                      label: title(x),
                    })),
                  },
                ]}
                onSubmit={(b) =>
                  save(() =>
                    put(`/api/admin/stores/${storeId}/waitlist-state`, b),
                  )
                }
              />
              {s.session ? (
                <button
                  className="secondary"
                  onClick={() =>
                    save(() =>
                      api(
                        `/api/admin/stores/${storeId}/sessions/${s.session.session_id}/close`,
                        {},
                      ),
                    )
                  }
                >
                  Close drained session
                </button>
              ) : (
                <FieldForm
                  button="Open session"
                  fields={[
                    {
                      name: "owner_device_id",
                      label: "Owner tablet",
                      options: s.devices
                        .filter((d: any) => d.device_kind === "tablet")
                        .map((d: any) => ({
                          value: d.device_id,
                          label: d.device_label,
                        })),
                    },
                    {
                      name: "layout_id",
                      label: "Published layout",
                      options: s.layouts
                        .filter((l: any) => l.layout_status === "published")
                        .map((l: any) => ({
                          value: l.layout_id,
                          label: "Version " + l.version_number,
                        })),
                    },
                    {
                      name: "policy_id",
                      label: "Policy",
                      options: s.policies.map((p: any) => ({
                        value: p.policy_id,
                        label: "Version " + p.version_number,
                      })),
                    },
                    {
                      name: "business_date",
                      label: "Business date",
                      type: "date",
                      value: new Date().toLocaleDateString("en-CA"),
                    },
                  ]}
                  onSubmit={(b) =>
                    save(() =>
                      put(
                        `/api/admin/stores/${storeId}/sessions/${crypto.randomUUID()}`,
                        b,
                      ),
                    )
                  }
                />
              )}
            </div>
            <div className="panel">
              <h2>Offline review</h2>
              <p>Review physical table state before resolving a discrepancy.</p>
              {!config.conflicts.length ? (
                <p className="empty">No open synchronization conflicts.</p>
              ) : (
                config.conflicts.map((c: any) => (
                  <div className="rule-row" key={c.conflict_id}>
                    <span>{c.reason_code}</span>
                    <button
                      className="secondary"
                      onClick={() =>
                        save(() =>
                          api(
                            `/api/admin/stores/${storeId}/sync-conflicts/${c.conflict_id}/resolve`,
                            { resolution_code: "physical_verified" },
                          ),
                        )
                      }
                    >
                      Confirm reviewed
                    </button>
                  </div>
                ))
              )}
              <h3>Tablet PIN</h3>
              <FieldForm
                button="Rotate PIN"
                fields={[
                  {
                    name: "new_pin",
                    label: "New PIN (6–12 digits)",
                    type: "password",
                  },
                ]}
                onSubmit={(b) =>
                  save(() => put(`/api/admin/stores/${storeId}/tablet-pin`, b))
                }
              />
            </div>
          </div>
        )}
        {tab === "Layout" && (
          <>
            <div className="toolbar">
              <select
                aria-label="Layout version"
                value={layout}
                onChange={(e) => setLayout(e.target.value)}
              >
                {s.layouts.map((l: any) => (
                  <option key={l.layout_id} value={l.layout_id}>
                    Version {l.version_number} · {l.layout_status}
                  </option>
                ))}
              </select>
              <button
                className="secondary"
                onClick={() =>
                  save(async () => {
                    const id = crypto.randomUUID();
                    await put(`/api/admin/stores/${storeId}/layouts/${id}`, {
                      version_number:
                        Math.max(
                          0,
                          ...s.layouts.map((l: any) => l.version_number),
                        ) + 1,
                    });
                    setLayout(id);
                  })
                }
              >
                New draft
              </button>
              <button
                onClick={() =>
                  save(() =>
                    api(
                      `/api/admin/stores/${storeId}/layouts/${layout}/publish`,
                      {},
                    ),
                  )
                }
              >
                Publish layout
              </button>
            </div>
            <div className="floor panel">
              {config.rows
                .filter((r: any) => r.layout_id === layout)
                .map((r: any) => (
                  <div key={r.row_id}>
                    <div className="eyebrow">
                      Row {r.row_number} · {r.row_label}
                    </div>
                    <div className="table-grid">
                      {config.tables
                        .filter((t: any) => t.row_id === r.row_id)
                        .map((t: any) => (
                          <div className="dining free" key={t.table_id}>
                            <b>{t.table_number}</b>
                            <span>
                              {t.seat_count} seats{" "}
                              {t.is_window ? "· Window" : ""}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                ))}
            </div>
            <div className="columns">
              <div className="panel">
                <h3>Add row to draft</h3>
                <FieldForm
                  fields={[
                    {
                      name: "row_number",
                      label: "Row number",
                      type: "number",
                      value: 1,
                    },
                    { name: "row_label", label: "Row label" },
                  ]}
                  onSubmit={(b) =>
                    save(() =>
                      put(
                        `/api/admin/stores/${storeId}/layouts/${layout}/rows/${crypto.randomUUID()}`,
                        b,
                      ),
                    )
                  }
                />
              </div>
              <div className="panel">
                <h3>Add table</h3>
                <FieldForm
                  fields={[
                    {
                      name: "row_id",
                      label: "Row",
                      options: config.rows
                        .filter((r: any) => r.layout_id === layout)
                        .map((r: any) => ({
                          value: r.row_id,
                          label: r.row_label,
                        })),
                    },
                    {
                      name: "table_number",
                      label: "Table number",
                      value: "T1",
                    },
                    {
                      name: "row_position",
                      label: "Position in row",
                      type: "number",
                      value: 1,
                    },
                    {
                      name: "seat_count",
                      label: "Seats",
                      type: "number",
                      value: 4,
                    },
                    {
                      name: "is_window",
                      label: "Window seat",
                      type: "checkbox",
                    },
                  ]}
                  onSubmit={(b) =>
                    save(() =>
                      put(
                        `/api/admin/stores/${storeId}/tables/${crypto.randomUUID()}`,
                        b,
                      ),
                    )
                  }
                />
              </div>
            </div>
          </>
        )}
        {tab === "Policies & hours" && (
          <div className="columns">
            <div className="panel">
              <h2>Effective policy</h2>
              <FieldForm
                fields={[
                  {
                    name: "template_id",
                    label: "Head-office template",
                    options: data.templates.map((p: any) => ({
                      value: p.template_id,
                      label: "Version " + p.version_number,
                    })),
                  },
                  {
                    name: "version_number",
                    label: "New policy version",
                    type: "number",
                    value:
                      Math.max(
                        0,
                        ...s.policies.map((p: any) => p.version_number),
                      ) + 1,
                  },
                  {
                    name: "join_radius_metres",
                    label: "Join radius (m)",
                    type: "number",
                    value: 300,
                  },
                  {
                    name: "arrival_radius_metres",
                    label: "Arrival radius (m)",
                    type: "number",
                    value: 50,
                  },
                  {
                    name: "call_grace_seconds",
                    label: "Call grace (seconds)",
                    type: "number",
                    value: 300,
                  },
                ]}
                button="Publish policy"
                onSubmit={(b) =>
                  save(() =>
                    put(
                      `/api/admin/stores/${storeId}/policies/${crypto.randomUUID()}`,
                      b,
                    ),
                  )
                }
              />
              <p className="muted">
                New versions apply when a new operating session opens.
              </p>
            </div>
            <div className="panel">
              <h2>Opening hours</h2>
              {config.periods.map((p: any) => (
                <p key={p.period_id}>
                  {
                    [
                      "Sunday",
                      "Monday",
                      "Tuesday",
                      "Wednesday",
                      "Thursday",
                      "Friday",
                      "Saturday",
                    ][p.weekday]
                  }{" "}
                  · {Math.floor(p.opens_minute / 60)}:
                  {String(p.opens_minute % 60).padStart(2, "0")}–
                  {Math.floor(p.closes_minute / 60)}:
                  {String(p.closes_minute % 60).padStart(2, "0")}
                </p>
              ))}
              <FieldForm
                fields={[
                  {
                    name: "weekday",
                    label: "Day (Sunday 0 – Saturday 6)",
                    type: "number",
                    value: 1,
                  },
                  {
                    name: "opens_minute",
                    label: "Opening minute after midnight",
                    type: "number",
                    value: 660,
                  },
                  {
                    name: "closes_minute",
                    label: "Closing minute after midnight",
                    type: "number",
                    value: 1320,
                  },
                ]}
                button="Add opening period"
                onSubmit={(b) =>
                  save(() =>
                    put(
                      `/api/admin/stores/${storeId}/opening-periods/${crypto.randomUUID()}`,
                      b,
                    ),
                  )
                }
              />
            </div>
          </div>
        )}
        {tab === "Devices" && (
          <>
            <div className="columns">
              <div className="panel">
                <h2>Device health</h2>
                {health.map((d) => (
                  <div className="device-row" key={d.device_id}>
                    <div>
                      <b>{d.device_label}</b>
                      <small>
                        {title(d.device_kind)} · {d.connectivity_status} ·{" "}
                        {d.fault_code || "No report"}
                      </small>
                    </div>
                    {d.device_kind === "tablet" ? (
                      <small>Use the tablet connection switch</small>
                    ) : (
                    <select
                      aria-label={"Simulate fault for " + d.device_label}
                      value={
                        sim?.controls?.[d.device_id]?.offline
                          ? "offline"
                          : sim?.controls?.[d.device_id]?.fault_code || "none"
                      }
                      onChange={(e) =>
                        work(async () => {
                          await put(
                            `/api/simulator/${storeId}/${d.device_id}`,
                            {
                              offline: e.target.value === "offline",
                              fault_code:
                                e.target.value === "offline"
                                  ? "none"
                                  : e.target.value,
                            },
                          );
                          setSim(await api("/api/simulator/" + storeId));
                        })
                      }
                    >
                      {[
                        "none",
                        "offline",
                        "paper_out",
                        "jam",
                        "adapter_error",
                      ].map((x) => (
                        <option key={x} value={x}>
                          {title(x)}
                        </option>
                      ))}
                    </select>
                    )}
                  </div>
                ))}
                <FieldForm
                  button="Register device"
                  fields={[
                    {
                      name: "device_kind",
                      label: "Kind",
                      options: ["tablet", "kiosk", "printer", "call_bell"].map(
                        (x) => ({ value: x, label: title(x) }),
                      ),
                    },
                    { name: "device_label", label: "Label" },
                  ]}
                  onSubmit={(b) =>
                    save(() =>
                      put(
                        `/api/admin/stores/${storeId}/devices/${crypto.randomUUID()}`,
                        b,
                      ),
                    )
                  }
                />
              </div>
              <div className="panel">
                <h2>Delivery & simulator log</h2>
                <button
                  className="secondary"
                  onClick={() =>
                    work(async () => {
                      setSim(await api("/api/simulator/" + storeId));
                      await refresh();
                    })
                  }
                >
                  Refresh records
                </button>
                {sim?.jobs.map((j: any) => (
                  <div className="rule-row" key={j.job_id}>
                    <span>
                      {title(j.channel)}
                      <small>
                        {new Date(j.created_at).toLocaleTimeString()} ·{" "}
                        {j.attempt_count} attempts
                      </small>
                    </span>
                    <b>{j.job_status}</b>
                  </div>
                ))}
                {!sim?.jobs.length && (
                  <p className="empty">
                    Delivery records appear when a group is called.
                  </p>
                )}
              </div>
            </div>
          </>
        )}
        {tab === "Figures" && (
          <>
            <div className="panel">
              <FieldForm
                button="Show figures"
                fields={[
                  {
                    name: "from_time",
                    label: "From",
                    type: "datetime-local",
                    value: new Date(Date.now() - 86400000)
                      .toISOString()
                      .slice(0, 16),
                  },
                  {
                    name: "to_time",
                    label: "To",
                    type: "datetime-local",
                    value: new Date().toISOString().slice(0, 16),
                  },
                ]}
                onSubmit={(b) =>
                  work(async () => {
                    const query = new URLSearchParams({
                      from_time: new Date(b.from_time).toISOString(),
                      to_time: new Date(b.to_time).toISOString(),
                    });
                    const [basic, seating, hourly, faults] = await Promise.all(
                      ["", "/seating", "/hourly", "/device-faults"].map((p) =>
                        api(
                          `/api/admin/stores/${storeId}/metrics${p}?${query}`,
                        ),
                      ),
                    );
                    const start =
                        Math.floor(new Date(b.from_time).getTime() / 3600000) *
                        3600000,
                      end = new Date(b.to_time).getTime();
                    const filled: any[] = [];
                    for (let at = start; at < end; at += 3600000) {
                      const key = new Date(at).toISOString();
                      filled.push(
                        hourly.find(
                          (h: any) =>
                            new Date(h.hour_start_utc).getTime() === at,
                        ) || {
                          hour_start_utc: key,
                          joined_groups: 0,
                          seated_groups: 0,
                        },
                      );
                    }
                    setMetrics({
                      basic: basic[0],
                      seating: seating[0],
                      hourly: filled,
                      faults,
                    });
                  })
                }
              />
            </div>
            {metrics && (
              <>
                <Stats
                  items={[
                    ["Joined", metrics.basic.joined_count],
                    ["No-shows", metrics.basic.no_show_count],
                    ["Deferrals", metrics.basic.deferral_count],
                    [
                      "Mean wait (min)",
                      metrics.seating.mean_wait_seconds
                        ? Math.round(metrics.seating.mean_wait_seconds / 60)
                        : "—",
                    ],
                  ]}
                />
                <div className="panel">
                  <h2>
                    Hourly activity <small>UTC · recorded events</small>
                  </h2>
                  {metrics.hourly.map((h: any) => (
                    <div className="bar-row" key={h.hour_start_utc}>
                      <span>{h.hour_start_utc.slice(0, 16)}</span>
                      <div
                        style={{
                          width:
                            Math.max(4, Math.min(80, h.joined_groups * 5)) +
                            "%",
                        }}
                      />
                      <b>
                        {h.joined_groups} joined · {h.seated_groups} seated
                      </b>
                    </div>
                  ))}
                  {!metrics.hourly.length && <p>No activity in this period.</p>}
                  <h3>Device fault transitions</h3>
                  {metrics.faults.map((f: any, i: number) => (
                    <p key={i}>
                      {
                        s.devices.find((d: any) => d.device_id === f.device_id)
                          ?.device_label
                      }{" "}
                      · {f.fault_code} · {f.transition_count}
                    </p>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </Shell>
  );
}
function Tablet() {
  const { store } = useParams(),
    storeId = store!,
    [snapshot, setSnapshot] = useState<any>({ groups: [], tables: [] }),
    [offline, setOffline] = useState(
      !navigator.onLine || sessionStorage.getItem("tablet-offline") === "true",
    ),
    [unlocked, setUnlocked] = useState(!!auth()?.unlock),
    [party, setParty] = useState(2),
    [windowSeat, setWindowSeat] = useState(false),
    [arrived, setArrived] = useState(true),
    [issued, setIssued] = useState<any>(),
    [tab, setTab] = useState("Queue"),
    [count, setCount] = useState(0),
    [arrival, setArrival] = useState<any>(),
    [health, setHealth] = useState<any[]>([]);
  const { work, error, setError, busy } = useWork();
  useEffect(() => {
    const lost = () => {
      setOffline(true);
      sessionStorage.setItem("tablet-offline", "true");
      sessionStorage.setItem("tablet-offline-kind", "network");
    };
    const restored = async () => {
      try {
        await api("/api/health");
        setOffline(false);
        sessionStorage.setItem("tablet-offline", "false");
      } catch {
        lost();
      }
    };
    window.addEventListener("offline", lost);
    window.addEventListener("online", restored);
    return () => {
      window.removeEventListener("offline", lost);
      window.removeEventListener("online", restored);
    };
  }, []);
  const refresh = async () => {
    let data;
    try {
      data = offline ? await cached(storeId) : await syncJournal(storeId);
    } catch (e: any) {
      if (
        e instanceof TypeError ||
        e.name === "TimeoutError" ||
        e.status >= 500
      ) {
        setOffline(true);
        sessionStorage.setItem("tablet-offline", "true");
        sessionStorage.setItem("tablet-offline-kind", "network");
        data = await cached(storeId);
      } else throw e;
    }
    setSnapshot(data);
    setCount((await pending(storeId)).length);
  };
  useEffect(() => {
    if (!offline) return;
    const timer = setInterval(async () => {
      if (sessionStorage.getItem("tablet-offline-kind") !== "network") return;
      try {
        await api("/api/health");
        setOffline(false);
        sessionStorage.setItem("tablet-offline", "false");
        setError("");
      } catch {}
    }, 5000);
    return () => clearInterval(timer);
  }, [offline]);
  useEffect(() => {
    void work(refresh);
    const tick = setInterval(() => {
      if (!offline && unlocked)
        void refresh().catch((e) => setError(e.message));
    }, 5000);
    return () => clearInterval(tick);
  }, [store, offline, unlocked]);
  useEffect(() => {
    if (offline || !unlocked) return;
    const tick = async () => {
      try {
        const d = auth();
        await api(`/api/devices/${d.device_id}/heartbeat`, {
          store_id: storeId,
          heartbeat_sequence: Date.now(),
          device_time: new Date().toISOString(),
          fault_code: "none",
        });
        setHealth(await api(`/api/store/${storeId}/device-health`));
      } catch (e: any) {
        setError(e.message);
      }
    };
    void tick();
    const t = setInterval(tick, 10000);
    return () => clearInterval(t);
  }, [store, offline, unlocked]);
  const change = async (action: string, g?: any) =>
    work(async () => {
      if (offline) {
        if (!["call", "seat", "clear"].includes(action))
          throw new Error("Only call, seat and clear are available offline");
        await journalOfflineAction(storeId, action as any, g);
      } else {
        if (count)
          throw new Error("Wait for pending offline actions to reconcile");
        if (action === "call")
          await api(`/api/store/${storeId}/calls/next`, {
            expected_state_version: snapshot.manifest.state_version,
          });
        else if (action === "clear")
          await api(`/api/store/${storeId}/tables/${g.table_id}/clear`, {
            expected_allocation_id: g.allocation_id,
          });
        else if (action === "watch") {
          setIssued({
            ...(await api(`/api/store/groups/${g.group_id}/watch-code`, {})),
            group_id: g.group_id,
            ticket_code: "A-" + String(g.ticket_number).padStart(3, "0"),
          });
        } else if (action === "arrival")
          await api(`/api/groups/${g.group_id}/arrival`, {
            arrival_code: "",
            latitude: 0,
            longitude: 0,
          });
        else {
          const prefix = ["cancel", "defer"].includes(action)
            ? "/api/groups"
            : "/api/store/groups";
          await api(
            `${prefix}/${g.group_id}/${action}`,
            action === "cancel"
              ? {}
              : action === "no-show"
                ? { expected_call_id: g.call_id, reason_code: "grace_elapsed" }
                : { expected_call_id: g.call_id },
          );
        }
      }
      await refresh();
    });
  if (auth()?.store_id !== storeId)
    return (
      <Shell section="Store tablet">
        <main>
          <h1>Enroll this tablet.</h1>
          <p>
            Open it from the store settings page with an authorized manager
            account.
          </p>
          <Link className="button" to={"/settings/" + storeId}>
            Go to store settings
          </Link>
        </main>
      </Shell>
    );
  if (!unlocked)
    return (
      <Shell section="Store tablet">
        <main className="narrow panel">
          <h1>Unlock the tablet.</h1>
          <p>The store stays signed in. Enter the store PIN to begin.</p>
          <Notice>{error}</Notice>
          <FieldForm
            fields={[{ name: "pin", label: "Store PIN", type: "password" }]}
            button="Unlock"
            busy={busy}
            onSubmit={(b) =>
              work(async () => {
                const result = await api("/api/auth/tablet-unlock", b);
                sessionStorage.setItem(
                  "tableq-device",
                  JSON.stringify({ ...auth(), unlock: result.unlock_token }),
                );
                setUnlocked(true);
              })
            }
          />
        </main>
      </Shell>
    );
  const groups = snapshot.groups.filter((g: any) =>
      ["waiting", "called"].includes(g.group_status),
    ),
    ts = snapshot.tables;
  const canCall = groups.some(
    (g: any) =>
      g.group_status === "waiting" &&
      g.arrival_confirmed &&
      ts.some((t: any) => t.table_status === "free" && fits(g, t)),
  );
  return (
    <Shell
      section="Store tablet"
      actions={
        <button
          className={offline ? "" : "secondary"}
          onClick={() => {
            const next = !offline;
            setOffline(next);
            sessionStorage.setItem("tablet-offline", String(next));
            sessionStorage.setItem(
              "tablet-offline-kind",
              next ? "manual" : "network",
            );
          }}
        >
          {offline ? "Reconnect store" : "Simulate connection loss"}
        </button>
      }
    >
      <main>
        <Section
          label="TODAY / LIVE SERVICE"
          title="Keep things moving."
          aside={
            <span className={"pill " + (offline ? "warning" : "")}>
              {offline ? "○ Offline · remote joins paused" : "● Connected"}{" "}
              {count ? `· ${count} actions pending` : ""}
            </span>
          }
        />
        <Notice>{error}</Notice>
        {offline && (
          <div className="notice">
            Working from the last saved snapshot. Call, seat and clear continue
            locally; new remote groups may be missing.
          </div>
        )}
        <Stats
          items={[
            [
              "Waiting",
              groups.filter((g: any) => g.group_status === "waiting").length,
            ],
            [
              "Called",
              groups.filter((g: any) => g.group_status === "called").length,
            ],
            [
              "Free tables",
              ts.filter((t: any) => t.table_status === "free").length,
            ],
            [
              "Occupied",
              ts.filter((t: any) => t.table_status === "occupied").length,
            ],
          ]}
        />
        <nav className="tabs">
          {["Queue", "Tables", "Add group"].map((x) => (
            <button
              className={tab === x ? "active" : ""}
              key={x}
              onClick={() => setTab(x)}
            >
              {x}
            </button>
          ))}
          <button
            onClick={() =>
              work(async () =>
                setArrival(
                  await api(`/api/store/${storeId}/arrival-challenge`, {}),
                ),
              )
            }
            disabled={offline}
          >
            Show arrival code
          </button>
        </nav>
        {arrival && (
          <div className="arrival-code">
            Arrival code <b>{arrival.arrival_code}</b>
            <span>
              Valid until {new Date(arrival.expires_at).toLocaleTimeString()}
            </span>
            <button className="text-button" onClick={() => setArrival(null)}>
              Close
            </button>
          </div>
        )}
        {tab === "Queue" && (
          <div className="tablet-grid">
            <div className="panel queue-panel">
              <div className="toolbar">
                <h2>
                  The queue <small>{groups.length} groups</small>
                </h2>
                <button
                  disabled={!canCall || busy}
                  onClick={() => change("call")}
                >
                  Call next eligible →
                </button>
              </div>
              {!groups.length && (
                <div className="empty">
                  <h2>A fresh start.</h2>
                  <p>Add a group or let customers check in.</p>
                  <button
                    className="secondary"
                    onClick={() => setTab("Add group")}
                  >
                    Add a group
                  </button>
                </div>
              )}
              {groups
                .sort((a: any, b: any) => a.queue_sequence - b.queue_sequence)
                .map((g: any) => (
                  <div
                    className={
                      "queue-row " +
                      (g.group_status === "called" ? "called" : "")
                    }
                    key={g.group_id}
                  >
                    <div className="ticket-number">
                      A-{String(g.ticket_number).padStart(3, "0")}
                      <small>
                        {g.party_size} people {g.wants_window ? "· Window" : ""}
                      </small>
                    </div>
                    <div>
                      <span className="pill">
                        {g.group_status === "called"
                          ? "Called"
                          : g.arrival_confirmed
                            ? "Arrived"
                            : "Awaiting arrival"}
                      </span>
                      <small>
                        {g.table_id
                          ? ts.find((t: any) => t.table_id === g.table_id)
                              ?.table_number
                          : ""}
                      </small>
                    </div>
                    <div className="actions compact">
                      {g.group_status === "called" ? (
                        <>
                          <button
                            disabled={busy}
                            onClick={() => change("seat", g)}
                          >
                            Seat
                          </button>
                          <button
                            disabled={offline || busy}
                            className="secondary"
                            onClick={() => change("recall", g)}
                          >
                            Recall
                          </button>
                          <button
                            disabled={offline || busy}
                            className="secondary"
                            onClick={() => change("defer", g)}
                          >
                            Defer
                          </button>
                          <button
                            disabled={offline || busy}
                            className="text-button"
                            onClick={() => change("no-show", g)}
                          >
                            No-show
                          </button>
                        </>
                      ) : (
                        <>
                          {!g.arrival_confirmed && (
                            <button
                              disabled={offline || busy}
                              className="secondary"
                              onClick={() => change("arrival", g)}
                            >
                              Confirm arrival
                            </button>
                          )}
                          <button
                            disabled={offline || busy}
                            className="secondary"
                            onClick={() => change("watch", g)}
                          >
                            Watch code
                          </button>
                        </>
                      )}
                      <button
                        disabled={offline || busy}
                        className="text-button"
                        onClick={() => change("cancel", g)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ))}
            </div>
            <div className="panel">
              <h3>At a glance</h3>
              <div className="mini-floor">
                {ts.map((t: any) => (
                  <button
                    className={"dining " + t.table_status}
                    key={t.table_id}
                    onClick={() => setTab("Tables")}
                  >
                    <b>{t.table_number}</b>
                    <span>{t.seat_count} seats</span>
                  </button>
                ))}
              </div>
              <h3>Devices</h3>
              {health.map((d) => (
                <p className="rule-row" key={d.device_id}>
                  <span>{d.device_label}</span>
                  <b>
                    {d.connectivity_status === "online" &&
                    d.fault_code === "none"
                      ? "● Ready"
                      : d.fault_code || d.connectivity_status}
                  </b>
                </p>
              ))}
            </div>
          </div>
        )}
        {tab === "Tables" && (
          <div className="floor panel">
            {[...new Set(ts.map((t: any) => t.row_number))]
              .sort()
              .map((row: any) => (
                <div key={row}>
                  <div className="eyebrow">Row {row}</div>
                  <div className="table-grid">
                    {ts
                      .filter((t: any) => t.row_number === row)
                      .map((t: any) => (
                        <div
                          className={"dining " + t.table_status}
                          key={t.table_id}
                        >
                          <b>{t.table_number}</b>
                          <span>
                            {t.seat_count} seats {t.is_window ? "· Window" : ""}
                          </span>
                          <strong>{title(t.table_status)}</strong>
                          {t.table_status === "occupied" && (
                            <button
                              disabled={busy}
                              onClick={() => change("clear", t)}
                            >
                              Clear table
                            </button>
                          )}
                          {t.table_status === "held" && (
                            <button
                              onClick={() => setTab("Queue")}
                              className="secondary"
                            >
                              Seat from queue
                            </button>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              ))}
          </div>
        )}
        {tab === "Add group" && (
          <div className="panel narrow">
            <div className="eyebrow">WALK-INS & PHONE BOOKINGS</div>
            <h2>A place in the queue.</h2>
            <p>How many people?</p>
            <Party value={party} setValue={setParty} />
            <div className="checks">
              <label>
                <input
                  type="checkbox"
                  checked={windowSeat}
                  onChange={(e) => setWindowSeat(e.target.checked)}
                />{" "}
                Window seat
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={arrived}
                  onChange={(e) => setArrived(e.target.checked)}
                />{" "}
                Arrived already
              </label>
            </div>
            <button
              className="full"
              disabled={offline || busy}
              onClick={() =>
                work(async () => {
                  const g = await api(`/api/store/${storeId}/groups`, {
                    party_size: party,
                    wants_window: windowSeat,
                    arrived,
                  });
                  setIssued({
                    ...g,
                    ...(await api(
                      `/api/store/groups/${g.group_id}/watch-code`,
                      {},
                    )),
                  });
                  await refresh();
                })
              }
            >
              Add to queue and issue watch code
            </button>
          </div>
        )}
        {issued && (
          <div className="modal-backdrop">
            <div className="panel modal">
              <div className="eyebrow">ADDED · {issued.ticket_code}</div>
              <h2>Your place is saved.</h2>
              <p>Enter at {window.location.host}/w</p>
              <div className="watch-code">
                {issued.watch_code?.split("").join(" ")}
              </div>
              <p>
                Read-only queue updates. Valid until the ticket ends or the code
                expires.
              </p>
              <div className="actions">
                <button
                  onClick={() =>
                    work(async () => {
                      await api("/api/simulator/print", {
                        job_id: crypto.randomUUID(),
                        group_id: issued.group_id,
                      });
                      window.print();
                    })
                  }
                >
                  Print ticket
                </button>
                <button
                  className="secondary"
                  onClick={() => {
                    setIssued(null);
                    setTab("Queue");
                  }}
                >
                  Back to queue
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </Shell>
  );
}
function Kiosk() {
  const { store } = useParams(),
    [party, setParty] = useState(2),
    [windowSeat, setWindowSeat] = useState(false),
    [ticket, setTicket] = useState<any>();
  const { work, error, busy } = useWork();
  return (
    <Shell section="Kiosk check-in">
      <main className="kiosk">
        <div className="eyebrow">WELCOME TO THE TABLE</div>
        <h1>{ticket ? "You’re on the list." : "Good company.\nGreat food."}</h1>
        <Notice>{error}</Notice>
        {auth()?.store_id !== store ? (
          <p>
            Open the enrolled kiosk from{" "}
            <Link to={"/settings/" + store}>store settings</Link>.
          </p>
        ) : ticket ? (
          <>
            <div className="ticket-number giant">{ticket.ticket_code}</div>
            <div className="watch-code">{ticket.watch_code}</div>
            <p>
              Keep this code to watch your place at {window.location.host}/w.
            </p>
            <button
              onClick={() =>
                work(async () => {
                  await api("/api/simulator/print", {
                    job_id: ticket.print_job_id,
                    group_id: ticket.group_id,
                  });
                  window.print();
                })
              }
            >
              Print / retry ticket
            </button>
            <button className="secondary" onClick={() => setTicket(null)}>
              Next guest →
            </button>
          </>
        ) : (
          <>
            <p>How many are joining us?</p>
            <Party value={party} setValue={setParty} />
            <label className="check-block">
              <input
                type="checkbox"
                checked={windowSeat}
                onChange={(e) => setWindowSeat(e.target.checked)}
              />{" "}
              We'd prefer a window seat
            </label>
            <button
              className="full"
              disabled={busy}
              onClick={() =>
                work(async () => {
                  const result = await api(
                    `/api/kiosk/stores/${store}/groups`,
                    { party_size: party, wants_window: windowSeat },
                  );
                  setTicket({ ...result, print_job_id: crypto.randomUUID() });
                })
              }
            >
              Check in — {party} people →
            </button>
          </>
        )}
      </main>
    </Shell>
  );
}
function Stores() {
  const [query, setQuery] = useState(""),
    [stores, setStores] = useState<any[]>([]);
  const { work, error } = useWork();
  useEffect(() => {
    const t = setTimeout(
      () =>
        void work(async () =>
          setStores(
            await api(
              "/api/customer/stores?query=" + encodeURIComponent(query),
            ),
          ),
        ),
      200,
    );
    return () => clearTimeout(t);
  }, [query]);
  return (
    <Mobile back="/">
      <div className="mobile-body">
        <div className="eyebrow">FIND YOUR NEXT TABLE</div>
        <h1>Where to?</h1>
        <label>
          Search restaurants
          <input
            aria-label="Search restaurants"
            placeholder="Store name or code"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <Notice>{error}</Notice>
        <div className="eyebrow spaced">OUR RESTAURANTS</div>
        {stores.map((s) => (
          <Link
            className="store-card"
            key={s.store_id}
            to={"/join/" + s.store_id}
          >
            <div>
              <b>{s.store_name}</b>
              <small>{s.address}</small>
              <span className="pill">{title(s.store_status)}</span>
            </div>
            <strong>↗</strong>
          </Link>
        ))}
        <Link className="button secondary full" to="/w">
          Enter a watch code
        </Link>
      </div>
    </Mobile>
  );
}
function Join() {
  const { store, qr } = useParams(),
    [s, setStore] = useState<any>(),
    [party, setParty] = useState(2),
    [windowSeat, setWindowSeat] = useState(false),
    [pos, setPos] = useState<GeolocationPosition>();
  const { work, error, busy } = useWork(),
    nav = useNavigate();
  useEffect(() => {
    void work(async () => {
      await api("/api/customer/context");
      if (qr) {
        const found = await api("/api/customer/qr/" + qr);
        setStore(found);
      } else
        setStore(
          (await api("/api/customer/stores?query=")).find(
            (x: any) => x.store_id === store,
          ),
        );
    });
  }, [store, qr]);
  return (
    <Mobile>
      <div className="mobile-body">
        <div className="eyebrow">A PLACE AT THE TABLE</div>
        <h1>{s?.store_name || "Join the queue."}</h1>
        <Notice>{error}</Notice>
        <p>
          Choose your party size. We’ll keep your place while you enjoy the
          neighbourhood.
        </p>
        <Party value={party} setValue={setParty} />
        <label className="check-block">
          <input
            type="checkbox"
            checked={windowSeat}
            onChange={(e) => setWindowSeat(e.target.checked)}
          />{" "}
          Window seat, please
        </label>
        <button
          className="secondary full"
          onClick={() => work(async () => setPos(await location()))}
        >
          {pos ? "✓ Location ready — refresh" : "Check my location"}
        </button>
        <button
          className="full"
          disabled={!s || busy}
          onClick={() =>
            work(async () => {
              const p = await location();
              setPos(p);
              const out = await api(
                `/api/customer/stores/${s.store_id}/groups`,
                {
                  party_size: party,
                  wants_window: windowSeat,
                  latitude: p.coords.latitude,
                  longitude: p.coords.longitude,
                  location_accuracy: p.coords.accuracy,
                  location_time: new Date(p.timestamp).toISOString(),
                },
              );
              sessionStorage.setItem("owner:" + out.group_id, out.owner_token);
              nav("/ticket/" + out.group_id);
            })
          }
        >
          Join — {party} people →
        </button>
        <p className="muted">
          Joining requires a fresh location within this store’s radius. Confirm
          arrival separately when you reach the restaurant.
        </p>
      </div>
    </Mobile>
  );
}
function Watch() {
  const [code, setCode] = useState("");
  const { work, error, busy } = useWork(),
    nav = useNavigate();
  useEffect(() => {
    void work(() => api("/api/customer/context"));
  }, []);
  const submit = () =>
    work(async () => {
      const result = await api("/api/customer/watch/exchange", {
        watch_code: code,
      });
      nav("/ticket/" + result.group_id);
    });
  return (
    <Mobile>
      <div className="mobile-body">
        <div className="eyebrow">YOUR PLACE IS SAVED</div>
        <h1>
          Enter your
          <br />
          watch code.
        </h1>
        <p>The four digits on your waiting ticket.</p>
        <Notice>{error}</Notice>
        <div className="code-cells" aria-label="Entered watch code">
          {Array.from({ length: 4 }, (_, i) => (
            <div className={i === code.length ? "active" : ""} key={i}>
              {code[i] || "—"}
            </div>
          ))}
        </div>
        <div className="keypad">
          {[
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "Clear",
            "0",
            "Back",
          ].map((x) => (
            <button
              className="secondary"
              key={x}
              onClick={() =>
                setCode(
                  x === "Clear"
                    ? ""
                    : x === "Back"
                      ? code.slice(0, -1)
                      : (code + x).slice(0, 4),
                )
              }
            >
              {x}
            </button>
          ))}
        </div>
        <button
          className="full"
          disabled={code.length !== 4 || busy}
          onClick={submit}
        >
          Watch my queue →
        </button>
        <p className="muted">
          No sign-in. No personal details. Just your place in line.
        </p>
      </div>
    </Mobile>
  );
}
function Ticket() {
  const { group } = useParams(),
    [status, setStatus] = useState<any>(),
    [arrival, setArrival] = useState(false);
  const owner = sessionStorage.getItem("owner:" + group);
  const { work, error, setError, busy } = useWork();
  const headers: Record<string, string> = owner
    ? { Authorization: "Bearer " + owner }
    : {};
  const refresh = async () =>
    setStatus(
      await api("/api/customer/tickets/" + group, undefined, "GET", headers),
    );
  useEffect(() => {
    void work(refresh);
    let stopped = false;
    const controller = new AbortController();
    const stream = async () => {
      try {
        const res = await fetch("/api/customer/tickets/" + group + "/events", {
          headers,
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error();
        const reader = res.body.getReader();
        while (!stopped) {
          const v = await reader.read();
          if (v.done) break;
          await refresh();
        }
      } catch {
        /* Polling remains the fallback. */
      }
    };
    void stream();
    const timer = setInterval(
      () => void refresh().catch((e) => setError(e.message)),
      5000,
    );
    return () => {
      stopped = true;
      controller.abort();
      clearInterval(timer);
    };
  }, [group]);
  const action = (name: string) =>
    work(async () => {
      await api(
        `/api/groups/${group}/${name}`,
        name === "defer" ? { expected_call_id: status.call_id } : {},
        "POST",
        headers,
      );
      await refresh();
    });
  return (
    <Mobile>
      <Notice>{error}</Notice>
      {status ? (
        <>
          <div
            className={
              status.group_status === "called" ? "called-hero" : "mobile-body"
            }
          >
            {status.group_status === "called" ? (
              <>
                <div className="eyebrow">YOUR TABLE IS READY</div>
                <h1>Now.</h1>
                <h3>Head to {status.assigned_table}</h3>
                <p>Let the team know you’re here.</p>
              </>
            ) : (
              <>
                <div className="eyebrow">{title(status.group_status)}</div>
                <h1>
                  Your place.
                  <br />
                  Your time.
                </h1>
                <div className="ahead">
                  <span className="eyebrow">GROUPS AHEAD OF YOU</span>
                  <strong>{status.groups_ahead}</strong>
                  <p>Groups competing for tables that fit your party.</p>
                </div>
              </>
            )}
          </div>
          <div className="mobile-body">
            <Stats
              items={[
                ["Ticket", status.ticket_code],
                ["Party", status.party_size],
                ["Arrival", status.arrival_confirmed ? "Confirmed" : "Not yet"],
                [
                  "Joined",
                  new Date(status.joined_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  }),
                ],
              ]}
            />
            {owner &&
              !status.arrival_confirmed &&
              status.group_status === "waiting" && (
                <button className="full" onClick={() => setArrival(!arrival)}>
                  I'm at the restaurant
                </button>
              )}
            {arrival && (
              <FieldForm
                fields={[
                  {
                    name: "arrival_code",
                    label: "Arrival code shown at the store",
                  },
                ]}
                button="Confirm arrival"
                onSubmit={(b) =>
                  work(async () => {
                    const p = await location();
                    await api(
                      `/api/groups/${group}/arrival`,
                      {
                        ...b,
                        latitude: p.coords.latitude,
                        longitude: p.coords.longitude,
                      },
                      "POST",
                      headers,
                    );
                    setArrival(false);
                    await refresh();
                  })
                }
              />
            )}{" "}
            {status.can_defer && (
              <button
                disabled={busy}
                className="full"
                onClick={() => action("defer")}
              >
                I need a moment — defer
              </button>
            )}
            {status.can_cancel && (
              <button
                disabled={busy}
                className="secondary full"
                onClick={() => action("cancel")}
              >
                Leave the queue
              </button>
            )}
            {!owner && (
              <p className="muted">
                You’re watching this ticket. Ask staff if you need to change it.
              </p>
            )}
            <Link className="button secondary full" to="/stores">
              Stop watching
            </Link>
          </div>
        </>
      ) : (
        <div className="mobile-body">Loading your ticket…</div>
      )}
    </Mobile>
  );
}
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/hq" element={<HeadOffice />} />
        <Route path="/settings/:store" element={<Settings />} />
        <Route path="/tablet/:store" element={<Tablet />} />
        <Route path="/kiosk/:store" element={<Kiosk />} />
        <Route path="/stores" element={<Stores />} />
        <Route path="/join/:store" element={<Join />} />
        <Route path="/q/:qr" element={<Join />} />
        <Route path="/w" element={<Watch />} />
        <Route path="/ticket/:group" element={<Ticket />} />
        <Route
          path="*"
          element={
            <Mobile>
              <div className="mobile-body">
                <h1>Page not found.</h1>
                <Link to="/">Return home</Link>
              </div>
            </Mobile>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
