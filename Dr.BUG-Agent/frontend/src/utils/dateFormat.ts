/**
 * Site-wide datetime display: yyyy-MM-dd HH:mm, with seconds shown for second-level timestamps.
 */
export function formatDisplayDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const raw = String(iso).trim();
  if (!raw) return "—";
  const normalized = raw.includes("T") ? raw.replace("T", " ") : raw;
  const noZ = normalized.replace(/Z$/i, "");
  const m = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::(\d{2}))?/.exec(noZ);
  if (m) {
    const sec = m[3];
    return sec ? `${m[1]} ${m[2]}:${sec}` : `${m[1]} ${m[2]}`;
  }
  try {
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return raw;
    const y = d.getFullYear();
    const mo = String(d.getMonth() + 1).padStart(2, "0");
    const da = String(d.getDate()).padStart(2, "0");
    const h = String(d.getHours()).padStart(2, "0");
    const mi = String(d.getMinutes()).padStart(2, "0");
    const s = d.getSeconds();
    const ms = d.getMilliseconds();
    if (s > 0 || ms > 0) {
      return `${y}-${mo}-${da} ${h}:${mi}:${String(s).padStart(2, "0")}`;
    }
    return `${y}-${mo}-${da} ${h}:${mi}`;
  } catch {
    return raw;
  }
}
