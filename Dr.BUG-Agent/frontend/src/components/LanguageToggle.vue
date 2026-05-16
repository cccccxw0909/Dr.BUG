<template>
  <div
    class="language-toggle"
    role="group"
    :aria-label="$t('nav.language')"
  >
    <button
      type="button"
      class="language-toggle-btn"
      :class="{ 'is-active': locale === 'zh-CN' }"
      :aria-pressed="locale === 'zh-CN'"
      @click="pickLocale('zh-CN')"
    >
      {{ $t("nav.langToggleZh") }}
    </button>
    <button
      type="button"
      class="language-toggle-btn"
      :class="{ 'is-active': locale === 'en-US' }"
      :aria-pressed="locale === 'en-US'"
      @click="pickLocale('en-US')"
    >
      {{ $t("nav.langToggleEn") }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { setLocale, type SupportedLocale } from "../i18n";

const { locale } = useI18n();

function pickLocale(code: SupportedLocale) {
  setLocale(code);
}
</script>

<style scoped>
.language-toggle {
  display: inline-flex;
  flex-shrink: 0;
  align-items: stretch;
  min-width: 0;
  white-space: nowrap;
  border: 1px solid var(--wb-border);
  border-radius: var(--wb-radius-sm);
  overflow: hidden;
  background: var(--wb-surface-soft);
}

.language-toggle-btn {
  margin: 0;
  padding: var(--wb-space-1) var(--wb-space-3);
  min-width: 3rem;
  border: none;
  border-radius: 0;
  background: transparent;
  color: var(--wb-text-muted);
  font-family: inherit;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: var(--wb-font-size-sm);
  font-weight: 650;
  letter-spacing: 0.02em;
  line-height: 1.35;
  cursor: pointer;
  transition: background 120ms ease, color 120ms ease;
}

.language-toggle-btn + .language-toggle-btn {
  border-left: 1px solid var(--wb-border);
}

.language-toggle-btn:hover:not(.is-active) {
  background: var(--wb-surface);
  color: var(--wb-text-primary);
}

.language-toggle-btn.is-active {
  background: var(--wb-surface);
  color: var(--wb-text-primary);
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
}

.language-toggle-btn:focus-visible {
  outline: 2px solid var(--wb-accent);
  outline-offset: 2px;
  z-index: 1;
}
</style>
