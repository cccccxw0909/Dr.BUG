<template>
  <div class="chat-input">
    <div class="chat-input-row">
      <textarea
        v-model="text"
        class="chat-input-field"
        rows="1"
        data-testid="chat-input-field"
        :placeholder="effectivePlaceholder"
        @keydown="onKeydown"
      />
      <button type="button" class="wb-btn wb-btn-primary chat-send-btn" data-testid="chat-send" @click="send">
        {{ effectiveSendLabel }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";

const props = withDefaults(
  defineProps<{
    placeholder?: string;
    sendLabel?: string;
  }>(),
  {
    placeholder: undefined,
    sendLabel: undefined,
  },
);

const { t: i18nT } = useI18n();

const effectivePlaceholder = computed(() => props.placeholder ?? i18nT("pages.workbench.chat.placeholder"));
const effectiveSendLabel = computed(() => props.sendLabel ?? i18nT("pages.workbench.chat.send"));

const emit = defineEmits<{
  (e: "send", text: string): void;
}>();
const text = ref("");

function send() {
  const v = text.value.trim();
  if (!v) return;
  emit("send", v);
  text.value = "";
}

function onKeydown(e: KeyboardEvent) {
  if (e.key !== "Enter") return;
  if (e.shiftKey) return;
  if (e.isComposing) return;
  e.preventDefault();
  send();
}
</script>

<style scoped>
.chat-input {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.chat-input-row {
  display: flex;
  align-items: flex-end;
  gap: var(--wb-space-2);
}

.chat-input-field {
  flex: 1;
  min-height: var(--wb-chat-textarea-min-height);
  max-height: var(--wb-chat-textarea-max-height);
  resize: vertical;
  border: 1px solid var(--wb-border-strong);
  border-radius: var(--wb-chat-embed-radius);
  background: #fff;
  color: var(--wb-text-primary);
  padding: var(--wb-chat-input-padding-y) var(--wb-chat-input-padding-x);
  outline: none;
  font-size: var(--wb-font-size-sm);
  line-height: var(--wb-line-height);
  font-family: inherit;
  transition: border-color 120ms ease, box-shadow 120ms ease, background-color 120ms ease;
  box-sizing: border-box;
  /* Chromium: grow with content so multiline input expands naturally; unsupported browsers keep single-line height with internal scrolling. */
  field-sizing: content;
}

.chat-input-field::placeholder {
  color: #8b94a3;
}

.chat-input-field:focus {
  border-color: #93a8c0;
  box-shadow: 0 0 0 3px rgba(143, 164, 188, 0.18);
}

.chat-send-btn {
  min-width: var(--wb-chat-send-min-width);
  flex-shrink: 0;
  align-self: flex-end;
}
</style>
