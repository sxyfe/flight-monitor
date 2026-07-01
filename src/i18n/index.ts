import { createI18n } from "vue-i18n";
import enUS from "./locales/en-US";
import zhCN from "./locales/zh-CN";

export const SUPPORTED_LOCALES = ["zh-CN", "en-US"] as const;
export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

const storedLocale = localStorage.getItem("flight-monitor.locale");
const defaultLocale: AppLocale =
  storedLocale === "en-US" || storedLocale === "zh-CN" ? storedLocale : "zh-CN";

export const i18n = createI18n({
  legacy: false,
  locale: defaultLocale,
  fallbackLocale: "en-US",
  messages: {
    "zh-CN": zhCN,
    "en-US": enUS,
  },
});

export function setLocale(locale: AppLocale) {
  i18n.global.locale.value = locale;
  localStorage.setItem("flight-monitor.locale", locale);
  document.documentElement.lang = locale;
}

document.documentElement.lang = defaultLocale;
