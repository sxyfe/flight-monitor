use chrono::{DateTime, Utc};
use rusqlite::params;
use serde::{Deserialize, Serialize};

use crate::db::DbState;
use crate::error::{AppError, AppResult};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MonitorSegment {
    pub segment_order: i32,
    pub from_city: String,
    pub to_city: String,
    pub from_date: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MonitorRule {
    pub id: i32,
    pub name: String,
    pub trip_type: String,
    pub max_price: f64,
    pub adult_count: i32,
    pub child_count: i32,
    pub cabin_grade: String,
    pub return_date: Option<String>,
    pub segments: Vec<MonitorSegment>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MonitorRuleInput {
    pub name: String,
    pub trip_type: String,
    pub max_price: f64,
    pub adult_count: i32,
    pub child_count: i32,
    pub cabin_grade: String,
    pub return_date: Option<String>,
    pub segments: Vec<MonitorSegment>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PriceHistoryItem {
    pub id: i64,
    pub polled_at: String,
    pub combined_total: Option<f64>,
    pub success: bool,
    pub error_message: Option<String>,
    pub segments_json: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct NotificationLogItem {
    pub id: i64,
    pub sent_at: String,
    pub combined_total: f64,
    pub success: bool,
    pub message: String,
}

#[derive(Debug, Clone, Default)]
pub struct NotificationState {
    pub last_notified_price: Option<f64>,
    pub last_notified_at: Option<DateTime<Utc>>,
    pub last_total_price: Option<f64>,
}

pub fn get_setting(db: &DbState, key: &str) -> AppResult<Option<String>> {
    db.with_conn(|conn| {
        let mut stmt = conn.prepare("SELECT value FROM app_settings WHERE key = ?1")?;
        let value = map_optional(stmt.query_row(params![key], |row| row.get(0)))?;
        Ok(value)
    })
}

pub fn set_setting(db: &DbState, key: &str, value: &str) -> AppResult<()> {
    db.with_conn(|conn| {
        conn.execute(
            "INSERT INTO app_settings(key, value) VALUES (?1, ?2)
             ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            params![key, value],
        )?;
        Ok(())
    })
}

pub fn is_onboarding_complete(db: &DbState) -> AppResult<bool> {
    Ok(get_setting(db, "onboarding_complete")?.as_deref() == Some("true"))
}

pub fn set_onboarding_complete(db: &DbState) -> AppResult<()> {
    set_setting(db, "onboarding_complete", "true")
}

pub fn get_monitor_rule(db: &DbState) -> AppResult<Option<MonitorRule>> {
    db.with_conn(|conn| {
        let mut stmt = conn.prepare(
            "SELECT id, name, trip_type, max_price, adult_count, child_count, cabin_grade, return_date
             FROM monitor_rules WHERE id = 1",
        )?;
        let rule = map_optional(stmt.query_row([], |row| {
            Ok((
                row.get::<_, i32>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, f64>(3)?,
                row.get::<_, i32>(4)?,
                row.get::<_, i32>(5)?,
                row.get::<_, String>(6)?,
                row.get::<_, Option<String>>(7)?,
            ))
        }))?;

        let Some((
            id,
            name,
            trip_type,
            max_price,
            adult_count,
            child_count,
            cabin_grade,
            return_date,
        )) = rule
        else {
            return Ok(None);
        };

        let mut seg_stmt = conn.prepare(
            "SELECT segment_order, from_city, to_city, from_date
             FROM monitor_segments WHERE rule_id = 1 ORDER BY segment_order ASC",
        )?;
        let segments = seg_stmt
            .query_map([], |row| {
                Ok(MonitorSegment {
                    segment_order: row.get(0)?,
                    from_city: row.get(1)?,
                    to_city: row.get(2)?,
                    from_date: row.get(3)?,
                })
            })?
            .collect::<Result<Vec<_>, _>>()?;

        Ok(Some(MonitorRule {
            id,
            name,
            trip_type,
            max_price,
            adult_count,
            child_count,
            cabin_grade,
            return_date,
            segments,
        }))
    })
}

pub fn save_monitor_rule(db: &DbState, input: MonitorRuleInput) -> AppResult<MonitorRule> {
    validate_rule(&input)?;
    let now = Utc::now().to_rfc3339();

    db.with_conn(|conn| {
        let tx = conn.unchecked_transaction()?;
        tx.execute("DELETE FROM monitor_segments WHERE rule_id = 1", [])?;
        tx.execute("DELETE FROM monitor_rules WHERE id = 1", [])?;
        tx.execute(
            "INSERT INTO monitor_rules(
                id, name, trip_type, max_price, adult_count, child_count, cabin_grade, return_date,
                enabled, created_at, updated_at
             ) VALUES (1, ?1, ?2, ?3, ?4, ?5, ?6, ?7, 1, ?8, ?8)",
            params![
                input.name,
                input.trip_type,
                input.max_price,
                input.adult_count,
                input.child_count,
                input.cabin_grade,
                input.return_date,
                now,
            ],
        )?;

        for segment in &input.segments {
            tx.execute(
                "INSERT INTO monitor_segments(rule_id, segment_order, from_city, to_city, from_date)
                 VALUES (1, ?1, ?2, ?3, ?4)",
                params![
                    segment.segment_order,
                    segment.from_city.to_uppercase(),
                    segment.to_city.to_uppercase(),
                    segment.from_date,
                ],
            )?;
        }

        tx.commit()?;
        Ok(())
    })?;

    get_monitor_rule(db)?.ok_or_else(|| AppError::Internal("failed to load saved monitor".into()))
}

pub fn insert_price_history(
    db: &DbState,
    combined_total: Option<f64>,
    success: bool,
    error_message: Option<&str>,
    segments_json: Option<&str>,
) -> AppResult<()> {
    let now = Utc::now().to_rfc3339();
    db.with_conn(|conn| {
        conn.execute(
            "INSERT INTO price_history(rule_id, polled_at, combined_total, success, error_message, segments_json)
             VALUES (1, ?1, ?2, ?3, ?4, ?5)",
            params![now, combined_total, success as i32, error_message, segments_json],
        )?;
        Ok(())
    })
}

pub fn get_price_history(db: &DbState, limit: i64) -> AppResult<Vec<PriceHistoryItem>> {
    db.with_conn(|conn| {
        let mut stmt = conn.prepare(
            "SELECT id, polled_at, combined_total, success, error_message, segments_json
             FROM price_history ORDER BY id DESC LIMIT ?1",
        )?;
        let rows = stmt
            .query_map(params![limit], |row| {
                Ok(PriceHistoryItem {
                    id: row.get(0)?,
                    polled_at: row.get(1)?,
                    combined_total: row.get(2)?,
                    success: row.get::<_, i32>(3)? == 1,
                    error_message: row.get(4)?,
                    segments_json: row.get(5)?,
                })
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    })
}

pub fn get_notification_log(db: &DbState, limit: i64) -> AppResult<Vec<NotificationLogItem>> {
    db.with_conn(|conn| {
        let mut stmt = conn.prepare(
            "SELECT id, sent_at, combined_total, success, message
             FROM notification_log ORDER BY id DESC LIMIT ?1",
        )?;
        let rows = stmt
            .query_map(params![limit], |row| {
                Ok(NotificationLogItem {
                    id: row.get(0)?,
                    sent_at: row.get(1)?,
                    combined_total: row.get(2)?,
                    success: row.get::<_, i32>(3)? == 1,
                    message: row.get(4)?,
                })
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    })
}

pub fn get_notification_state(db: &DbState) -> AppResult<NotificationState> {
    db.with_conn(|conn| {
        let mut stmt =
            conn.prepare("SELECT last_notified_price, last_notified_at, last_total_price FROM notification_state WHERE rule_id = 1")?;
        let row = map_optional(stmt.query_row([], |row| {
            Ok((
                row.get::<_, Option<f64>>(0)?,
                row.get::<_, Option<String>>(1)?,
                row.get::<_, Option<f64>>(2)?,
            ))
        }))?;

        Ok(match row {
            Some((last_notified_price, last_notified_at, last_total_price)) => NotificationState {
                last_notified_price,
                last_notified_at: last_notified_at
                    .and_then(|value| DateTime::parse_from_rfc3339(&value).ok())
                    .map(|value| value.with_timezone(&Utc)),
                last_total_price,
            },
            None => NotificationState::default(),
        })
    })
}

pub fn upsert_notification_state(
    db: &DbState,
    last_notified_price: Option<f64>,
    last_notified_at: Option<DateTime<Utc>>,
    last_total_price: Option<f64>,
) -> AppResult<()> {
    db.with_conn(|conn| {
        conn.execute(
            "INSERT INTO notification_state(rule_id, last_notified_price, last_notified_at, last_total_price)
             VALUES (1, ?1, ?2, ?3)
             ON CONFLICT(rule_id) DO UPDATE SET
               last_notified_price = excluded.last_notified_price,
               last_notified_at = excluded.last_notified_at,
               last_total_price = excluded.last_total_price",
            params![
                last_notified_price,
                last_notified_at.map(|value| value.to_rfc3339()),
                last_total_price,
            ],
        )?;
        Ok(())
    })
}

pub fn insert_notification_log(
    db: &DbState,
    combined_total: f64,
    success: bool,
    message: &str,
) -> AppResult<()> {
    let now = Utc::now().to_rfc3339();
    db.with_conn(|conn| {
        conn.execute(
            "INSERT INTO notification_log(rule_id, sent_at, combined_total, success, message)
             VALUES (1, ?1, ?2, ?3, ?4)",
            params![now, combined_total, success as i32, message],
        )?;
        Ok(())
    })
}

fn validate_rule(input: &MonitorRuleInput) -> AppResult<()> {
    if input.name.trim().is_empty() {
        return Err(AppError::Validation("monitor name is required".into()));
    }
    if input.max_price <= 0.0 {
        return Err(AppError::Validation("max price must be greater than 0".into()));
    }
    if input.segments.is_empty() || input.segments.len() > 4 {
        return Err(AppError::Validation("segments must be between 1 and 4".into()));
    }

    let city_count = input.segments.len() + 1;
    if city_count < 2 || city_count > 5 {
        return Err(AppError::Validation("city count must be between 2 and 5".into()));
    }

    if input.trip_type == "round_trip" {
        if input.segments.len() != 1 {
            return Err(AppError::Validation("round trip requires exactly one outbound segment".into()));
        }
        if input.return_date.as_ref().is_none_or(|value| value.is_empty()) {
            return Err(AppError::Validation("return date is required for round trip".into()));
        }
    }

    for segment in &input.segments {
        if segment.from_city.trim().len() < 3 || segment.to_city.trim().len() < 3 {
            return Err(AppError::Validation("city codes must be at least 3 characters".into()));
        }
        if segment.from_date.len() != 10 {
            return Err(AppError::Validation("segment date must be YYYY-MM-DD".into()));
        }
    }

    Ok(())
}

fn map_optional<T>(result: Result<T, rusqlite::Error>) -> Result<Option<T>, rusqlite::Error> {
    match result {
        Ok(value) => Ok(Some(value)),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(err) => Err(err),
    }
}
