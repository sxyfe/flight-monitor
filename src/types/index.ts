export interface MonitorSegment {
  segmentOrder: number;
  fromCity: string;
  toCity: string;
  fromDate: string;
}

export interface MonitorRule {
  id: number;
  name: string;
  tripType: "one_way" | "round_trip" | "multi_segment";
  maxPrice: number;
  adultCount: number;
  childCount: number;
  cabinGrade: string;
  returnDate?: string | null;
  segments: MonitorSegment[];
}

export interface MonitorRuleInput {
  name: string;
  tripType: MonitorRule["tripType"];
  maxPrice: number;
  adultCount: number;
  childCount: number;
  cabinGrade: string;
  returnDate?: string | null;
  segments: MonitorSegment[];
}

export interface AppBootstrapState {
  onboardingComplete: boolean;
  hasApiKey: boolean;
  hasWebhook: boolean;
  hasMonitor: boolean;
}

export interface PollStatus {
  running: boolean;
  lastPolledAt?: string | null;
  nextPollAt?: string | null;
  lastCombinedTotal?: number | null;
  lastError?: string | null;
  polling: boolean;
}

export interface PriceHistoryItem {
  id: number;
  polledAt: string;
  combinedTotal?: number | null;
  success: boolean;
  errorMessage?: string | null;
  segmentsJson?: string | null;
}

export interface NotificationLogItem {
  id: number;
  sentAt: string;
  combinedTotal: number;
  success: boolean;
  message: string;
}

export interface AirportInfo {
  airportCode: string;
  airportName: string;
  cityCode: string;
  cityName: string;
}
