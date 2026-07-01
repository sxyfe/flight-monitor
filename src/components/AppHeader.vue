<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { SUPPORTED_LOCALES, type AppLocale } from "@/i18n";
import { THEME_MODES, useAppStore, type ThemeMode } from "@/stores/app";

defineProps<{
  active: "dashboard" | "history" | "settings" | "onboarding";
}>();

const emit = defineEmits<{
  navigate: [view: "dashboard" | "history" | "settings"];
}>();

const { t } = useI18n();
const appStore = useAppStore();
</script>

<template>
  <header class="topbar panel">
    <div>
      <p class="eyebrow mono">Flight Console</p>
      <h1>{{ t("app.name") }}</h1>
      <p class="subtitle">{{ t("app.tagline") }}</p>
    </div>

    <div class="controls">
      <nav v-if="active !== 'onboarding'" class="nav">
        <button :class="{ active: active === 'dashboard' }" @click="emit('navigate', 'dashboard')">
          {{ t("nav.dashboard") }}
        </button>
        <button :class="{ active: active === 'history' }" @click="emit('navigate', 'history')">
          {{ t("nav.history") }}
        </button>
        <button :class="{ active: active === 'settings' }" @click="emit('navigate', 'settings')">
          {{ t("nav.settings") }}
        </button>
      </nav>

      <label>
        <span>{{ t("common.language") }}</span>
        <select
          :value="appStore.locale"
          @change="appStore.updateLocale(($event.target as HTMLSelectElement).value as AppLocale)"
        >
          <option v-for="locale in SUPPORTED_LOCALES" :key="locale" :value="locale">
            {{ locale }}
          </option>
        </select>
      </label>

      <label>
        <span>{{ t("common.theme") }}</span>
        <select
          :value="appStore.theme"
          @change="appStore.updateTheme(($event.target as HTMLSelectElement).value as ThemeMode)"
        >
          <option v-for="mode in THEME_MODES" :key="mode" :value="mode">
            {{ t(`theme.${mode}`) }}
          </option>
        </select>
      </label>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 28px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-accent);
}

h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 3vw, 2.4rem);
}

.subtitle {
  margin: 8px 0 0;
  color: var(--color-text-muted);
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: end;
  justify-content: flex-end;
}

.nav {
  display: flex;
  gap: 8px;
}

.nav button {
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  border-radius: 999px;
  padding: 8px 14px;
}

.nav button.active {
  color: var(--color-text);
  border-color: var(--color-accent);
  background: var(--color-accent-soft);
}

label {
  display: grid;
  gap: 8px;
  min-width: 140px;
  color: var(--color-text-muted);
  font-size: 13px;
}

select {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--color-text);
  background: var(--color-bg-muted);
}

@media (max-width: 860px) {
  .topbar {
    flex-direction: column;
  }
}
</style>
