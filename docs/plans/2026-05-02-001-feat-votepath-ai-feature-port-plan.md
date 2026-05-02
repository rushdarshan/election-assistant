---
title: "feat: Port VotePath-AI features as independent pages"
type: feat
status: active
date: 2026-05-02
origin: docs/brainstorms/votepath-ai-feature-port-requirements.md
---

# feat: Port VotePath-AI features as independent pages

## Overview

Port 5 features from VotePath-AI into election-assistant as independent standalone pages: Scenario Simulator (`/scenarios`), Smart Checklist (`/checklist`), AI Chat with History (`/chat`), Polling Place Finder (`/map`), and Server Analytics (`/stats`). All features work within the stateless session architecture (30-min TTL cookies) and follow existing FastAPI/HTMX/Jinja2 patterns.

---

## Problem Frame

The election-assistant currently provides a wizard → timeline → Ask-Why flow. It lacks interactive tools for exploring edge-case scenarios, tracking readiness with a checklist, having multi-turn conversations, finding polling places, and understanding usage patterns. VotePath-AI has all 5 of these capabilities but built for India elections with React/Express/MongoDB. The goal is to adapt them for US elections within the existing FastAPI/HTMX/Python stack, keeping the stateless constraint.

---

## Requirements Trace

- R1. 5 features accessible via separate routes, each independently functional
- R2. All user-facing state stored in session cookies (30-min TTL), no database
- R3. No new external dependencies beyond existing stack (except itsdangerous for signed cookies)
- R4. New pages maintain WCAG 2.2 AAA compliance
- R5. Code follows existing patterns: typed functions, Pydantic models, single-responsibility
- R6. Tests written for new logic
- R7. All VotePath-AI India-specific content US-ized
- R8. Server analytics are aggregate-only, no user-identifiable data

**Origin actors:** A1 (US voter — first-time, moved, accessibility-needs), A2 (server process — analytics counters)
**Origin flows:** F1 (scenario selection → AI solution), F2 (checklist toggle → score recalc), F3 (multi-turn chat with session history), F4 (address lookup → polling place), F5 (view aggregate stats)

---

## Scope Boundaries

- No user accounts or authentication
- No persistent storage (database)
- No cross-session data retention
- No multi-language translation UI
- No admin panel
- Polling map: data display + Google Maps link, not a full interactive map (e.g., no Leaflet.js)
- Analytics: in-memory counters only, reset on server restart
- Chat: session-scoped history (lost on session expiry), no sentiment analysis (VotePath-AI feature not needed)

---

## Context & Research

### Relevant Code and Patterns

- **Routes**: All in `app/main.py` (476 lines). Pattern: `@app.get/post("/path")` → `templates.TemplateResponse(...)`.
- **Session**: No SessionMiddleware currently active. Wizard state passed through form fields. `app/wizard.py` exists (in-memory dict store, 30-min TTL) but is not wired into routes.
- **HTMX**: Loaded in `templates/base.html` v1.9.10. Pattern: `/ask-why/partial` endpoint returns HTML fragment via `TemplateResponse`. Minimal actual HTMX attribute usage in templates.
- **AI integration**: `app/ask_why.py` — Gemini 1.5 Flash with system prompt restrictions, JSON schema validation via `app/security.py` `validate_llm_output()`, KB retrieval fallback.
- **Readiness**: `app/readiness.py` — `calculate_readiness_score()` already exists, returns `ReadinessScore` with breakdown, next_steps, color helpers.
- **Models**: `app/models.py` — Pydantic models for all data contracts.
- **Templates**: All extend `templates/base.html` which contains nav, CSS tokens, HTMX script, dark mode toggle. Nav items: Home, Journey →, Quiz ✓, Readiness 📊.
- **Providers**: `app/providers/us_provider.py` — Google Civic API client with `get_timeline_data()`.
- **Testing**: `tests/` — pytest + pytest-asyncio + Hypothesis property-based tests. 4 test files, ~20 tests. No route/integration tests yet. `TestClient(app)` pattern available.
- **Sanitization**: `sanitize()` in `main.py` — strips HTML, enforces max length, `html.escape()`.

