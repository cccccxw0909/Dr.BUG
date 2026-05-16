<template>
  <div v-if="data" style="border:1px solid #999;padding:10px;margin-top:10px;">
    <h4>{{ $t("components.confirmation.title") }}</h4>
    <div><b>recognized_action:</b> {{ data.recognized_action }}</div>
    <div><b>can_confirm:</b> {{ data.can_confirm }}</div>
    <div><b>pending_status:</b> {{ data.pending_confirmation?.status || "none" }}</div>
    <div><b>missing_fields:</b> {{ data.missing_fields.join(", ") || "none" }}</div>
    <div v-if="data.missing_fields.length > 0" style="color:#b00020;">
      {{ $t("components.confirmation.missingParams", { fields: data.missing_fields.join(', ') }) }}
    </div>
    <div v-if="data.pending_confirmation && data.pending_confirmation.status !== 'pending'" style="color:#b00020;">
      {{ $t("components.confirmation.invalidPendingStatus", { status: data.pending_confirmation.status }) }}
    </div>
    <div>
      <b>completed_params:</b>
      <pre style="white-space:pre-wrap;">{{ JSON.stringify(data.completed_params, null, 2) }}</pre>
    </div>
    <button class="wb-btn wb-btn-primary" :disabled="confirmDisabled" @click="$emit('confirm')">{{ $t("components.confirmation.confirm") }}</button>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ChatTurnData } from "../types";

const props = defineProps<{ data: ChatTurnData | null }>();
defineEmits<{ (e: "confirm"): void }>();

const confirmDisabled = computed(() => {
  const data = props.data;
  if (!data || !data.pending_confirmation) return true;
  if (!data.can_confirm) return true;
  if (data.missing_fields.length > 0) return true;
  return data.pending_confirmation.status !== "pending";
});
</script>

