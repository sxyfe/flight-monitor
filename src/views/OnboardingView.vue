<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { openUrl } from "@tauri-apps/plugin-opener";
import MonitorForm from "@/components/MonitorForm.vue";
import { useMonitorStore } from "@/stores/monitor";
import { useSetupStore } from "@/stores/setup";
import type { MonitorRuleInput } from "@/types";

const setupStore = useSetupStore();
const monitorStore = useMonitorStore();
const { t } = useI18n();

const apiKey = ref("");
const webhookUrl = ref("");
const busy = ref(false);
const message = ref<string | null>(null);

async function run(action: () => Promise<void>) {
  busy.value = true;
  message.value = null;
  try {
    await action();
    message.value = t("common.success");
  } catch (err) {
    message.value = String(err);
  } finally {
    busy.value = false;
  }
}

async function openApplyPage() {
  await openUrl("https://rollinggo.store/");
}

async function handleKeyStep() {
  await run(async () => {
    await setupStore.validateApiKey(apiKey.value);
    setupStore.onboardingStep = 2;
  });
}

async function handleWebhookStep() {
  await run(async () => {
    await setupStore.testWebhook(webhookUrl.value);
    setupStore.onboardingStep = 3;
  });
}

async function handleMonitorStep(rule: MonitorRuleInput) {
  await run(async () => {
    await monitorStore.saveRule(rule);
    await setupStore.completeOnboarding();
  });
}
</script>

<template>
  <section class="onboarding panel">
    <div class="steps mono">Step {{ setupStore.onboardingStep + 1 }} / 4</div>

    <template v-if="setupStore.onboardingStep === 0">
      <h2>{{ t("onboarding.welcomeTitle") }}</h2>
      <p>{{ t("onboarding.welcomeBody") }}</p>
      <p class="notice">{{ t("onboarding.welcomeNotice") }}</p>
      <button class="primary" @click="setupStore.onboardingStep = 1">{{ t("common.continue") }}</button>
    </template>

    <template v-else-if="setupStore.onboardingStep === 1">
      <h2>{{ t("onboarding.keyTitle") }}</h2>
      <p>{{ t("onboarding.keyBody") }}</p>
      <div class="actions">
        <button class="ghost" @click="openApplyPage">{{ t("common.openLink") }}</button>
      </div>
      <input v-model="apiKey" :placeholder="t('onboarding.keyPlaceholder')" />
      <div class="actions">
        <button class="ghost" @click="setupStore.onboardingStep = 0">{{ t("common.back") }}</button>
        <button class="primary" :disabled="busy || !apiKey" @click="handleKeyStep">
          {{ t("common.verify") }}
        </button>
      </div>
    </template>

    <template v-else-if="setupStore.onboardingStep === 2">
      <h2>{{ t("onboarding.webhookTitle") }}</h2>
      <p>{{ t("onboarding.webhookBody") }}</p>
      <input v-model="webhookUrl" :placeholder="t('onboarding.webhookPlaceholder')" />
      <div class="actions">
        <button class="ghost" @click="setupStore.onboardingStep = 1">{{ t("common.back") }}</button>
        <button class="primary" :disabled="busy || !webhookUrl" @click="handleWebhookStep">
          {{ t("common.test") }}
        </button>
      </div>
    </template>

    <template v-else>
      <h2>{{ t("onboarding.monitorTitle") }}</h2>
      <p>{{ t("onboarding.monitorBody") }}</p>
      <MonitorForm :submit-label="t('common.finish')" @submit="handleMonitorStep" />
    </template>

    <p v-if="message" class="message">{{ message }}</p>
  </section>
</template>

<style scoped>
.onboarding {
  padding: 28px;
  display: grid;
  gap: 16px;
}

.steps {
  color: var(--color-accent);
  font-size: 12px;
  letter-spacing: 0.12em;
}

h2 {
  margin: 0;
  font-family: var(--font-display);
}

p {
  margin: 0;
  color: var(--color-text-muted);
}

.notice {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--color-accent-soft);
  color: var(--color-text);
}

input {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  background: var(--color-bg-muted);
  color: var(--color-text);
}

.actions {
  display: flex;
  gap: 10px;
}

button {
  border-radius: 999px;
  padding: 10px 16px;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text);
}

button.primary {
  background: var(--color-accent);
  border-color: transparent;
  color: white;
}

button.ghost {
  color: var(--color-text-muted);
}

.message {
  color: var(--color-warning);
}
</style>
