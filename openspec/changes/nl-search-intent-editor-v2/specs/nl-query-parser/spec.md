## MODIFIED Requirements

### Requirement: Structured output schema

The parser MUST constrain LLM output to a documented JSON schema for `SearchIntent` fields: `origins`, `destinations`, optional `countries`, `date_start`, `date_end`, `min_stay_days`, `max_price`, `trip_modes`, `cabin`, `adults`, `children`.

#### Scenario: Missing dates default

- **WHEN** user says "国庆" without explicit ISO dates and reference date is known
- **THEN** parser fills `date_start` as the next future occurrence of October 1 and `date_end` as the next future occurrence of October 7 for the same year

#### Scenario: National day buffer window

- **WHEN** user says "国庆前后" without explicit ISO dates and reference date is known
- **THEN** parser fills `date_start` as the next future occurrence of September 28 and `date_end` as the next future occurrence of October 10 for the same year

#### Scenario: Past holiday window rolls forward

- **WHEN** reference date is after October 10 of the current year and user says "国庆" or "国庆前后"
- **THEN** parser uses the same month-day rules for the following calendar year

## ADDED Requirements

### Requirement: Future-aware holiday window resolution

The NL query parser SHALL resolve Chinese holiday keywords to future-valid ISO date ranges using deterministic code shared between LLM post-processing and rule-based fallback.

#### Scenario: 国庆 keyword takes precedence over 国庆前后

- **WHEN** user query contains both "国庆前后" and no narrower "国庆" substring conflict
- **THEN** parser applies the 09-28 to 10-10 window

- **WHEN** user query contains "国庆" but not "国庆前后"
- **THEN** parser applies the 10-01 to 10-07 window

#### Scenario: LLM prompt includes reference date

- **WHEN** LLM parsing is used
- **THEN** system prompt includes `today=YYYY-MM-DD` and documents the 国庆 / 国庆前后 windows above

### Requirement: Intent validate without LLM

The system SHALL expose deterministic validation of a `SearchIntent` object independent of natural language parsing.

#### Scenario: Validate edited intent

- **WHEN** client submits a complete `SearchIntent` to the validate endpoint
- **THEN** server returns `validation` with `valid`, warnings, errors, clarifications, and query count estimates without calling the LLM
