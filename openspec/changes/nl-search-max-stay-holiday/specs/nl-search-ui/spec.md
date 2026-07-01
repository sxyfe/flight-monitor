## ADDED Requirements

### Requirement: Max stay form field

The form tab SHALL expose a numeric input labeled 「最多停留（天）」 bound to `max_stay_days`. Empty input SHALL map to null (no maximum). It MUST appear alongside 「最少停留（天）」 and 「最高价格（元）」.

#### Scenario: User sets max stay

- **WHEN** user enters 10 in the max stay field and starts search
- **THEN** submitted intent includes `max_stay_days: 10`

#### Scenario: User clears max stay

- **WHEN** user clears the max stay field
- **THEN** intent omits max stay or sets it null and query string excludes max-stay phrasing

### Requirement: National Day core week read-only highlight

The date range area SHALL keep native `<input type="date">` controls unchanged. Below the inputs, a read-only reference mini-calendar MUST highlight the future-valid National Day core week (October 1–7) using warm Element-style tokens. The reference calendar MUST NOT capture pointer events for date selection.

#### Scenario: Core week cells highlighted

- **WHEN** form date section is visible and reference year is 2026
- **THEN** cells for 2026-10-01 through 2026-10-07 display distinct highlight styling

#### Scenario: Selected range overlay

- **WHEN** user selects a date range overlapping September or October
- **THEN** reference calendar also indicates selected range days within the displayed months

#### Scenario: Native inputs unchanged

- **WHEN** user interacts with date fields
- **THEN** behavior remains native dual date inputs (no popover calendar)

## MODIFIED Requirements

### Requirement: Query string sync includes stay bounds

Form changes SHALL auto-generate query strings that reflect both minimum and maximum stay when set.

#### Scenario: Query string with max stay

- **WHEN** form has `min_stay_days: 7` and `max_stay_days: 14`
- **THEN** generated query string includes phrasing for both constraints in Chinese
