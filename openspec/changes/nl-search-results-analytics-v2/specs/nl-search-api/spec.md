## ADDED Requirements

### Requirement: Search result metadata

Search completion responses (synchronous `POST /api/search` result and SSE `completed` event payload) SHALL include a `meta` object with `code_to_country`: a map from IATA city code to Chinese country name for destinations relevant to the search intent and returned offers.

#### Scenario: Completed SSE includes country mapping

- **WHEN** an exhaustive or smart search completes via SSE
- **THEN** the `completed` event JSON includes `meta.code_to_country` with entries for destination codes appearing in offers

#### Scenario: Synchronous search includes country mapping

- **WHEN** a smart search returns synchronously with offers
- **THEN** the response body includes `meta.code_to_country` alongside `offers` and `aggregations`

#### Scenario: Mapping covers offer destination codes

- **WHEN** an offer has `out_dest` "MNL" and `ret_dest` "BKK"
- **THEN** `meta.code_to_country` includes mappings for both codes when those cities are in the engine destination tables

#### Scenario: Non-breaking extension

- **WHEN** a client ignores the `meta` field
- **THEN** existing `offers` and `aggregations` consumption continues to work unchanged
