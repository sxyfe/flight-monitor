## MODIFIED Requirements

### Requirement: Settings panel for dual API configuration

The web UI SHALL provide inputs for RollingGo base URL, RollingGo API key, LLM base URL, LLM model, and LLM API key, with buttons to test each connection and save configuration.

#### Scenario: Configure and test RollingGo

- **WHEN** user enters RollingGo URL and key and clicks test
- **THEN** UI shows success or error toast without displaying the full key after save

#### Scenario: Toggle API key visibility

- **WHEN** user clicks the visibility toggle on a RollingGo or LLM API key field
- **THEN** the field switches between masked and plaintext display without submitting the form

### Requirement: Natural language search input

The UI SHALL provide a multiline text area for natural language queries and a parse button within a dedicated "自然语言查询" tab. Search mode selector (`smart` / `exhaustive`) MAY be shared below both tabs.

#### Scenario: Parse displays structured preview

- **WHEN** user clicks parse after entering a query in the natural language tab
- **THEN** UI switches to the "表单查询" tab and pre-fills the structured intent editor with parsed values

### Requirement: Editable intent preview

The parse API response MUST include the full `intent` object so the UI can display and allow manual edits before search. The user SHALL confirm edits via an explicit confirm action before search.

#### Scenario: User edits max price after parse

- **WHEN** user changes `max_price` in the form editor, clicks confirm, and then clicks search without re-parsing
- **THEN** search uses the confirmed intent values

#### Scenario: Confirm merges dirty form and JSON

- **WHEN** user clicks confirm and only the form is dirty
- **THEN** UI builds `SearchIntent` from the form, updates the JSON textarea, and refreshes validation estimates

#### Scenario: Confirm prefers dirty JSON

- **WHEN** user clicks confirm and only the JSON textarea is dirty with valid JSON
- **THEN** UI parses JSON into `SearchIntent`, updates form fields, and refreshes validation estimates

#### Scenario: Confirm blocked when both form and JSON are dirty

- **WHEN** user clicks confirm and both the form and JSON textarea have unsynchronized edits
- **THEN** UI shows an error message and does not update confirmed intent

## ADDED Requirements

### Requirement: Dual-mode query tabs

The web UI SHALL provide two top-level tabs: "自然语言查询" for NL input and parsing, and "表单查询" for structured intent editing. Users MUST be able to open the form tab directly without parsing.

#### Scenario: Direct form entry

- **WHEN** user opens the form tab without parsing
- **THEN** UI shows an empty or last-confirmed intent editor ready for manual input

#### Scenario: NL parse navigates to form

- **WHEN** natural language parse succeeds
- **THEN** UI activates the form tab and pre-fills all supported intent fields

### Requirement: Element Plus intent editor

The form tab SHALL use Vue 3 and Element Plus (CDN) for intent editing, including date range picker, country multi-select, trip-type checkboxes, and editable JSON textarea.

#### Scenario: Date range picker disables past dates

- **WHEN** user opens the date range picker in the form tab
- **THEN** dates before today are not selectable

#### Scenario: Trip type as independent checkboxes

- **WHEN** user toggles "往返联票" and "开口程" checkboxes
- **THEN** `trip_modes` reflects `round_trip` and/or `open_jaw` respectively, with at least one required before confirm

#### Scenario: Country multi-select

- **WHEN** user selects multiple countries from the fixed list (泰国, 菲律宾, 印度尼西亚, 马来西亚, 日本)
- **THEN** confirmed intent `countries` array matches the selection

### Requirement: Airport search picker for origins and destinations

The form tab SHALL provide airport search inputs for both origins and destinations. Users MUST be able to search by Chinese city or airport name, select a result, and add it as a removable tag showing IATA city code.

#### Scenario: Add origin by Chinese search

- **WHEN** user searches "北京", selects a result, and clicks add
- **THEN** origins tags include `BJS` (or the returned `cityCode`) and confirmed intent JSON lists the code in `origins`

#### Scenario: Add destination by Chinese search

- **WHEN** user searches "曼谷", selects a result, and clicks add
- **THEN** destinations tags include `BKK` and confirmed intent JSON lists the code in `destinations`

#### Scenario: Empty destinations uses countries

- **WHEN** user confirms intent with empty destinations but non-empty countries
- **THEN** search proceeds using engine country expansion per existing smart/exhaustive rules

### Requirement: Search gated on confirmed intent

The UI MUST disable or block "开始搜索" until the user has successfully clicked confirm and validation reports `valid: true`.

#### Scenario: Search blocked before confirm

- **WHEN** user edits the form but has not clicked confirm
- **THEN** search action does not send the draft form values
