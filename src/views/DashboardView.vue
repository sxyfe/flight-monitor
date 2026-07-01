<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import RouteTimeline from "@/components/RouteTimeline.vue";
import { useMonitorStore } from "@/stores/monitor";

const monitorStore = useMonitorStore();
const { t } = useI18n();

const statusText = computed(() =>
  monitorStore.pollStatus?.polling
    ? t("monitor.pollingNow")
    : monitorStore.isReady
      ? t("monitor.running")
      : t("monitor.paused"),
);

function formatTime(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}
</script>

<template>
  <section class="dashboard">
    <RouteTimeline :rule="monitorStore.rule" :polling="monitorStore.pollStatus?.polling">
      <p class="route-caption">{{ monitorStore.rule?.name ?? t("monitor.noRule") }}</p>
    </RouteTimeline>

    <div class="status-grid">
      <article class="status-card panel">
        <p class="label">{{ statusText }}</p>
        <p class="value mono">{{ monitorStore.pollStatus?.lastCombinedTotal ? `¥${monitorStore.pollStatus.lastCombinedTotal.toFixed(0)}` : "—" }}</p>
        <p class="meta">{{ t("monitor.lastPrice") }}</p>
      </article>

      <article class="status-card panel">
        <p class="label mono">{{ formatTime(monitorStore.pollStatus?.lastPolledAt) }}</p>
        <p class="meta">{{ t("monitor.lastPoll") }}</p>
      </article>

      <article class="status-card panel">
        <p class="label mono">{{ formatTime(monitorStore.pollStatus?.nextPollAt) }}</p>
        <p class="meta">{{ t("monitor.nextPoll") }}</p>
      </article>
    </div>

    <div class="actions">
      <button class="primary" :disabled="!monitorStore.rule || monitorStore.pollStatus?.polling" @click="monitorStore.pollNow()">
        {{ t("common.refresh") }}
      </button>
      <p class="hint">{{ t("monitor.disclaimer") }}</p>
      <p v-if="monitorStore.pollStatus?.lastError" class="error">{{ monitorStore.pollStatus.lastError }}</p>
    </div>
  </section>
</template>

<style scoped>
.dashboard {
  display: grid;
  gap: 20px;
}

.route-caption {
  position: absolute;
  left: 28px;
  bottom: 24px;
  margin: 0;
  color: var(--color-text-muted);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.status-card {
  padding: 20px;
}

.label {
  margin: 0;
  font-size: 1.1rem;
}

.value {
  margin: 10px 0 0;
  font-size: 1.8rem;
  color: var(--color-success);
}

.meta {
  margin: 8px 0 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.actions {
  display: grid;
  gap: 10px;
}

button.primary {
  width: fit-content;
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  background: var(--color-accent);
  color: white;
}

.hint,
.error {
  margin: 0;
  font-size: 13px;
}

.error {
  color: var(--color-warning);
}

@media (max-width: 760px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
