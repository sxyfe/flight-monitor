<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppHeader from "@/components/AppHeader.vue";
import DashboardView from "@/views/DashboardView.vue";
import HistoryView from "@/views/HistoryView.vue";
import OnboardingView from "@/views/OnboardingView.vue";
import SettingsView from "@/views/SettingsView.vue";
import { useMonitorStore } from "@/stores/monitor";
import { useSetupStore } from "@/stores/setup";

type ViewName = "onboarding" | "dashboard" | "history" | "settings";

const setupStore = useSetupStore();
const monitorStore = useMonitorStore();
const view = ref<ViewName>("dashboard");
const bootstrapping = ref(true);

const headerView = computed<ViewName>(() =>
  setupStore.bootstrap?.onboardingComplete ? view.value : "onboarding",
);

onMounted(async () => {
  await setupStore.refresh();
  await monitorStore.bootstrap();
  await monitorStore.bindEvents();
  view.value = setupStore.bootstrap?.onboardingComplete ? "dashboard" : "onboarding";
  bootstrapping.value = false;
});

function navigate(next: Exclude<ViewName, "onboarding">) {
  view.value = next;
}
</script>

<template>
  <div class="app-shell">
    <AppHeader :active="headerView" @navigate="navigate" />

    <main v-if="!bootstrapping">
      <OnboardingView v-if="!setupStore.bootstrap?.onboardingComplete" />
      <DashboardView v-else-if="view === 'dashboard'" />
      <HistoryView v-else-if="view === 'history'" />
      <SettingsView v-else />
    </main>

    <p v-else class="loading mono">Loading…</p>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding: 24px;
  display: grid;
  gap: 20px;
}

.loading {
  color: var(--color-text-muted);
}
</style>