### Institutional Learnings

- Multi-source consensus for deadlines (critical architecture pattern) — do not hallucinate election data.
- HTMX partial-template pattern: return `TemplateResponse("partial.html", {...})` for dynamic updates, not JSON.
- WCAG 2.2 AAA is non-negotiable: 7:1+ contrast, 44px+ touch targets, semantic HTML, ARIA labels, skip links, prefers-reduced-motion.
- Stateless architecture: no database, session cookies only, analytics are in-memory.
- >85% test coverage required. External APIs mocked in tests.

### External References

- Starlette SessionMiddleware (used by FastAPI): signed cookies via itsdangerous. Requires `itsdangerous` package.
- Google Civic API `voterInfo` endpoint: provides polling locations by address.

---

## Key Technical Decisions

- **Session middleware**: Add Starlette `SessionMiddleware` with `itsdangerous` for signed cookies. This is the foundation for chat history and checklist state. 30-min TTL via `max_age=1800`. Secret from `SESSION_SECRET` env var. This decision replaces the current form-passing pattern for new features while not breaking existing wizard routes.
- **All routes in main.py**: Follow the existing pattern of defining routes in `app/main.py` rather than splitting into route modules. The file is already 476 lines; adding ~200 more for 5 features is acceptable. Refactor to modular routes can be a follow-up.
- **Analytics in-memory**: Module-level dict counters in a new `app/analytics.py`. Incremented at key points (chat messages sent, scenarios viewed, map lookups, checklist toggles). Simple counter dict, no threading concerns for Cloud Run (single worker per instance).
- **No heavy JS for map**: Polling place finder displays location data as structured text with a Google Maps directions link. No Leaflet.js or map embedding. Keeps the JS bundle minimal (consistent with project's HTMX-first philosophy).
- **Chat: 20-message history**: Store last 20 messages in session dict. Truncates oldest when exceeded. Matches VotePath-AI's pattern of carrying recent conversation context.

---

## Open Questions

### Resolved During Planning

- **Session storage mechanism**: Use Starlette SessionMiddleware (signed cookies) rather than the existing unused `app/wizard.py` in-memory dict. Reason: signed cookies are truly stateless (work across Cloud Run instances), while in-memory dicts break on horizontal scaling.
- **Navigation**: Add nav links for `/scenarios`, `/checklist`, `/chat`, `/map`, `/stats` to `templates/base.html`. 5 new links is acceptable given the project is expanding into a tool suite.
- **Chat endpoint style**: `/chat` returns full page on GET. POST sends message, HTMX appends response. Session stores history. Follows the `/ask-why/partial` HTMX pattern already in the codebase.
- **Analytics visibility**: `/stats` is public-facing (no auth needed). Shows aggregate counters only — no user-identifiable data, per R8.

### Deferred to Implementation

- Exact session secret configuration in production (Cloud Run env var setup)
- Final scenario prompt text and scenario list (should cover the 8 listed in requirements doc, but exact wording can be tuned during implementation)
- Exact analytics counter names and categories (implementation will define based on actual feature usage points)

---

## Output Structure

    election-assistant/
    ├── app/
    │   ├── main.py                    # Modify: add 5 new routes
    │   ├── models.py                  # Modify: add ScenarioResult, ChatMessage, AnalyticsStats models
    │   ├── scenarios.py               # Create: scenario prompt templates + AI solution generator
    │   ├── analytics.py               # Create: in-memory counters + stats aggregation
    │   ├── security.py                # Unchanged
    │   ├── ask_why.py                 # Unchanged (chat reuses same patterns)
    │   ├── readiness.py               # Unchanged (checklist reuses calculate_readiness_score)
    │   └── providers/
    │       └── us_provider.py         # Unchanged (map reuses existing Civic API pattern)
    ├── templates/
    │   ├── base.html                  # Modify: add 5 nav links
    │   ├── scenarios.html             # Create: scenario grid + solution display
    │   ├── checklist.html             # Create: interactive checklist + readiness score
    │   ├── chat.html                  # Create: chat interface with message history
    │   ├── map.html                   # Create: polling place search + results
    │   └── stats.html                 # Create: aggregate analytics display
    ├── tests/
    │   ├── test_scenarios.py          # Create
    │   ├── test_checklist.py          # Create
    │   ├── test_chat.py               # Create
    │   ├── test_map.py                # Create
    │   ├── test_analytics.py          # Create
    │   └── test_integration_new_features.py  # Create: E2E flows for new pages
    └── requirements.txt               # Modify: add itsdangerous

---

## Implementation Units

- U1. **Session Middleware + Analytics Infrastructure**

**Goal:** Add Starlette SessionMiddleware for signed cookie sessions and create the in-memory analytics counter module. This is the foundation that chat and checklist depend on.

**Requirements:** R2, R3, R8

**Dependencies:** None

**Files:**
- Modify: `app/main.py` (add SessionMiddleware, SESSION_SECRET env var)
- Create: `app/analytics.py` (in-memory counter module)
- Modify: `requirements.txt` (add itsdangerous)
- Test: `tests/test_analytics.py`

**Approach:**
- Add `itsdangerous` to `requirements.txt`
- Wire up `SessionMiddleware` in `main.py` with `secret_key` from `SESSION_SECRET` env var, `max_age=1800`, `https_only=True`, `same_site="strict"`
- Create `app/analytics.py` with module-level counter dict and helper functions: `increment(counter_name, labels=None)`, `get_all_stats()`, `get_endpoint_stats()`. Counters tracked: `chat_messages_sent`, `scenarios_viewed`, `map_lookups`, `checklist_toggles`, `total_page_views`
- Add a simple middleware or decorator to increment `total_page_views` on each request
- Generate `SESSION_SECRET` via `secrets.token_hex(32)` for local dev; production uses env var

**Execution note:** Write analytics tests first — the module is pure logic (dict operations) and easy to test without HTTP.

**Patterns to follow:**
- `app/main.py` middleware pattern (existing error handlers show how middleware is added)
- Module-level singleton pattern (similar to how `app/wizard.py` uses `_session_store` dict)

**Test scenarios:**
- Happy path: increment counter, verify value increases by 1
- Happy path: get_all_stats returns dict with all counter keys, zero-initialized
- Happy path: increment with labels, verify labels are stored
- Edge case: concurrent increments from same process (no race issues in single-worker Cloud Run)
- Edge case: get_all_stats on fresh module returns all zeros
- Error path: increment with empty counter name (handle gracefully or raise)

**Verification:**
- Session cookie set on responses after middleware is added
- `app/analytics.py` counters increment correctly when called
- `itsdangerous` is in `requirements.txt` and importable

---

- U2. **Scenario Simulator**

**Goal:** Build `/scenarios` page with grid of scenario cards. User clicks a card → AI generates step-by-step solution displayed inline.

**Requirements:** R1, R4, R5, R6, R7

**Dependencies:** U1 (for analytics tracking — scenario_viewed counter)

**Files:**
- Create: `app/scenarios.py` (scenario definitions, prompt templates, `generate_scenario_solution()`)
- Modify: `app/main.py` (add GET/POST `/scenarios` and `/scenarios/partial` routes)
- Create: `templates/scenarios.html` (scenario grid + HTMX partial swap area)
- Create: `app/models.py` additions: `ScenarioResult` Pydantic model
- Test: `tests/test_scenarios.py`

**Approach:**
- Define 8 US-specific scenarios in `app/scenarios.py`: `lost_voter_id`, `moved_wrong_precinct`, `name_mismatch`, `missed_deadline`, `no_id_at_polling`, `lost_mail_ballot`, `provisional_ballot`, `accessibility_accommodations`
- Each scenario has: `id`, `title`, `description`, `icon` (emoji), `prompt_template`
- `generate_scenario_solution()` calls Gemini with structured prompt (adapted from VotePath-AI `promptService.js` scenario prompts, US-ized). Returns `ScenarioResult` with: `steps[]`, `documents_needed[]`, `estimated_time`, `official_links[]`
- Route: `GET /scenarios` renders grid of cards. `POST /scenarios/partial` accepts `scenario_id` via HTMX form, calls AI, returns solution HTML fragment
- Solution displayed in HTMX swap target with expandable steps, document list, timeline, and resource links
- Use `app/security.py` `validate_llm_output()` for JSON schema validation (same pattern as `app/ask_why.py`)
- Increment `scenarios_viewed` analytics counter on each generation

**Technical design:** *(directional guidance, not implementation specification)*

```
ScenarioResult model:
  scenario_id: str
  title: str
  description: str
  steps: List[{number: int, action: str, details: str, link: Optional[str]}]
  documents_needed: List[str]
  estimated_time: str
  official_links: List[{label: str, url: str}]
  next_action: str
```

**Patterns to follow:**
- `app/ask_why.py` for AI call pattern: system prompt → generate → `validate_llm_output()` → fallback
- `templates/ask_why_partial.html` for HTMX partial response pattern
- Design tokens from `templates/base.html` for card styling

**Test scenarios:**
- Happy path: generate_scenario_solution returns valid ScenarioResult with all fields populated for each of the 8 scenarios
- Happy path: /scenarios GET returns 200 with scenario grid HTML containing all 8 scenario titles
- Happy path: /scenarios/partial POST with valid scenario_id returns HTML fragment with steps and documents
- Edge case: /scenarios/partial POST with invalid scenario_id returns error message
- Error path: Gemini API failure → fallback response displayed with appropriate message
- Error path: validate_llm_output JSON validation failure → fallback ScenarioResult returned

**Verification:**
- All 8 scenarios visible on /scenarios page
- Clicking any scenario generates a solution with steps, documents, timeline, and links
- Solution contains only US-relevant content (no India/ECI references)
- Page passes Axe accessibility scan (contrast, ARIA, keyboard nav)

---

- U3. **Smart Checklist + Readiness Score**

**Goal:** Build `/checklist` page with interactive voter prep checklist. Toggling items recalculates readiness score using existing `app/readiness.py` logic.

**Requirements:** R1, R4, R5, R6

**Dependencies:** U1 (session middleware needed for checklist state persistence)

**Files:**
- Create: `templates/checklist.html` (checklist items + readiness score display)
- Modify: `app/main.py` (add GET `/checklist` and POST `/checklist/toggle` routes)
- Modify: `app/models.py` additions: `ChecklistState` Pydantic model for session storage
- Modify: `app/readiness.py` if needed (may need minor adjustments for checklist-driven progress)
- Test: `tests/test_checklist.py`

**Approach:**
- Define 10 checklist items (matching the 8–10 from requirements doc): registration verified, voting method chosen, timeline reviewed, polling place located, ID requirements checked, mail ballot requested (conditional), candidates/measures researched, transportation arranged, voter rights reviewed, readiness quiz taken
- `GET /checklist` renders page with checklist items (checkboxes) and readiness score display below
- Each checkbox toggle sends HTMX POST to `/checklist/toggle` with item id and checked state
- Route updates checklist state in session dict, reconstructs `ReadinessProgress` from session data, calls `calculate_readiness_score()`, returns updated score HTML fragment via HTMX swap
- Score displayed using existing `get_readiness_color()`, `get_readiness_emoji()`, `get_readiness_label()` helpers
- Checklist items stored in session as dict: `{item_id: bool, ...}`
- Increment `checklist_toggles` analytics counter on each toggle

**Patterns to follow:**
- `app/readiness.py` `calculate_readiness_score()` for score computation
- `templates/readiness/dashboard.html` for score display styling (reuse circular progress, color classes)
- HTMX partial pattern for score update (swap only score section, not whole page)

**Test scenarios:**
- Happy path: /checklist GET renders page with all 10 checklist items and initial score
- Happy path: toggling a checklist item updates session and recalculates score correctly
- Happy path: all items checked → readiness score reaches maximum, shows "Voting-Ready"
- Happy path: no items checked → readiness score at minimum, shows "Start Here"
- Edge case: session expires → checklist resets, page handles gracefully with zeroed state
- Edge case: rapid toggle requests (debounce handled by HTMX naturally)
- Integration: toggling items and then visiting /readiness shows consistent score

**Verification:**
- All 10 checklist items render with correct labels
- Toggling any item updates the readiness score in real-time via HTMX
- Score colors match the existing readiness color scale (green/yellow/orange/red)
- Next-step recommendations update based on unchecked items

---

- U4. **Polling Place Finder**

**Goal:** Build `/map` page where users enter address/ZIP and see their polling place with a Google Maps directions link.

**Requirements:** R1, R4, R5, R6, R7

**Dependencies:** None (standalone, but can reuse wizard state if user completed wizard)

**Files:**
- Create: `templates/map.html` (search form + results display)
- Modify: `app/main.py` (add GET `/map` and POST `/map/search` routes)
- Modify: `app/models.py` additions: `PollingPlaceResult` Pydantic model
- Test: `tests/test_map.py`

**Approach:**
- `GET /map` renders search form (address/ZIP input, pre-filled if wizard state available in session)
- `POST /map/search` accepts address/ZIP, calls Google Civic API `voterInfo` endpoint to get polling location
- Reuse or extend the existing `app/providers/us_provider.py` pattern for Civic API calls
- `PollingPlaceResult` model: `polling_place_name`, `address`, `hours`, `available_methods[]`, `google_maps_url`
- Results displayed as structured card with polling place details and "Get Directions" link to Google Maps
- Fallback: if API returns no data, show message with link to state's election website
- Increment `map_lookups` analytics counter on each successful lookup
- For testing: mock Google Civic API responses (no live calls)

**Patterns to follow:**
- `app/providers/us_provider.py` `get_timeline_data()` for Google Civic API call pattern
- `app/main.py` `/timeline` route for form handling + API call + template response pattern
- Design tokens from `templates/base.html` for result card styling

**Test scenarios:**
- Happy path: /map GET renders search form
- Happy path: /map/search POST with valid address returns polling place details
- Happy path: /map/search POST with pre-filled wizard data (state in session) returns correct results
- Happy path: Google Maps directions URL is correctly formatted
- Edge case: /map/search POST with empty address returns validation error
- Edge case: Google Civic API returns no data → fallback message with state election website link
- Error path: Google Civic API rate limited or down → graceful error message
- Error path: Invalid state code → error handling

**Verification:**
- Searching for an address displays polling place name, address, and hours
- "Get Directions" link opens Google Maps with the correct destination
- API errors display user-friendly fallback message
- Page is accessible (ARIA labels on form, keyboard navigation, contrast)

---

- U5. **AI Chat with Conversation History**

**Goal:** Build `/chat` page with multi-turn conversational interface. History stored in session (last 20 messages, 30-min window).

**Requirements:** R1, R2, R4, R5, R6

**Dependencies:** U1 (session middleware required for chat history storage)

**Files:**
- Modify: `app/ask_why.py` or create `app/chat.py` (multi-turn chat with history, prompt builder)
- Modify: `app/main.py` (add GET `/chat`, POST `/chat/send`, POST `/chat/partial` routes)
- Create: `templates/chat.html` (chat interface with message bubbles, input, HTMX swap)
- Modify: `app/models.py` additions: `ChatMessage`, `ChatSession` Pydantic models
- Test: `tests/test_chat.py`

**Approach:**
- `GET /chat` renders chat page. If session has chat history, displays it. Otherwise shows welcome message
- `POST /chat/partial` accepts user message via HTMX form, appends to session history (max 20 messages), calls Gemini with conversation context, returns response HTML fragment
- System prompt: reuse and adapt `app/ask_why.py` guardrails (KB-only when possible, refuse speculation, cite official sources, low temperature). Additionally, instruct model to personalize based on wizard session data (state, voting method) if available
- Chat history stored in session as list of `{role: "user"|"assistant", content: str, timestamp: str}` dicts
- Truncate to last 20 messages when limit exceeded
- Display warning when session is nearing expiry (e.g., last 5 minutes)
- Increment `chat_messages_sent` analytics counter on each message
- For testing: mock Gemini responses, verify session history management

**Technical design:** *(directional guidance, not implementation specification)*

```
ChatMessage model:
  role: str  # "user" or "assistant"
  content: str
  timestamp: str  # ISO

Prompt construction for Gemini:
  System: election educator guardrails + personalization context from session
  Messages: last 20 from session history + new user message
  Config: temperature=0.3, max_tokens=500, response_mime_type="text/plain"
```

**Patterns to follow:**
- `app/ask_why.py` for Gemini API call and guardrails
- `templates/base.html` HTMX infrastructure for partial swaps
- Chat bubble styling from existing design tokens (use `--civic-accent` for user, `--civic-light` for assistant)

**Test scenarios:**
- Happy path: /chat GET renders chat page with welcome message
- Happy path: /chat/partial POST with user message returns AI response HTML fragment
- Happy path: session stores message history, history grows with each message
- Happy path: history truncated to 20 messages when limit exceeded (oldest removed)
- Happy path: chat personalized with wizard session data (state, voting method) when available
- Edge case: session expires → history lost, chat resets with welcome message
- Edge case: empty message submission → rejected with validation error
- Error path: Gemini API failure → fallback error message displayed
- Error path: Gemini returns malformed response → fallback displayed

**Verification:**
- Sending a message displays both user message and AI response in chat bubbles
- Conversation history persists across HTMX requests within the session
- After 20+ messages, oldest messages are no longer visible
- Session expiry clears history and resets chat

---

- U6. **Server Analytics Dashboard**

**Goal:** Build `/stats` page showing aggregate, in-memory query statistics. Public-facing, no user-identifiable data.

**Requirements:** R1, R4, R8

**Dependencies:** U1 (analytics counter module), U2–U5 (counters incremented by other features)

**Files:**
- Create: `templates/stats.html` (stats dashboard with counters and simple charts)
- Modify: `app/main.py` (add GET `/stats` route)
- Test: `tests/test_analytics.py` (extend U1's test file)

**Approach:**
- `GET /stats` calls `app/analytics.get_all_stats()` and renders `templates/stats.html`
- Display: total page views, per-feature counters (chat messages, scenarios viewed, map lookups, checklist toggles), and per-endpoint response times if tracked
- Use simple HTML/CSS bar charts (CSS width percentages) — no JS charting library
- All data is aggregate; no user-level breakdowns
- Stats reset on server restart (documented on page)

**Patterns to follow:**
- `templates/readiness/dashboard.html` for dashboard layout patterns
- CSS-only bar charts using `--civic-accent` color and width percentages

**Test scenarios:**
- Happy path: /stats GET returns 200 with stats page HTML
- Happy path: page displays all counter names and their values
- Happy path: after incrementing counters, /stats shows updated values
- Edge case: fresh server (no requests) → all counters show 0

**Verification:**
- /stats page loads and displays all tracked metrics
- Counters reflect actual usage (incremented by other features)
- Page clearly states data is ephemeral and resets on server restart

---

- U7. **Navigation Integration + Accessibility Pass**

**Goal:** Add nav links for all 5 new pages to `templates/base.html` and run accessibility verification on all new templates.

**Requirements:** R1, R4

**Dependencies:** U2, U3, U4, U5, U6 (all pages must exist before linking to them)

**Files:**
- Modify: `templates/base.html` (add 5 nav links, update `active_nav` logic)
- Modify: all new templates (scenarios.html, checklist.html, chat.html, map.html, stats.html) — accessibility fixes identified during review

**Approach:**
- Add 5 nav links to `.nav-links` list in `templates/base.html`:
  - Scenarios (icon: 🎭), Checklist (📋), Chat (💬), Map (📍), Stats (📊)
- Each link uses `active_nav` matching pattern: `{% if active_nav == 'scenarios' %}aria-current="page"{% endif %}`
- Pass `active_nav` context in each new route's `TemplateResponse`
- Accessibility checklist: semantic HTML (`<main>`, `<section>`, `<nav>`), ARIA labels, skip links, 7:1+ contrast, 44px+ touch targets, `prefers-reduced-motion` compliance, keyboard navigation, heading hierarchy
- Ensure all HTMX swap targets have `aria-live="polite"` for screen reader announcements

**Test scenarios:**
- Happy path: all 5 nav links render correctly in base.html
- Happy path: active_nav highlighting works for each new page
- Accessibility: each new page has skip link, semantic HTML, ARIA labels, keyboard nav
- Accessibility: HTMX swap regions have aria-live for dynamic content

**Verification:**
- Nav bar shows all 9 links (Home, Journey, Quiz, Readiness, Scenarios, Checklist, Chat, Map, Stats)
- Clicking any nav link navigates to the correct page with active state highlighted
- Axe DevTools scan shows 0 violations on all new pages
- Keyboard-only navigation works across all new pages

---

## System-Wide Impact

- **Interaction graph:** New routes added to `app/main.py`. Nav links in `templates/base.html` affect every page (shared template). Session middleware affects all routes (adds session cookie to responses).
- **Error propagation:** AI features (scenarios, chat) reuse `app/security.py` `validate_llm_output()` for fallback handling — consistent error behavior across all AI endpoints.
- **State lifecycle risks:** Session data lost on expiry. All new features handle empty session gracefully (defaults/welcomes). No partial-write risks (session is atomically replaced).
- **API surface parity:** No existing APIs changed. New routes are additive. Existing wizard, quiz, readiness, ask-why routes unaffected.
- **Unchanged invariants:** Multi-source consensus for deadlines (timeline generation unchanged). LLM guardrails (ask_why.py unchanged). Stateless architecture (no database added).

---

## Risks & Dependencies

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SessionMiddleware secret not set in production | Low | High | `SESSION_SECRET` env var required; app fails fast with clear error if missing |
| Gemini API quota exhaustion affects scenarios + chat | Medium | Medium | Both features have fallback responses; existing `ask_why.py` fallback pattern reused |
| main.py grows too large (700+ lines) | Medium | Low | Acceptable for this scope; route modularization can be a follow-up refactor |
| HTMX chat append causes jank on slow connections | Low | Low | Add loading indicator (existing `.htmx-indicator` CSS class) |
| In-memory analytics reset on Cloud Run scale-down | High | Low | Expected behavior; page documents "data resets on server restart" |
| Nav becomes crowded with 9 links | Low | Low | Nav wraps on mobile (existing responsive CSS handles this) |

---

## Documentation / Operational Notes

- `SESSION_SECRET` must be set in Cloud Run environment variables (generate via `openssl rand -hex 32`)
- `requirements.txt` updated with `itsdangerous` — rebuild Docker image on deploy
- All 5 new features add to `requirements.txt` dependency count by 1 package (itsdangerous, already needed by Starlette SessionMiddleware)

---

## Sources & References

- **Origin document:** docs/brainstorms/votepath-ai-feature-port-requirements.md
- **VotePath-AI source:** C:\Users\rushd\Downloads\ele\VotePath-AI (scenario prompts, analytics service, chat patterns)
- Related code: `app/main.py`, `app/ask_why.py`, `app/readiness.py`, `app/models.py`, `app/security.py`, `app/providers/us_provider.py`, `templates/base.html`
- Related patterns: HTMX partial responses (`templates/ask_why_partial.html`), session management (`app/wizard.py` — unused but shows intent)
