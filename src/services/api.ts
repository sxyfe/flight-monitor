import { invoke } from "@tauri-apps/api/core";
import type {
  AppBootstrapState,
  AirportInfo,
  MonitorRule,
  MonitorRuleInput,
  NotificationLogItem,
  PollStatus,
  PriceHistoryItem,
} from "@/types";

export const api = {
  getAppState: () => invoke<AppBootstrapState>("get_app_state"),
  saveApiKey: (key: string) => invoke<void>("save_api_key_command", { key }),
  clearApiKey: () => invoke<void>("clear_api_key_command"),
  validateApiKey: (key?: string) => invoke<void>("validate_api_key_command", { key }),
  saveWebhook: (url: string) => invoke<void>("save_webhook_command", { url }),
  clearWebhook: () => invoke<void>("clear_webhook_command"),
  testWebhook: (url?: string) => invoke<void>("test_webhook_command", { url }),
  completeOnboarding: () => invoke<void>("complete_onboarding_command"),
  getMonitorRule: () => invoke<MonitorRule | null>("get_monitor_rule_command"),
  saveMonitorRule: (rule: MonitorRuleInput) =>
    invoke<MonitorRule>("save_monitor_rule_command", { rule }),
  getPollStatus: () => invoke<PollStatus>("get_poll_status_command"),
  triggerPollNow: () => invoke<PollStatus>("trigger_poll_now_command"),
  getPriceHistory: (limit = 30) =>
    invoke<PriceHistoryItem[]>("get_price_history_command", { limit }),
  getNotificationLog: (limit = 30) =>
    invoke<NotificationLogItem[]>("get_notification_log_command", { limit }),
  searchAirports: (keyword: string) =>
    invoke<AirportInfo[]>("search_airports_command", { keyword }),
  maskSecret: () => invoke<string | null>("mask_secret_command"),
  maskWebhook: () => invoke<string | null>("mask_webhook_command"),
};
