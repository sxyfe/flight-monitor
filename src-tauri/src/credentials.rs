const SERVICE: &str = "flight-monitor";
const API_KEY_ACCOUNT: &str = "rollinggo-api-key";
const WEBHOOK_ACCOUNT: &str = "feishu-webhook";

use crate::error::{AppError, AppResult};

pub fn save_api_key(key: &str) -> AppResult<()> {
    let entry = keyring::Entry::new(SERVICE, API_KEY_ACCOUNT)?;
    entry.set_password(key.trim())?;
    Ok(())
}

pub fn get_api_key() -> AppResult<Option<String>> {
    let entry = keyring::Entry::new(SERVICE, API_KEY_ACCOUNT)?;
    match entry.get_password() {
        Ok(value) if !value.is_empty() => Ok(Some(value)),
        Ok(_) => Ok(None),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(err) => Err(err.into()),
    }
}

pub fn delete_api_key() -> AppResult<()> {
    let entry = keyring::Entry::new(SERVICE, API_KEY_ACCOUNT)?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()),
        Err(err) => Err(err.into()),
    }
}

pub fn save_webhook_url(url: &str) -> AppResult<()> {
    let entry = keyring::Entry::new(SERVICE, WEBHOOK_ACCOUNT)?;
    entry.set_password(url.trim())?;
    Ok(())
}

pub fn get_webhook_url() -> AppResult<Option<String>> {
    let entry = keyring::Entry::new(SERVICE, WEBHOOK_ACCOUNT)?;
    match entry.get_password() {
        Ok(value) if !value.is_empty() => Ok(Some(value)),
        Ok(_) => Ok(None),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(err) => Err(err.into()),
    }
}

pub fn delete_webhook_url() -> AppResult<()> {
    let entry = keyring::Entry::new(SERVICE, WEBHOOK_ACCOUNT)?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()),
        Err(err) => Err(err.into()),
    }
}

pub fn require_api_key() -> AppResult<String> {
    get_api_key()?.ok_or_else(|| AppError::Auth("RollingGo API Key 未配置".into()))
}

pub fn require_webhook_url() -> AppResult<String> {
    get_webhook_url()?.ok_or_else(|| AppError::Auth("飞书 Webhook 未配置".into()))
}
