use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AirportInfo {
    pub airport_code: String,
    pub airport_name: String,
    pub city_code: String,
    pub city_name: String,
}

#[derive(Debug, Deserialize)]
pub struct AirportSearchResponse {
    pub message: String,
    #[serde(default)]
    pub air_port_information_list: Vec<AirportInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct FlightSegmentInfo {
    pub flight_number: String,
    pub dep_time: String,
    pub arr_time: String,
    pub dep_airport: String,
    pub arr_airport: String,
}

#[derive(Debug, Deserialize)]
pub struct FlightRouting {
    pub total_adult_price: f64,
    pub currency: String,
    #[serde(default)]
    pub from_segments: Vec<FlightSegmentInfo>,
    #[serde(default)]
    pub ret_segments: Vec<FlightSegmentInfo>,
}

#[derive(Debug, Deserialize)]
pub struct FlightSearchResponse {
    pub message: String,
    #[serde(default)]
    pub flight_information_list: Vec<FlightRouting>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SegmentQuote {
    pub segment_order: i32,
    pub from_city: String,
    pub to_city: String,
    pub from_date: String,
    pub total_price: f64,
    pub currency: String,
    pub flights: Vec<FlightSegmentInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PollQuote {
    pub combined_total: f64,
    pub currency: String,
    pub segments: Vec<SegmentQuote>,
}
