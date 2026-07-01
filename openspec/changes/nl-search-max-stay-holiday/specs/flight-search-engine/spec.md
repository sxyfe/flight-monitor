## ADDED Requirements

### Requirement: SearchIntent max stay field

The flight search engine SHALL accept an optional `max_stay_days` integer on `SearchIntent`. When null or omitted, no maximum stay constraint applies. When set, only outbound/return date pairs whose stay duration is less than or equal to `max_stay_days` SHALL be enumerated.

#### Scenario: Filter pairs by max stay

- **WHEN** `min_stay_days` is 3, `max_stay_days` is 10, and a candidate pair has stay duration 12 days
- **THEN** that pair is excluded from search queries

#### Scenario: Max stay omitted

- **WHEN** intent JSON omits `max_stay_days`
- **THEN** engine behavior matches pre-change logic (only minimum stay applies)

### Requirement: Validate min/max stay consistency

`validate_intent()` SHALL reject intents where both `min_stay_days` and `max_stay_days` are set and `min_stay_days > max_stay_days`.

#### Scenario: Min greater than max

- **WHEN** `min_stay_days` is 10 and `max_stay_days` is 7
- **THEN** validation returns `valid: false` with an error explaining the conflict

#### Scenario: No feasible pairs under both bounds

- **WHEN** date window cannot produce any pair satisfying both min and max stay
- **THEN** validation returns `valid: false` with an error mentioning both constraints
