use crate::db::repository::{MonitorRule, MonitorSegment};
use crate::error::{AppError, AppResult};
use crate::rollinggo::client::RollingGoClient;
use crate::rollinggo::types::{FlightRouting, PollQuote, SegmentQuote};

pub async fn quote_rule(client: &RollingGoClient, rule: &MonitorRule) -> AppResult<PollQuote> {
    if rule.trip_type == "round_trip" {
        quote_round_trip(client, rule).await
    } else {
        quote_segments(client, rule).await
    }
}

async fn quote_round_trip(client: &RollingGoClient, rule: &MonitorRule) -> AppResult<PollQuote> {
    let outbound = rule
        .segments
        .first()
        .ok_or_else(|| AppError::Validation("round trip segment missing".into()))?;
    let return_date = rule
        .return_date
        .clone()
        .ok_or_else(|| AppError::Validation("return date missing".into()))?;

    let response = client
        .search_flights(
            &outbound.from_city,
            &outbound.to_city,
            &outbound.from_date,
            Some(&return_date),
            "ROUND_TRIP",
            rule.adult_count,
            rule.child_count,
            &rule.cabin_grade,
        )
        .await?;

    let best = pick_cheapest(&response.flight_information_list)
        .ok_or_else(|| AppError::Validation("no round-trip flights found".into()))?;

    let mut flights = best.from_segments.clone();
    flights.extend(best.ret_segments.clone());

    Ok(PollQuote {
        combined_total: best.total_adult_price,
        currency: best.currency.clone(),
        segments: vec![SegmentQuote {
            segment_order: 1,
            from_city: outbound.from_city.clone(),
            to_city: outbound.to_city.clone(),
            from_date: outbound.from_date.clone(),
            total_price: best.total_adult_price,
            currency: best.currency.clone(),
            flights,
        }],
    })
}

async fn quote_segments(client: &RollingGoClient, rule: &MonitorRule) -> AppResult<PollQuote> {
    let mut quotes = Vec::new();
    let mut total = 0.0;
    let mut currency = "CNY".to_string();

    for segment in &rule.segments {
        let quote = quote_one_way_segment(client, rule, segment).await?;
        total += quote.total_price;
        currency = quote.currency.clone();
        quotes.push(quote);
    }

    Ok(PollQuote {
        combined_total: total,
        currency,
        segments: quotes,
    })
}

async fn quote_one_way_segment(
    client: &RollingGoClient,
    rule: &MonitorRule,
    segment: &MonitorSegment,
) -> AppResult<SegmentQuote> {
    let response = client
        .search_flights(
            &segment.from_city,
            &segment.to_city,
            &segment.from_date,
            None,
            "ONE_WAY",
            rule.adult_count,
            rule.child_count,
            &rule.cabin_grade,
        )
        .await?;

    let best = pick_cheapest(&response.flight_information_list)
        .ok_or_else(|| AppError::Validation(format!(
            "no flights found for {} -> {} on {}",
            segment.from_city, segment.to_city, segment.from_date
        )))?;

    Ok(SegmentQuote {
        segment_order: segment.segment_order,
        from_city: segment.from_city.clone(),
        to_city: segment.to_city.clone(),
        from_date: segment.from_date.clone(),
        total_price: best.total_adult_price,
        currency: best.currency.clone(),
        flights: best.from_segments.clone(),
    })
}

fn pick_cheapest(routings: &[FlightRouting]) -> Option<&FlightRouting> {
    routings
        .iter()
        .filter(|routing| routing.total_adult_price > 0.0)
        .min_by(|a, b| {
            a.total_adult_price
                .partial_cmp(&b.total_adult_price)
                .unwrap_or(std::cmp::Ordering::Equal)
        })
}
