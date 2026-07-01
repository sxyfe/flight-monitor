## ADDED Requirements

### Requirement: Settings panel for dual API configuration

The web UI SHALL provide inputs for RollingGo base URL, RollingGo API key, LLM base URL, LLM model, and LLM API key, with buttons to test each connection and save configuration.

#### Scenario: Configure and test RollingGo

- **WHEN** user enters RollingGo URL and key and clicks test
- **THEN** UI shows success or error toast without displaying the full key after save

### Requirement: Natural language search input

The UI SHALL provide a multiline text area for natural language queries, a parse button, and mode selector (`smart` / `exhaustive`).

#### Scenario: Parse displays structured preview

- **WHEN** user clicks parse after entering a query
- **THEN** UI shows editable structured fields for origins, destinations, dates, budget, stay days, and trip modes

### Requirement: Search progress display

During search, the UI SHALL show a progress bar and query count using SSE or polling from the API.

#### Scenario: Exhaustive search shows progress

- **WHEN** exhaustive search is running
- **THEN** progress bar updates until completion or error

### Requirement: Results table with sorting and filtering

The UI SHALL render offers in a sortable table with columns: price, trip type, origin, destination(s), outbound date, return date, stay days, and flight summary. Filters MUST support max price, minimum stay days, origin, trip type, and country.

#### Scenario: Filter by round-trip only

- **WHEN** user unchecks open-jaw filter
- **THEN** table shows only offers with `trip_type: round_trip`

#### Scenario: Open-jaw visual distinction

- **WHEN** offer has `bookable: false`
- **THEN** row displays an "开口程·分段价" badge and disclaimer footer is visible

### Requirement: Multi-dimensional charts

The UI SHALL display chart tabs or sections for price distribution, stay days, destination, and trip type using aggregation data from the API.

#### Scenario: Price distribution chart

- **WHEN** search results include multiple offers
- **THEN** price bucket chart reflects `aggregations.by_price_bucket`

### Requirement: Recommendation cards

The UI SHALL highlight up to three recommendation cards: cheapest overall, longest stay within budget, and best round-trip (`bookable: true`).

#### Scenario: Cheapest recommendation

- **WHEN** aggregations include `recommendations.cheapest`
- **THEN** UI scrolls to or highlights the matching offer card at top of results

### Requirement: Responsive layout at 1080px content width

The dashboard layout SHALL be optimized for desktop widths ≥ 1024px with a filter sidebar and main content area per design wireframes.

#### Scenario: Desktop layout

- **WHEN** viewport width is at least 1024px
- **THEN** filter sidebar and results table are visible side by side
