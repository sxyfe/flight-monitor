import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { listen } from "@tauri-apps/api/event";
import { api } from "@/services/api";
import type { MonitorRule, MonitorRuleInput, PollStatus } from "@/types";

export const useMonitorStore = defineStore("monitor", () => {
  const rule = ref<MonitorRule | null>(null);
  const pollStatus = ref<PollStatus | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const isReady = computed(
    () => Boolean(pollStatus.value?.running && rule.value),
  );

  async function refreshRule() {
    rule.value = await api.getMonitorRule();
  }

  async function refreshPollStatus() {
    pollStatus.value = await api.getPollStatus();
  }

  async function bootstrap() {
    loading.value = true;
    error.value = null;
    try {
      await Promise.all([refreshRule(), refreshPollStatus()]);
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function saveRule(input: MonitorRuleInput) {
    rule.value = await api.saveMonitorRule(input);
    await refreshPollStatus();
  }

  async function pollNow() {
    pollStatus.value = await api.triggerPollNow();
    await refreshRule();
  }

  async function bindEvents() {
    await listen("poll-updated", () => {
      void refreshPollStatus();
    });
  }

  return {
    rule,
    pollStatus,
    loading,
    error,
    isReady,
    bootstrap,
    refreshRule,
    refreshPollStatus,
    saveRule,
    pollNow,
    bindEvents,
  };
});
