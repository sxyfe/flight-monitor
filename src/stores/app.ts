import { defineStore } from "pinia";
import { ref, watch } from "vue";
import { type AppLocale, setLocale } from "../i18n";

export const THEME_MODES = ["light", "dark", "system", "claude"] as const;
export type ThemeMode = (typeof THEME_MODES)[number];

const storedTheme = localStorage.getItem("flight-monitor.theme");
const initialTheme: ThemeMode =
  storedTheme === "light" ||
  storedTheme === "dark" ||
  storedTheme === "system" ||
  storedTheme === "claude"
    ? storedTheme
    : "system";

function applyTheme(mode: ThemeMode) {
  document.documentElement.dataset.theme = mode;
  localStorage.setItem("flight-monitor.theme", mode);
}

export const useAppStore = defineStore("app", () => {
  const locale = ref<AppLocale>(
    (localStorage.getItem("flight-monitor.locale") as AppLocale) || "zh-CN",
  );
  const theme = ref<ThemeMode>(initialTheme);

  function updateLocale(next: AppLocale) {
    locale.value = next;
    setLocale(next);
  }

  function updateTheme(next: ThemeMode) {
    theme.value = next;
    applyTheme(next);
  }

  watch(
    theme,
    (value) => {
      applyTheme(value);
    },
    { immediate: true },
  );

  return {
    locale,
    theme,
    updateLocale,
    updateTheme,
  };
});
