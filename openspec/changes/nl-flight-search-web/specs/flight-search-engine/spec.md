## ADDED Requirements

### Requirement: SearchIntent validation

The flight search engine SHALL validate a `SearchIntent` before executing any RollingGo API calls. Validation MUST check date range ordering, minimum stay feasibility within `date_end`, resolvable origin/destination city codes, positive `max_price` when provided, and `trip_modes` non-empty.

#### Scenario: Invalid stay window

- **WHEN** `date_start` is 2026-10-01 and `min_stay_days` is 7 and `date_end` is 2026-10-07
- **THEN** validation returns `valid: false` with an error explaining no return date satisfies minimum stay

#### Scenario: Valid intent

- **WHEN** origins, destinations, dates, and stay days form at least one feasible outbound/return pair
- **THEN** validation returns `valid: true` and includes `estimated_queries_smart` and `estimated_queries_exhaustive`

### Requirement: RollingGo flight search execution

The engine SHALL query RollingGo REST endpoints `/api/mcp/flightsearch` and `/api/mcp/airportsearch` using configured `base_url` and Bearer token. Round-trip searches MUST use `tripType=ROUND_TRIP`; open-jaw segments MUST use `tripType=ONE_WAY` and combine outbound and return minimum prices.

#### Scenario: Round-trip cheapest offer

- **WHEN** a round-trip query returns flights
- **THEN** the engine selects the routing with minimum `totalAdultPrice` and maps `fromSegments` and `retSegments` into a `FlightOffer` with `bookable: true`

#### Scenario: Open-jaw combined price

- **WHEN** open-jaw mode is enabled
- **THEN** the engine computes `price` as sum of cheapest one-way outbound and return segment prices and sets `bookable: false`

### Requirement: Smart and exhaustive query modes

The engine SHALL support `smart` mode with fewer API calls than `exhaustive` mode for the same intent. When estimated queries exceed 500 in exhaustive mode, the API layer MUST require `confirmed_high_cost: true` before execution.

#### Scenario: Smart mode reduces scope

- **WHEN** user intent lists countries but not every city in those countries
- **THEN** smart mode searches only cities explicitly listed or a documented default hot-city subset per country

#### Scenario: Exhaustive requires confirmation

- **WHEN** `estimate_query_count` returns greater than 500 and `confirmed_high_cost` is false
- **THEN** search MUST NOT start and returns a validation error

### Requirement: Search progress reporting

The engine SHALL invoke an `on_progress(done, total)` callback during multi-query execution so the API layer can emit SSE progress events.

#### Scenario: Progress increments

- **WHEN** each RollingGo query completes
- **THEN** `done` increments by 1 until `done === total`

### Requirement: Result aggregation

The engine SHALL produce aggregations for price buckets, stay days, destination, origin, trip type, and recommendations (`cheapest`, `longest_stay`, `best_round_trip`) from the offer list.

#### Scenario: Price bucket aggregation

- **WHEN** search completes with multiple offers
- **THEN** aggregations include `by_price_bucket` with 100 CNY-wide buckets covering the result price range
