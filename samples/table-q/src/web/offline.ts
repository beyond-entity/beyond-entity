import Dexie, { type Table } from "dexie";
import { api, auth } from "./api";
export class TabletDB extends Dexie {
  tablet_session_snapshot!: Table<any, string>;
  tablet_group_cache!: Table<any, [string, string]>;
  tablet_table_cache!: Table<any, [string, string]>;
  tablet_command_journal!: Table<any, string>;
  constructor() {
    super("TableQTablet");
    this.version(1).stores({
      tablet_session_snapshot: "store_id",
      tablet_group_cache: "[store_id+group_id],store_id",
      tablet_table_cache: "[store_id+table_id],store_id",
      tablet_command_journal:
        "sync_command_id,store_id,[store_id+device_sequence]",
    });
  }
}
export const db = new TabletDB();
export const pending = (store: string) =>
  db.tablet_command_journal.where("store_id").equals(store).toArray();
export async function cached(store: string) {
  return {
    manifest: await db.tablet_session_snapshot.get(store),
    groups: await db.tablet_group_cache
      .where("store_id")
      .equals(store)
      .toArray(),
    tables: (
      await db.tablet_table_cache.where("store_id").equals(store).toArray()
    ).sort(
      (a, b) => a.row_number - b.row_number || a.row_position - b.row_position,
    ),
  };
}
export async function saveTabletSnapshot(store: string) {
  if ((await pending(store)).length) return cached(store);
  const manifest = await api(`/api/store/${store}/snapshot`);
  if (!manifest) return { manifest: null, groups: [], tables: [] };
  const suffix = `?state_version=${manifest.state_version}&sync_snapshot_revision=${manifest.sync_snapshot_revision}`;
  const [groupRows, tableRows] = await Promise.all([
    api(`/api/store/${store}/snapshot/groups${suffix}`),
    api(`/api/store/${store}/snapshot/tables${suffix}`),
  ]);
  const final = await api(`/api/store/${store}/snapshot`);
  if (
    final.state_version !== manifest.state_version ||
    final.sync_snapshot_revision !== manifest.sync_snapshot_revision
  )
    throw new Error("Snapshot changed; refresh again");
  // Explicit API → browser-owned row collections → IndexedDB handoff. No fetch in the transaction.
  await db.transaction(
    "rw",
    db.tablet_session_snapshot,
    db.tablet_group_cache,
    db.tablet_table_cache,
    db.tablet_command_journal,
    async () => {
      if ((await pending(store)).length)
        throw new Error("Local journal must reconcile before replacing cache");
      const prior = await db.tablet_session_snapshot.get(store);
      const same =
        prior?.session_id === manifest.session_id &&
        prior?.authority_epoch === manifest.authority_epoch;
      await db.tablet_group_cache.where("store_id").equals(store).delete();
      await db.tablet_table_cache.where("store_id").equals(store).delete();
      await db.tablet_group_cache.bulkPut(
        groupRows.map((row: any) => ({
          ...row,
          store_id: store,
          session_id: manifest.session_id,
        })),
      );
      await db.tablet_table_cache.bulkPut(
        tableRows.map((row: any) => ({
          ...row,
          store_id: store,
          layout_id: manifest.layout_id,
        })),
      );
      await db.tablet_session_snapshot.put({
        ...manifest,
        store_id: store,
        device_id: auth()?.device_id,
        next_device_sequence: Math.max(
          same ? prior.next_device_sequence : 1,
          manifest.next_device_sequence || 1,
        ),
        snapshot_complete: true,
        saved_at: new Date().toISOString(),
      });
    },
  );
  return cached(store);
}
export const fits = (g: any, t: any) =>
  t.seat_count >= g.party_size && (!g.wants_window || t.is_window);
export async function journalOfflineAction(
  store: string,
  operation: "call" | "seat" | "clear",
  target?: any,
) {
  await db.transaction(
    "rw",
    db.tablet_session_snapshot,
    db.tablet_group_cache,
    db.tablet_table_cache,
    db.tablet_command_journal,
    async () => {
      const { manifest: s, groups, tables } = await cached(store);
      if (!s?.snapshot_complete || s.owner_device_id !== auth()?.device_id)
        throw new Error(
          "An initialized authoritative tablet snapshot is required",
        );
      let g: any, t: any;
      if (operation === "call") {
        for (const candidate of groups
          .filter((g) => g.group_status === "waiting" && g.arrival_confirmed)
          .sort((a, b) => a.queue_sequence - b.queue_sequence)) {
          const fit = tables
            .filter((t) => t.table_status === "free" && fits(candidate, t))
            .sort(
              (a, b) =>
                a.seat_count - b.seat_count ||
                a.table_number.localeCompare(b.table_number),
            );
          if (fit.length) {
            g = candidate;
            t = fit[0];
            break;
          }
        }
        if (!g) throw new Error("No arrived group fits a free table");
        g = {
          ...g,
          group_status: "called",
          call_id: crypto.randomUUID(),
          allocation_id: crypto.randomUUID(),
          table_id: t.table_id,
        };
        t = { ...t, table_status: "held", allocation_id: g.allocation_id };
      } else if (operation === "seat") {
        g = groups.find((g) => g.group_id === target.group_id);
        t = tables.find((t) => t.table_id === g?.table_id);
        if (
          g?.group_status !== "called" ||
          t?.table_status !== "held" ||
          t.allocation_id !== g.allocation_id
        )
          throw new Error("The held table changed");
        g = { ...g, group_status: "seated" };
        t = { ...t, table_status: "occupied" };
      } else {
        t = tables.find((t) => t.table_id === target.table_id);
        g = groups.find((g) => g.allocation_id === t?.allocation_id);
        if (t?.table_status !== "occupied" || !g)
          throw new Error("This allocation cannot be cleared offline");
        g = { ...g, group_status: "completed" };
        t = { ...t, table_status: "free", allocation_id: null };
      }
      const command = {
        store_id: store,
        sync_command_id: crypto.randomUUID(),
        device_id: s.device_id,
        session_id: s.session_id,
        authority_epoch: s.authority_epoch,
        device_sequence: s.next_device_sequence,
        base_version: s.state_version,
        layout_id: s.layout_id,
        operation,
        group_id: g.group_id,
        call_id: g.call_id,
        allocation_id: g.allocation_id,
        table_id: t.table_id,
        occurred_at: new Date().toISOString(),
      };
      await db.tablet_command_journal.add(command);
      await db.tablet_group_cache.put(g);
      await db.tablet_table_cache.put(t);
      await db.tablet_session_snapshot.put({
        ...s,
        next_device_sequence: s.next_device_sequence + 1,
        state_version: s.state_version + 1,
      });
    },
  );
  return cached(store);
}
export async function syncJournal(store: string) {
  const commands = (await pending(store)).sort(
    (a, b) => a.device_sequence - b.device_sequence,
  );
  for (const c of commands) await api("/api/sync/commands", c);
  if (commands.length) {
    const s = commands[0];
    const results = await api(
      `/api/sync/commands?store_id=${store}&session_id=${s.session_id}&after_sequence=0`,
    );
    for (const result of results) {
      if (["applied", "rejected"].includes(result.sync_status))
        await db.tablet_command_journal.delete(result.sync_command_id);
      if (result.sync_status === "conflict")
        throw new Error(
          "Offline evidence needs manager review. Affected tables are quarantined.",
        );
    }
  }
  return (await pending(store)).length
    ? cached(store)
    : saveTabletSnapshot(store);
}
