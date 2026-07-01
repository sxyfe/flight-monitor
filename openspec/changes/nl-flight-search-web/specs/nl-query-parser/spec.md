## ADDED Requirements

### Requirement: Natural language to SearchIntent

The NL query parser SHALL accept a Chinese natural language string and produce a `SearchIntent` JSON object via an OpenAI-compatible chat completion API using the configured LLM base URL, model, and API key.

#### Scenario: Parse multi-city Southeast Asia trip

- **WHEN** user submits "京津出发，国庆去泰国和菲律宾，至少玩7天，2500以内，可以开口程"
- **THEN** parser returns origins including BJS and TSN, destinations including Thai and Philippine city codes, `min_stay_days: 7`, `max_price: 2500`, and `trip_modes` containing both `round_trip` and `open_jaw`

### Requirement: Structured output schema

The parser MUST constrain LLM output to a documented JSON schema for `SearchIntent` fields: `origins`, `destinations`, optional `countries`, `date_start`, `date_end`, `min_stay_days`, `max_price`, `trip_modes`, `cabin`, `adults`, `children`.

#### Scenario: Missing dates default

- **WHEN** user says "国庆" without explicit ISO dates and current context year is known
- **THEN** parser fills `date_start` and `date_end` per documented holiday window defaults or leaves them null with a clarification request

### Requirement: Post-parse rule validation

After LLM parsing, the system SHALL run deterministic validation (not LLM) and return `validation` with `valid`, `warnings`, `errors`, and `clarifications` arrays.

#### Scenario: Clarification required

- **WHEN** parser cannot resolve whether user allows only round-trip or open-jaw
- **THEN** `clarifications` contains a question and `valid` is false until user confirms

#### Scenario: Warning for unrealistic budget

- **WHEN** intent includes Japan destinations and `max_price` is 2500
- **THEN** `warnings` includes a message that Japan routes likely exceed budget based on prior search data

### Requirement: Editable intent preview

The parse API response MUST include the full `intent` object so the UI can display and allow manual edits before search.

#### Scenario: User edits max price after parse

- **WHEN** user changes `max_price` in the UI and clicks search without re-parsing
- **THEN** search uses the edited intent values
