## MODIFIED Requirements

### Requirement: Natural language search input

The UI SHALL provide a multiline text area for natural language queries and a parse button within the "自然语言查询" tab. After a successful parse, the UI MUST NOT modify or clear the textarea content. The UI SHALL still switch to the "表单查询" tab and pre-fill the intent editor.

#### Scenario: Parse preserves original query text

- **WHEN** user enters text in the natural language textarea and clicks parse successfully
- **THEN** the textarea still contains the original query text unchanged

#### Scenario: Parse still navigates to form tab

- **WHEN** natural language parse succeeds
- **THEN** UI activates the form tab and pre-fills structured intent fields while preserving NL textarea content

#### Scenario: User can review original query after parse

- **WHEN** user switches back to the natural language tab after a successful parse
- **THEN** the previously entered query text is still visible in the textarea

### Requirement: Results table with sorting and filtering

The UI SHALL render offers in a table with columns for price, trip type, origin, route, outbound date, return date, stay days, bookability, and flight summary. Table data MUST be driven by the shared results filter state (not independent filter controls).

#### Scenario: Table respects shared country filter

- **WHEN** user selects one or more countries in the shared filter bar
- **THEN** the table shows only offers whose outbound or return destination maps to a selected country

#### Scenario: Table respects shared city filter

- **WHEN** user selects one or more cities in the shared filter bar
- **THEN** the table shows only offers where origin, outbound destination, or return destination matches any selected city

#### Scenario: Table respects shared date filters

- **WHEN** user selects outbound and/or return dates in the shared filter bar
- **THEN** the table shows only offers matching all active date selections

### Requirement: Multi-dimensional charts

The UI SHALL display chart sections for price distribution, stay days, destination, and trip type. Charts MUST re-aggregate from filtered offers (not static server aggregations after filtering). All charts MUST show Chinese flight detail on hover.

#### Scenario: Charts update when shared filter changes

- **WHEN** user changes any shared filter while viewing the charts tab
- **THEN** all charts re-render to reflect only filtered offers

#### Scenario: Price bucket chart hover shows flight detail

- **WHEN** user hovers a bar in the price distribution chart
- **THEN** tooltip shows up to 5 matching offers with Chinese city names, outbound/return dates, price, and flight segment summary

#### Scenario: Destination chart hover shows flight detail

- **WHEN** user hovers a bar in the destination minimum-price chart
- **THEN** tooltip shows matching offers for that destination with Chinese labels and dates

#### Scenario: Hover truncates large result sets

- **WHEN** a chart dimension matches more than 5 offers
- **THEN** tooltip shows 5 offers and a line indicating how many additional offers match

## ADDED Requirements

### Requirement: Shared results filter bar

The results section SHALL provide a shared filter bar above the three result tabs with multi-select, searchable controls for country, city, outbound date, and return date, plus trip type and max price. Filter option lists MUST be derived only from the current search result offers (and `meta.code_to_country` for countries).

#### Scenario: Filter options scoped to current results

- **WHEN** search completes with offers for Thailand and Philippines only
- **THEN** country filter options include only countries present in those offers

#### Scenario: City filter matches any leg

- **WHEN** user selects city "马尼拉" in the shared city filter
- **THEN** offers are kept if Manila appears as origin, outbound destination, or return destination

#### Scenario: Multi-select country filter

- **WHEN** user selects "泰国" and "菲律宾" in the country filter
- **THEN** offers matching either country's destinations are shown (OR within country dimension; AND across active dimensions)

#### Scenario: Text search in city filter

- **WHEN** user types "曼谷" in the searchable city select
- **THEN** only cities from current offers matching the query are selectable

#### Scenario: Reset shared filters

- **WHEN** user clicks reset on the shared filter bar
- **THEN** all shared filters clear and three tabs show the full offer set

### Requirement: Price dimension analysis tab

The third result tab SHALL be labeled "价格维度分析" (replacing "航班分析" / "航变维度分析"). It SHALL present price comparisons by outbound date, return date, origin, and route using understandable Chinese titles. A date combination matrix SHALL use color intensity for lower prices and support hover detail.

#### Scenario: Tab renamed for clarity

- **WHEN** user views result tabs after search
- **THEN** the third tab label reads "价格维度分析" not "航班分析"

#### Scenario: Route chart uses Chinese city names

- **WHEN** user views the route minimum-price chart
- **THEN** route labels use Chinese format: round-trip `北京 ⇄ 曼谷`, open-jaw `天津 → 马尼拉 · 棉兰 → 天津`

#### Scenario: Date matrix hover shows offer detail

- **WHEN** user hovers a cell in the outbound×return date price matrix
- **THEN** tooltip or overlay shows Chinese route, dates, price, and flight summary for that cell's cheapest offer

#### Scenario: Price dimension tab respects shared filters

- **WHEN** user applies shared filters and opens the price dimension tab
- **THEN** all charts and the date matrix reflect only filtered offers

### Requirement: Chart hover flight detail

All result-area Chart.js instances (charts tab and price dimension tab) SHALL use a unified tooltip formatter displaying Chinese location names, outbound and return dates, total price, trip type, and flight segment summary from offer fields (`origin_name`, `out_dest_name`, `ret_dest_name`, `out_date`, `ret_date`, `detail` or segment summaries).

#### Scenario: Open-jaw hover shows both legs in Chinese

- **WHEN** user hovers a chart element matching an open-jaw offer
- **THEN** tooltip shows Chinese origin and both destination cities with segment price note if applicable

#### Scenario: Round-trip hover shows bookable indicator context

- **WHEN** user hovers a round-trip offer in a chart tooltip
- **THEN** tooltip includes route in Chinese and both segment summaries without implying open-jaw booking
