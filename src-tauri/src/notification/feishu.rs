use crate::error::{AppError, AppResult};
use crate::rollinggo::types::{PollQuote, SegmentQuote};

pub async fn send_price_alert(webhook_url: &str, rule_name: &str, quote: &PollQuote, max_price: f64) -> AppResult<String> {
    let mut lines = vec![
        format!("✈️ 机票监控提醒 · {rule_name}"),
        format!(
            "含税总价：¥{:.0}（限价 ¥{:.0}）",
            quote.combined_total, max_price
        ),
        String::new(),
    ];

    for segment in &quote.segments {
        lines.push(format_segment(segment));
        lines.push(String::new());
    }

    lines.push("⚠️ 分段最低价相加，仅供参考，请以实际可订联票为准。".into());

    let text = lines.join("\n");
    post_text(webhook_url, &text).await?;
    Ok(text)
}

pub async fn send_test_message(webhook_url: &str) -> AppResult<()> {
    post_text(
        webhook_url,
        "Flight Monitor 测试消息：飞书 Webhook 已连接成功。",
    )
    .await
}

fn format_segment(segment: &SegmentQuote) -> String {
    let header = format!(
        "段{}  {}→{}  {}",
        segment.segment_order, segment.from_city, segment.to_city, segment.from_date
    );
    let flights = segment
        .flights
        .iter()
        .map(format_flight_line)
        .collect::<Vec<_>>()
        .join("\n");
    format!("{header}\n{flights}\n段价：¥{:.0}", segment.total_price)
}

fn format_flight_line(flight: &crate::rollinggo::types::FlightSegmentInfo) -> String {
    format!(
        "{}  {} → {}  {}-{}",
        flight.flight_number,
        flight.dep_airport,
        flight.arr_airport,
        format_time(&flight.dep_time),
        format_time(&flight.arr_time)
    )
}

fn format_time(value: &str) -> String {
    value
        .split('T')
        .nth(1)
        .map(|part| &part[..part.len().min(5)])
        .unwrap_or(value)
        .to_string()
}

async fn post_text(webhook_url: &str, text: &str) -> AppResult<()> {
    let client = reqwest::Client::new();
    let response = client
        .post(webhook_url)
        .json(&serde_json::json!({
            "msg_type": "text",
            "content": { "text": text }
        }))
        .send()
        .await?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(AppError::Network(format!(
            "飞书 Webhook 发送失败 ({status}): {body}"
        )));
    }

    let payload: serde_json::Value = response.json().await?;
    if payload.get("code").and_then(|value| value.as_i64()) != Some(0) {
        return Err(AppError::Network(format!(
            "飞书 Webhook 返回错误: {payload}"
        )));
    }

    Ok(())
}
