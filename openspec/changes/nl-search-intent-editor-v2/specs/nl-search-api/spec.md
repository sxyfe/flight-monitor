## ADDED Requirements

### Requirement: Airport search endpoint

The API SHALL expose `GET /api/airport/search?q={keyword}` that proxies RollingGo airport search and returns normalized airport/city candidates for UI autocomplete.

#### Scenario: Search by Chinese city name

- **WHEN** client requests `/api/airport/search?q=北京` with RollingGo configured
- **THEN** response includes at least one item with `cityCode` and `cityName` fields

#### Scenario: Search without RollingGo configured

- **WHEN** RollingGo is not configured and client requests airport search
- **THEN** API returns HTTP 400 with a configuration error message

### Requirement: Intent validate endpoint

The API SHALL expose `POST /api/intent/validate` accepting `{ "intent": SearchIntent }` and returning `{ "validation": ValidationResult }` without invoking the LLM.

#### Scenario: Validate returns query estimates

- **WHEN** client posts a valid intent object to `/api/intent/validate`
- **THEN** response includes `estimated_queries_smart` and `estimated_queries_exhaustive`

#### Scenario: Validate returns errors for invalid intent

- **WHEN** client posts an intent with no resolvable origins or destinations/countries
- **THEN** response `validation.valid` is false and `errors` or `clarifications` is non-empty

## MODIFIED Requirements

### Requirement: Intent parse endpoint

The API SHALL expose `POST /api/intent/parse` accepting `{ "query": string, "locale": string }` and returning `{ "intent", "validation" }` per design.md. Parsed intents MUST apply future-aware 国庆 / 国庆前后 date windows when keywords are present.

#### Scenario: Parse applies 国庆前后 window

- **WHEN** client parses query containing "国庆前后" before October 10 of the current year
- **THEN** returned intent `date_start` is September 28 and `date_end` is October 10 of the applicable future year

#### Scenario: Parse without LLM configured

- **WHEN** LLM is not configured and client calls parse
- **THEN** API falls back to rule-based parsing and returns `{ "intent", "validation" }` with HTTP 200
