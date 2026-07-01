use chrono::{DateTime, Duration, Utc};

use crate::db::repository::NotificationState;

pub fn should_notify(state: &NotificationState, combined_total: f64, max_price: f64) -> bool {
    if combined_total > max_price {
        return false;
    }

    match state.last_notified_price {
        None => true,
        Some(last_notified) if combined_total + 0.009 < last_notified => true,
        Some(last_notified) if (combined_total - last_notified).abs() <= 0.009 => {
            !within_cooldown(state.last_notified_at)
        }
        Some(_) => false,
    }
}

fn within_cooldown(last_notified_at: Option<DateTime<Utc>>) -> bool {
    match last_notified_at {
        Some(value) => Utc::now().signed_duration_since(value) < Duration::hours(24),
        None => false,
    }
}
