import { createI18n } from "vue-i18n";

import enUS from "./locales/en-US";
import zhCN from "./locales/zh-CN";

export type SupportedLocale = "zh-CN" | "en-US";

/** Matches `getInitialLocale()` when nothing is stored; single source for app + API header fallback. */
export const DEFAULT_APP_LOCALE: SupportedLocale = "en-US";

const STORAGE_KEY = "drbug.locale";

function isSupportedLocale(v: unknown): v is SupportedLocale {
  return v === "zh-CN" || v === "en-US";
}

export function getInitialLocale(): SupportedLocale {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (isSupportedLocale(raw)) return raw;
  } catch {
    // Ignore storage errors (private mode, quota, etc.).
  }
  return DEFAULT_APP_LOCALE;
}

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: getInitialLocale(),
  fallbackLocale: "en-US",
  messages: {
    "zh-CN": zhCN,
    "en-US": enUS,
  },
});

export function setLocale(locale: SupportedLocale) {
  i18n.global.locale.value = locale;
  try {
    localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    // Ignore storage errors (private mode, quota, etc.).
  }
}

