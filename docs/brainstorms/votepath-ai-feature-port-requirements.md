# Requirements: VotePath-AI Feature Port to Election-Assistant

**Created:** 2026-05-02  
**Scope:** Deep — feature  
**Project:** election-assistant (FastAPI/HTMX/US elections, stateless)  
**Source Project:** VotePath-AI (Express/React/MongoDB/India elections)

## Overview

Port/adapt 5 features from VotePath-AI into the election-assistant project as independent standalone pages, keeping the stateless session architecture. Each feature reuses existing infrastructure (wizard state, Google Civic API, Vertex AI, session management).

## Features

### 1. Scenario Simulator (`/scenarios`)

Interactive "what-if" explorer for voter edge cases. User picks a scenario; AI generates a step-by-step solution with official resources.

**Scenarios to include:**
- Lost voter ID card
- Moved to a new address / wrong precinct on election day
- Name mismatch on voter roll
- Missed registration deadline
- No acceptable ID at polling place
- Mail ballot not received / lost in transit
- Provisional ballot process
- Accessibility accommodations (curbside voting, disability access)

**UX:** Grid of scenario cards → click one → HTMX fetches AI-generated solution → displayed inline with expandable steps, documents needed list, timeline estimate, and official resource links.

**Backend:** New endpoint using Vertex AI Gemini with structured prompt templates (adapted from VotePath-AI `promptService.js` scenario prompts, US-ized). Reuses `app/ask_why.py` patterns for guardrails and citations.

**Session-scoped:** Solutions cached in session dict during the session lifetime.

---

### 2. Smart Checklist + Readiness Score (`/checklist`)

Interactive voter prep checklist with visual readiness score. Backend (`app/readiness.py`) already exists — this adds the frontend and checklist persistence.

**Checklist items (8–10):**
- Verified registration status
- Chosen voting method (in-person / early / mail)
- Reviewed personalized timeline
- Located polling place
- Checked ID requirements for state
- Requested mail ballot (if applicable)
- Researched candidates/measures on ballot
- Arranged transportation/time off work
- Reviewed voter rights and rules
- Taken readiness quiz

**UX:** Checklist rendered as interactive items (checkboxes via HTMX). Each toggle posts to session, recalculates readiness score, updates display. Readiness score shown as a visual gauge (uses `get_readiness_color()` and `get_readiness_emoji()` from `app/readiness.py`). Next-step recommendations displayed below the score.

**Backend:** New route handlers that manage checklist state in session. Calls `app/readiness.calculate_readiness_score()` on each update. No database needed — state lives in session cookie.

---

### 3. AI Chat with Conversation History (`/chat`)

Multi-turn conversational interface replacing/upgrading the single-question Ask-Why assistant. Maintains conversation history within the 30-minute session window.

**UX:** Chat-style interface (message bubbles, input field, send button). Conversation history scrolls. New messages appended via HTMX swap. Previous messages preserved in session.

**Backend:** New chat route that:
- Stores message history (last 20 messages) in session dict
- Passes conversation context to Vertex AI Gemini
- Reuses guardrails from `app/ask_why.py` (low temperature, official sources only, refuse speculation)
- Personalizes responses using wizard session data (state, registration status, voting method)

**Session constraints:** History lost on session expiry. Display a warning when session is near timeout.

---

### 4. Polling Place Finder (`/map`)

Map-based polling location finder using Google Civic API data already fetched during wizard flow.

**UX:** User enters address or ZIP code (pre-filled if wizard was completed). Results show:
- Polling place name and address
- Distance/directions link (Google Maps URL)
- Voting hours
- Available voting methods at that location
- Embedded map (iframe or Leaflet-style embed — lightweight, no heavy JS framework)

**Backend:** New endpoint calling Google Civic API `voterInfo` endpoint (reuses existing `app/providers/` patterns). Returns polling place data for rendering. If wizard already fetched civic data, reuse session-stored results.

**Fallback:** If API returns no data for the address, display a message directing the user to their state's election website with a direct link.

---

### 5. Server Analytics Dashboard (`/stats`)

Server-level (not user-level) query statistics, since the project is stateless. Shows aggregate usage patterns.

**Data tracked (in-memory, ephemeral):**
- Total queries served (lifetime of server process)
- Queries per endpoint (wizard steps, chat, scenarios, map lookups)
- Average response time per endpoint
- Top question topics (keyword-based categorization, adapted from VotePath-AI `analyticsService.js` `_categorizeQuery()`)
- AI provider usage (Vertex AI vs KB-only fallback ratio)

**UX:** Simple stats page with counters and bar charts. No user-identifiable data. Public-facing — anyone can view.

**Backend:** In-memory counters stored in a module-level dict or singleton. Incremented on each request via middleware or decorator. Reset on server restart.

---

## Out of Scope

- User accounts / authentication
- Persistent storage (database)
- Cross-session data retention
- Multi-language translation UI (VotePath-AI's translator)
- EVM/Voting machine demo (US-specific equivalent not needed)
- Real-time analytics or dashboards
- Admin panel

## Dependencies / Reuse

| Feature | Reuses From Existing Project |
|---------|------------------------------|
| Scenarios | `app/ask_why.py` patterns, Vertex AI provider, session wizard data |
| Checklist | `app/readiness.py` (full), session management |
| Chat | `app/ask_why.py` Vertex AI integration, session management |
| Map | `app/providers/` Google Civic API client, session wizard data |
| Analytics | Existing middleware patterns, response timing |

## Technical Constraints

- **Stateless:** All user-facing state stored in session cookies (30-min TTL)
- **No database:** Analytics are in-memory, ephemeral
- **FastAPI + HTMX:** Pages rendered server-side, interactions via HTMX swaps
- **Template system:** Jinja2 — all new pages follow existing `templates/` patterns
- **US elections only:** All VotePath-AI India-specific content must be US-ized
- **Accessibility:** Must maintain WCAG 2.2 AAA compliance (existing standard)

## Success Criteria

1. All 5 features accessible via separate routes
2. Features functional within a single session (no data loss during active session)
3. No new external dependencies beyond what's already in `requirements.txt` (or additions are minimal and well-justified)
4. New pages pass existing accessibility standards
5. Code follows existing patterns (typed functions, Pydantic models, single-responsibility modules)
6. Tests written for new logic (scenarios, checklist state management, chat history, map lookups)
