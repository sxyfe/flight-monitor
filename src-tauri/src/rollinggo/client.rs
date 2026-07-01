use crate::error::{AppError, AppResult};
use crate::rollinggo::types::{AirportSearchResponse, FlightSearchResponse};

const DEFAULT_BASE_URL: &str = "https://mcp.rollinggo.cn";

pub struct RollingGoClient {
    http: reqwest::Client,
    base_url: String,
    api_key: String,
}

impl RollingGoClient {
    pub fn new(api_key: impl Into<String>) -> AppResult<Self> {
        let http = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(45))
            .build()?;
        Ok(Self {
            http,
            base_url: std::env::var("ROLLINGGO_API_BASE_URL")
                .unwrap_or_else(|_| DEFAULT_BASE_URL.to_string()),
            api_key: api_key.into(),
        })
    }

    pub async fn search_airports(&self, keyword: &str) -> AppResult<AirportSearchResponse> {
        self.post("/api/mcp/airportsearch", serde_json::json!({ "keyword": keyword }))
            .await
    }

    pub async fn search_flights(
        &self,
        from_city: &str,
        to_city: &str,
        from_date: &str,
        ret_date: Option<&str>,
        trip_type: &str,
        adult_number: i32,
        child_number: i32,
        cabin_grade: &str,
    ) -> AppResult<FlightSearchResponse> {
        let mut body = serde_json::json!({
            "adultNumber": adult_number,
            "childNumber": child_number,
            "cabinGrade": cabin_grade,
            "fromCity": from_city,
            "toCity": to_city,
            "fromDate": from_date,
            "tripType": trip_type,
        });
        if let Some(ret_date) = ret_date {
            body["retDate"] = serde_json::Value::String(ret_date.to_string());
        }
        self.post("/api/mcp/flightsearch", body).await
    }

    pub async fn validate_key(&self) -> AppResult<()> {
        self.search_airports("BJS").await?;
        Ok(())
    }

    async fn post<T: serde::de::DeserializeOwned>(
        &self,
        path: &str,
        body: serde_json::Value,
    ) -> AppResult<T> {
        let url = format!("{}{}", self.base_url.trim_end_matches('/'), path);
        let response = self
            .http
            .post(url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Accept-Language", "zh_CN")
            .json(&body)
            .send()
            .await?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err(AppError::Auth("RollingGo API Key 无效或已过期".into()));
        }

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            return Err(AppError::Network(format!(
                "RollingGo 请求失败 ({status}): {text}"
            )));
        }

        response.json::<T>().await.map_err(Into::into)
    }
}
