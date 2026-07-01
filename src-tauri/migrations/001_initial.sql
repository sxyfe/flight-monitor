CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_rules (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  name TEXT NOT NULL,
  trip_type TEXT NOT NULL,
  max_price REAL NOT NULL,
  adult_count INTEGER NOT NULL DEFAULT 1,
  child_count INTEGER NOT NULL DEFAULT 0,
  cabin_grade TEXT NOT NULL DEFAULT 'ECONOMY',
  return_date TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_id INTEGER NOT NULL REFERENCES monitor_rules(id) ON DELETE CASCADE,
  segment_order INTEGER NOT NULL,
  from_city TEXT NOT NULL,
  to_city TEXT NOT NULL,
  from_date TEXT NOT NULL,
  UNIQUE(rule_id, segment_order)
);

CREATE TABLE IF NOT EXISTS price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_id INTEGER NOT NULL,
  polled_at TEXT NOT NULL,
  combined_total REAL,
  success INTEGER NOT NULL,
  error_message TEXT,
  segments_json TEXT
);

CREATE TABLE IF NOT EXISTS notification_state (
  rule_id INTEGER PRIMARY KEY,
  last_notified_price REAL,
  last_notified_at TEXT,
  last_total_price REAL
);

CREATE TABLE IF NOT EXISTS notification_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_id INTEGER NOT NULL,
  sent_at TEXT NOT NULL,
  combined_total REAL NOT NULL,
  success INTEGER NOT NULL,
  message TEXT NOT NULL
);
