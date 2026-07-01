## ADDED Requirements

### Requirement: Matrix query tab

The UI SHALL provide a third query tab labeled「价格矩阵」with multi-select origins, multi-select destinations, outbound date range, return date range, optional min/max stay days, and a「开始矩阵搜索」button.

#### Scenario: Tab visible alongside NL and form

- **WHEN** user opens the main query page
- **THEN** three tabs are shown: 自然语言查询, 表单查询, 价格矩阵

### Requirement: Matrix date validation

Date inputs MUST use `min=today`. Valid date pairs require `ret > out` and stay within min/max stay bounds. Each axis span MUST NOT exceed 14 days. Empty valid pairs MUST block search with a Chinese error.

#### Scenario: Reject empty date pairs

- **WHEN** no `(out, ret)` pair satisfies constraints
- **THEN** validation returns an error and search does not start

### Requirement: Matrix pricing behavior

Matrix search SHALL query only ROUND_TRIP via RollingGo for each origin × destination × valid date pair. HTTP 200 with `success: false` SHALL count as pricing service failure per AGENTS.md.

#### Scenario: SSE streams matrix offers

- **WHEN** matrix search runs
- **THEN** SSE emits progress, offer events, and completed with matrix metadata

### Requirement: Matrix results overview

The matrix results page SHALL show: header with route count and axis legend; global green-to-red color scale with min/max price labels; two summary tables (lowest and highest per route); a responsive 3-column grid of route matrix cards with best-price highlight border; empty cells show「—」; cell hover shows Chinese route, dates, price, and flight summary.

#### Scenario: Best cell highlighted per route card

- **WHEN** a route matrix card renders
- **THEN** the cheapest priced cell in that card has a thicker border

### Requirement: Soft query limit warning

When estimated queries exceed the configured soft limit, the UI SHALL show a warning without blocking matrix search.

#### Scenario: Soft limit warning

- **WHEN** estimated matrix queries exceed soft_query_limit
- **THEN** a warning appears and search still proceeds on user action
