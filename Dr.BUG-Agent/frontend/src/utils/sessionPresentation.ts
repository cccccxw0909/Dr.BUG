import type { SessionItem } from "../types";
import type { Translate } from "./messageSanitizer";

const LEGACY_NEW_SESSION_EN = /^New session\s+(\d+)\s*$/i;

function isLegacyCurrentSessionLabel(s: string): boolean {
  const x = s.trim();
  return x === "Current session" || x.toLowerCase() === "current session";
}

function parsePositiveInt(v: unknown): number | undefined {
  if (typeof v === "number" && Number.isFinite(v) && v >= 1) return Math.floor(v);
  if (typeof v === "string" && /^\d+$/.test(v.trim())) {
    const n = Number.parseInt(v.trim(), 10);
    if (Number.isFinite(n) && n >= 1) return n;
  }
  return undefined;
}

/**
 * Normalize persisted sessions: stop storing default titles as fixed localized strings.
 * Legacy rows may include English default titles from older builds; those are mapped to defaultSlot only.
 */
export function migrateSessionsFromStorage(raw: unknown[]): SessionItem[] {
  if (!Array.isArray(raw)) return [];
  const rows = raw.filter((x): x is Record<string, unknown> => Boolean(x) && typeof x === "object");
  const out: SessionItem[] = [];

  for (const row of rows) {
    const id = String(row.id || "").trim();
    if (!id) continue;
    const created_at = String(row.created_at || new Date().toISOString());

    let defaultSlot = parsePositiveInt(row.defaultSlot);
    let customTitle =
      typeof row.customTitle === "string" && row.customTitle.trim() ? String(row.customTitle).trim() : undefined;
    const legacyTitle = typeof row.title === "string" ? row.title.trim() : "";

    if (!customTitle && legacyTitle && defaultSlot == null) {
      if (isLegacyCurrentSessionLabel(legacyTitle)) {
        defaultSlot = 1;
      } else {
        const mEn = legacyTitle.match(LEGACY_NEW_SESSION_EN);
        const n = mEn?.[1];
        const parsed = n ? Number.parseInt(n, 10) : NaN;
        if (Number.isFinite(parsed) && parsed >= 1) {
          defaultSlot = parsed;
        } else {
          customTitle = legacyTitle;
        }
      }
    }

    const item: SessionItem = { id, created_at };
    if (defaultSlot != null) item.defaultSlot = defaultSlot;
    if (customTitle) item.customTitle = customTitle;
    if (row.workbenchWelcomeIntroPinned === true) item.workbenchWelcomeIntroPinned = true;
    out.push(item);
  }

  let maxSlot = out.reduce((m, s) => Math.max(m, s.defaultSlot ?? 0), 0);
  for (const s of out) {
    if (!s.customTitle && (s.defaultSlot == null || s.defaultSlot < 1)) {
      maxSlot += 1;
      s.defaultSlot = maxSlot;
    } else if (s.defaultSlot != null) {
      maxSlot = Math.max(maxSlot, s.defaultSlot);
    }
  }

  return out;
}

export function sessionSidebarTitle(s: SessionItem, t: Translate): string {
  const ct = s.customTitle?.trim();
  if (ct) return ct;
  const slot = s.defaultSlot != null && s.defaultSlot > 0 ? s.defaultSlot : 1;
  return t("app.session.newSessionTitle", { n: slot });
}
