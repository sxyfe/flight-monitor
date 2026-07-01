<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { api } from "@/services/api";
import type { NotificationLogItem, PriceHistoryItem } from "@/types";

const { t } = useI18n();
const tab = ref<"poll" | "notify">("poll");
const polls = ref<PriceHistoryItem[]>([]);
const notifications = ref<NotificationLogItem[]>([]);

onMounted(async () => {
  polls.value = await api.getPriceHistory();
  notifications.value = await api.getNotificationLog();
});

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}
</script>

<template>
  <section class="history panel">
    <h2>{{ t("history.title") }}</h2>
    <div class="tabs">
      <button :class="{ active: tab === 'poll' }" @click="tab = 'poll'">{{ t("history.pollTab") }}</button>
      <button :class="{ active: tab === 'notify' }" @click="tab = 'notify'">{{ t("history.notifyTab") }}</button>
    </div>

    <div v-if="tab === 'poll'" class="list">
      <article v-for="item in polls" :key="item.id" class="item">
        <p class="mono">{{ formatTime(item.polledAt) }}</p>
        <p v-if="item.success && item.combinedTotal != null">¥{{ item.combinedTotal.toFixed(0) }}</p>
        <p v-else class="failed">{{ item.errorMessage ?? t("history.failed") }}</p>
      </article>
      <p v-if="!polls.length" class="empty">{{ t("history.empty") }}</p>
    </div>

    <div v-else class="list">
      <article v-for="item in notifications" :key="item.id" class="item">
        <p class="mono">{{ formatTime(item.sentAt) }} · ¥{{ item.combinedTotal.toFixed(0) }}</p>
        <pre>{{ item.message }}</pre>
      </article>
      <p v-if="!notifications.length" class="empty">{{ t("history.empty") }}</p>
    </div>
  </section>
</template>

<style scoped>
.history {
  padding: 24px;
  display: grid;
  gap: 16px;
}

h2 {
  margin: 0;
}

.tabs {
  display: flex;
  gap: 8px;
}

.tabs button {
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: transparent;
  padding: 8px 14px;
  color: var(--color-text-muted);
}

.tabs button.active {
  background: var(--color-accent-soft);
  color: var(--color-text);
  border-color: var(--color-accent);
}

.list {
  display: grid;
  gap: 12px;
}

.item {
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border);
}

.item p {
  margin: 0 0 6px;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.failed,
.empty {
  color: var(--color-text-muted);
}
</style>
