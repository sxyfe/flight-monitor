## ADDED Requirements

### Requirement: Local configuration endpoints

The API server SHALL expose endpoints to save and test RollingGo and LLM credentials. Keys MUST NOT be returned in full from `GET /api/config/status`; only masked or boolean configured flags.

#### Scenario: Save configuration

- **WHEN** client posts valid RollingGo and LLM config to `POST /api/config`
- **THEN** server stores config in memory for the running process and returns `{ "ok": true }`

#### Scenario: Test RollingGo connection

- **WHEN** client calls `POST /api/config/test-rollinggo`
- **THEN** server calls airport search for BJS and returns success or error message

### Requirement: Intent parse endpoint

The API SHALL expose `POST /api/intent/parse` accepting `{ "query": string, "locale": string }` and returning `{ "intent", "validation" }` per design.md.

#### Scenario: Parse without LLM configured

- **WHEN** LLM is not configured and client calls parse
- **THEN** API returns HTTP 400 with message to configure LLM first

### Requirement: Search execution endpoint

The API SHALL expose `POST /api/search` accepting `intent`, `mode`, and `confirmed_high_cost`, returning `search_id`, `stats`, `offers`, and `aggregations` on completion for smart mode.

#### Scenario: Successful smart search

- **WHEN** valid intent and smart mode are submitted
- **THEN** response `status` is `completed` and `offers` is sorted by ascending `price`

#### Scenario: High-cost search blocked

- **WHEN** exhaustive mode estimated queries exceed 500 and `confirmed_high_cost` is false
- **THEN** API returns HTTP 400 with `code: "CONFIRMATION_REQUIRED"`

### Requirement: SSE progress stream

The API SHALL expose `GET /api/search/{id}/stream` emitting Server-Sent Events for `progress`, `completed`, and `error` during long searches.

#### Scenario: Stream progress events

- **WHEN** client connects to SSE during an exhaustive search
- **THEN** server emits at least one `progress` event before `completed`

### Requirement: CORS and bind address

The server SHALL bind to `127.0.0.1` by default and MUST NOT enable public `0.0.0.0` binding without explicit environment flag documented as unsafe for credentials.

#### Scenario: Default local-only

- **WHEN** server starts without `NL_SEARCH_HOST` override
- **THEN** it listens on `127.0.0.1:8765`
