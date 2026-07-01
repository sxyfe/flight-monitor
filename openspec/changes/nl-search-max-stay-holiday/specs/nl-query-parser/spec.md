## ADDED Requirements

### Requirement: Parse max stay from natural language

The NL query parser SHALL extract `max_stay_days` from phrases such as 「最多玩 N 天」「不超过 N 天」「最多停留 N 天」. The LLM JSON schema and rule-based fallback MUST include the optional field.

#### Scenario: Rule parse max stay

- **WHEN** user query contains 「最多玩 10 天」
- **THEN** parsed intent includes `max_stay_days: 10`

#### Scenario: Coexist with min stay

- **WHEN** user query contains both 「至少玩 7 天」 and 「最多玩 14 天」
- **THEN** parsed intent includes `min_stay_days: 7` and `max_stay_days: 14`

## MODIFIED Requirements

### Requirement: SearchIntent JSON schema

The parser MUST constrain LLM output to a documented JSON schema for `SearchIntent` fields: `origins`, `destinations`, optional `countries`, `date_start`, `date_end`, `min_stay_days`, `max_stay_days`, `max_price`, `trip_modes`, `cabin`, `adults`, `children`.

#### Scenario: Schema documents max stay

- **WHEN** LLM returns intent JSON
- **THEN** `max_stay_days` is an optional integer or null in the validated schema
