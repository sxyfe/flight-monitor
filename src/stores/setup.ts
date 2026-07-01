import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/services/api";
import type { AppBootstrapState } from "@/types";

export const useSetupStore = defineStore("setup", () => {
  const bootstrap = ref<AppBootstrapState | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const onboardingStep = ref(0);

  async function refresh() {
    loading.value = true;
    error.value = null;
    try {
      bootstrap.value = await api.getAppState();
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function saveApiKey(key: string) {
    await api.saveApiKey(key);
    await refresh();
  }

  async function validateApiKey(key?: string) {
    await api.validateApiKey(key);
    if (key) {
      await api.saveApiKey(key);
      await refresh();
    }
  }

  async function saveWebhook(url: string) {
    await api.saveWebhook(url);
    await refresh();
  }

  async function testWebhook(url?: string) {
    await api.testWebhook(url);
    if (url) {
      await api.saveWebhook(url);
      await refresh();
    }
  }

  async function completeOnboarding() {
    await api.completeOnboarding();
    onboardingStep.value = 0;
    await refresh();
  }

  return {
    bootstrap,
    loading,
    error,
    onboardingStep,
    refresh,
    saveApiKey,
    validateApiKey,
    saveWebhook,
    testWebhook,
    completeOnboarding,
  };
});
