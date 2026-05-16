/**
 * When the UI locale is English but backend-driven copy is primarily CJK,
 * swap to a localized fallback line (does not translate arbitrary prose).
 */
import { i18n } from "../i18n";
import type { Translate } from "./messageSanitizer";

const HAN_RE = /\p{Script=Han}/u;

export function textLooksPrimarilyCjk(s: string): boolean {
  const t = s.trim();
  if (!t.length) return false;
  let han = 0;
  for (const ch of t) {
    if (HAN_RE.test(ch)) han++;
  }
  return han / t.length >= 0.15;
}

export function resolveUiLocale(explicit?: string): string {
  if (explicit && explicit.trim()) return explicit;
  try {
    return String(i18n.global.locale.value || "");
  } catch {
    return "";
  }
}

export function englishUiLocalizedFallback(raw: string, t: Translate | undefined, fallbackKey: string, locale?: string): string {
  const loc = resolveUiLocale(locale).toLowerCase();
  if (!loc.startsWith("en")) return raw;
  if (!textLooksPrimarilyCjk(raw)) return raw;
  return t ? String(t(fallbackKey)) : raw;
}
