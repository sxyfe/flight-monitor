<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { isEnabled, enable, disable } from "@tauri-apps/plugin-autostart";
import MonitorForm from "@/components/MonitorForm.vue";
import { api } from "@/services/api";
import { useMonitorStore } from "@/stores/monitor";
import type { MonitorRuleInput } from "@/types";

const { t } = useI18n();
const monitorStore = useMonitorStore();
const launchAtLogin = ref(false);
const maskedKey = ref<string | null>(null);
const maskedWebhook = ref<string | null>(null);
const apiKey = ref("");
const webhookUrl = ref("");
const message = ref<string | null>(null);

onMounted(async () => {
  launchAtLogin.value = await isEnabled();
  maskedKey.value = await api.maskSecret();
  maskedWebhook.value = await api.maskWebhook();
  await monitorStore.refreshRule();
});

async function saveKey() {
  try {
    await api.validateApiKey(apiKey.value);
    await api.saveApiKey(apiKey.value);
    maskedKey.value = await api.maskSecret();
    apiKey.value = "";
    message.value = t("common.success");
  } catch (err) {
    message.value = String(err);
  }
}

async function saveWebhook() {
  try {
    await api.testWebhook(webhookUrl.value);
    await api.saveWebhook(webhookUrl.value);
    maskedWebhook.value = await api.maskWebhook();
    webhookUrl.value = "";
    message.value = t("common.success");
  } catch (err) {
    message.value = String(err);
  }
}

async function saveRule(rule: MonitorRuleInput) {
  try {
    await monitorStore.saveRule(rule);
    message.value = t("common.success");
  } catch (err) {
    message.value = String(err);
  }
}

async function toggleAutostart() {
  if (launchAtLogin.value) {
    await enable();
  } else {
    await disable();
  }
}
</script>

<template>
  <section class="settings">
    <article class="panel block">
      <h2>{{ t("settings.title") }}</h2>
      <p class="notice">{{ t("settings.computerNotice") }}</p>
      <label class="switch">
        <input v-model="launchAtLogin" type="checkbox" @change="toggleAutostart" />
        <span>{{ t("settings.launchAtLogin") }}</span>
      </label>
    </article>

    <article class="panel block">
      <h3>{{ t("settings.apiKey") }}</h3>
      <p class="mono muted">{{ maskedKey ?? "—" }}</p>
      <input v-model="apiKey" :placeholder="t('onboarding.keyPlaceholder')" />
      <button @click="saveKey">{{ t("settings.replaceKey") }}</button>
    </article>

    <article class="panel block">
      <h3>{{ t("settings.webhook") }}</h3>
      <p class="mono muted">{{ maskedWebhook ?? "—" }}</p>
      <input v-model="webhookUrl" :placeholder="t('onboarding.webhookPlaceholder')" />
      <button @click="saveWebhook">{{ t("settings.replaceWebhook") }}</button>
    </article>

    <MonitorForm
      :initial="monitorStore.rule"
      :submit-label="t('common.save')"
      @submit="saveRule"
    />

    <p v-if="message" class="message">{{ message }}</p>
  </section>
</template>

<style scoped>
.settings {
  display: grid;
  gap: 18px;
}

.block {
  padding: 22px;
  display: grid;
  gap: 12px;
}

h2,
h3 {
  margin: 0;
}

.notice,
.muted {
  color: var(--color-text-muted);
}

input {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  background: var(--color-bg-muted);
  color: var(--color-text);
}

button {
  width: fit-content;
  border-radius: 999px;
  padding: 10px 16px;
  border: 1px solid var(--color-border);
  background: var(--color-accent-soft);
}

.switch {
  display: flex;
  gap: 10px;
  align-items: center;
}

.message {
  color: var(--color-success);
}
</style>
