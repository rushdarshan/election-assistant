# Election Process Education Assistant — Design Spec (Hybrid Wizard + Ask-Why)

Date: 2026-04-24

## 0) Summary
We will build a **Hybrid Election Process Education Assistant** optimized for clarity, safety, accessibility, and reviewer confidence:

- **Wizard Core (deterministic):** a short, structured flow that produces a personalized **timeline + checklist + official links**.
- **Ask-Why Sidebar (Vertex AI Gemini, RAG-only):** explains confusing concepts (ID verification, signature checks, moved/wrong precinct) using a strict response template with citations to a **whitelisted knowledge base**.

Deployment target: **Google Cloud Run**.

Jurisdictions:
- **United States:** timelines and links powered by **Google Civic Information API** (server-side) + caching.
- **India:** curated rules + official links (no scraping), via a pluggable provider.

This spec is designed to score well on:
**Instructions, Code Quality, Security, Efficiency, Testing, Accessibility, Google Services**.

## 1) Goals / Non-goals

### Goals
1. Make election participation steps **easy to follow** for first-time and returning voters.
2. Produce a **personalized timeline** with a clear “next best action” and official links.
3. Answer “why/how does this work?” questions safely (low hallucination risk).
4. Be auditable: the app must show **what sources** were used for guidance.
5. Ship an MVP that’s deployable on **Cloud Run** and can be reviewed quickly.

### Non-goals
- No partisan content, persuasion, candidate recommendations, or political advocacy.
- No storage of sensitive personal data (full address, DOB, ID numbers).
- No automated registration, ballot requests, or form submission.
- No “global coverage” promise—only US + India for MVP.

## 2) Primary user journeys

### Journey A — “I just want to know what to do next”
1. User selects **Country** and **State**.
2. Wizard asks registration status, preferred voting method, and whether user moved.
3. Output: timeline milestones + checklist + official links.

Success signal: user can state the **next step** in one sentence.

### Journey B — “I’m confused about the rules/security”
While viewing the timeline, user opens Ask-Why and selects a topic:
- “How do they verify I’m eligible without ID?”
- “How are signatures verified?”
- “Why can’t I vote in my old precinct after moving?”

Success signal: user receives a structured explanation + what varies + next steps, with citations.

### Journey C — “I moved / wrong precinct”
User indicates they moved.
Wizard branches to a guided checklist emphasizing:
- why precinct/jurisdiction matters,
- official office contact steps,
- provisional ballot pathway as “what if something goes wrong”.

## 3) UX / IA (Hybrid)

### Wizard pages (server-rendered + HTMX)
Order (minimal cognitive load):
1. Country
2. State (and ZIP for US only)
3. Registration status (Yes/No/Unsure)
4. Voting method (Election Day / Early / Mail)
5. Moved or changed name? (Yes/No)
6. Results: timeline + checklist + links + “Ask Why?”

### Ask-Why sidebar
- Locked until **Country + State** are known.
- Topic list uses user pain points:
  - Absentee vs in-person tradeoffs
  - “No ID” eligibility verification
  - Signature verification and mail ballot security
  - Moved / wrong precinct

Accessibility requirements:
- Sidebar must be keyboard-accessible (focus trap optional; never required).
- ARIA labels for disclosure controls.
- HTMX updates must preserve focus and announce changes with `aria-live` region.

## 4) System architecture (FastAPI monolith)

### Components
- **Web app:** FastAPI routes render Jinja templates (Wizard pages)
- **Timeline Engine:** pure functions that return `TimelineResult`
- **Jurisdiction Providers:**
  - `USProvider` (Google Civic Information API)
  - `IndiaProvider` (curated rules + official links)
- **Knowledge Base:** local, versioned markdown snippets used for RAG
- **AskWhy Service:** Vertex AI Gemini client + retrieval + strict output validation

### Key design principle
Separate **deterministic guidance** (wizard/timeline) from **explanations** (Ask-Why). The explanation module never invents deadlines; it can only explain concepts and point back to official sources.

## 5) Data model

### Wizard state
Minimal state persisted in signed session cookie:
- `country`: `US` | `IN`
- `state`: string (US: USPS abbreviation; IN: state/UT name)
- `zip`: string (US only; optional but recommended)
- `registration_status`: `yes|no|unsure`
- `voting_method`: `election_day|early|mail`
- `moved_recently`: boolean

No full street address. If ZIP is not provided, US timeline degrades gracefully to state-level links.

### TimelineResult (internal)
```json
{
  "jurisdiction": {"country":"US","state":"CA"},
  "milestones": [
    {"id":"register_by","label":"Register by","date":"2026-10-XX","confidence":"official"},
    {"id":"election_day","label":"Election Day","date":"2026-11-03","confidence":"official"}
  ],
  "checklist": [
    {"id":"check_registration","label":"Check registration status","link":"..."}
  ],
  "official_links": [
    {"label":"State election office","url":"..."}
  ],
  "source_notes": [
    {"source":"google_civic","details":"elections + voter info"}
  ]
}
```

### Knowledge base document format (RAG)
Each KB doc is a small markdown file with front matter:
```md
---
id: us-eligibility-pollbooks
country: US
topics: ["eligibility", "poll-books", "id"]
source_url: https://www.nass.org/can-I-vote
---
<curated excerpt + plain-language notes>
```

## 6) External integrations (Google Services)

### Google Civic Information API (US)
- Server-side only (API key in Secret Manager)
- Cache responses by `(state, zip)` with TTL.
- Fall back to NASS/USA.gov links when API is unavailable.

### Vertex AI Gemini (Ask-Why)
- Use Vertex AI with service account auth (Cloud Run workload identity / service account).
- RAG-only behavior:
  - retrieval from local KB (whitelist)
  - no browsing, no external fetching

## 7) Ask-Why: RAG + strict template (detailed)

### 7.1 Retrieval
Input to Ask-Why:
- `country`, `state`
- `topic_id` (enumerated)
- `timeline_context` (selected milestones + official links; no PII)

Retrieval steps:
1. Filter KB docs by `country` and `topic_id`.
2. Rank by simple heuristic:
   - exact topic match
   - state match where available
3. Return top 3–5 snippets (short; < 1,500 tokens total).

### 7.2 Output schema (must validate)
The model must output **only JSON** that validates this schema:

```json
{
  "topic_id": "string",
  "summary": "string",
  "explanation": ["string"],
  "what_varies": ["string"],
  "next_steps": [{"label":"string","url":"string"}],
  "if_something_goes_wrong": ["string"],
  "citations": [{"kb_id":"string","quote":"string"}],
  "disclaimer": "string"
}
```

Server behavior:
- Parse JSON strictly.
- Validate URLs (https only).
- If invalid: return a safe fallback message with official links only.

### 7.3 System prompt (exact)

**SYSTEM**

You are an election education assistant. Your job is to explain processes clearly and safely.

Hard rules:
1) You MUST answer using ONLY the provided Knowledge Base snippets and the provided `timeline_context`.
2) Do NOT invent deadlines, ID rules, or state-specific requirements. If not present in snippets/context, say it varies and direct the user to official links.
3) Output MUST be valid JSON matching the required schema. Output NOTHING else.
4) Provide citations: every key claim must be supported by at least one `citations[].quote` drawn from the KB snippets.
5) Be neutral and nonpartisan.
6) Do not request sensitive personal data.

Style rules:
- Use plain language.
- Keep `summary` under 30 words.
- Prefer bullet-like short sentences in arrays.

### 7.4 User prompt template (exact)

**USER**

Context:
- country: {{country}}
- state: {{state}}
- topic_id: {{topic_id}}
- timeline_context: {{timeline_context_json}}

Knowledge Base Snippets:
{{kb_snippets_with_ids}}

Task:
Return a JSON object matching the required schema. Include:
- explanation (3–6 items)
- what_varies (2–5 items)
- next_steps: link only to URLs that appear in `timeline_context` OR in KB snippet `source_url` fields.
- if_something_goes_wrong (2–4 items)
- disclaimer: always remind user to confirm with official election office.

### 7.5 Few-shot examples (2)

#### Example 1 — topic_id = "us_no_id_how_verified"
Input snippets include discussion of registration status checks, poll books, and official links.
Output (illustrative):
```json
{
  "topic_id": "us_no_id_how_verified",
  "summary": "Polling places typically check you against the voter roll, not just an ID card.",
  "explanation": [
    "Poll workers generally confirm you are on the voter registration list for that precinct.",
    "Some places confirm identity via signature or other record-based checks.",
    "Rules differ by state, so the best source is your state election office."
  ],
  "what_varies": [
    "Whether an ID is required and which forms are accepted.",
    "Whether signature matching is used and how it is handled."
  ],
  "next_steps": [
    {"label":"Check registration status","url":"{{from_timeline_context}}"},
    {"label":"State election office","url":"{{from_timeline_context_or_kb_source_url}}"}
  ],
  "if_something_goes_wrong": [
    "Ask the poll workers what options are available if you are not found on the roll.",
    "Contact your local election office as soon as possible for guidance."
  ],
  "citations": [
    {"kb_id":"us-can-i-vote-hub","quote":"...links directly to state election websites and trusted resources..."}
  ],
  "disclaimer": "Voting rules differ by state. Confirm details using your state/local election office links."
}
```

#### Example 2 — topic_id = "moved_wrong_precinct"
Output emphasizes jurisdiction differences and official contact steps.

## 8) Security & privacy

### Security controls
- Secrets in **Secret Manager** (Civic API key, Vertex config if needed)
- No client-side keys
- Strict input validation (country/state enums, zip regex)
- Content security: escape all template output; sanitize any model-provided strings before rendering

### Privacy stance
- Do not store full addresses or identifying details.
- Log only coarse telemetry (endpoint latency, provider errors), never user-entered ZIP alongside IP.

## 9) Performance / efficiency
- HTMX + SSR minimizes JS bundle size.
- Cache Civic API responses with TTL.
- Cache Ask-Why outputs per `(country,state,topic_id)` for short TTL to reduce cost.

## 10) Testing strategy

### Unit tests
- Timeline engine (pure function) returns stable results for fixtures.
- Provider adapters with mocked HTTP.
- Prompt builder produces stable prompts; schema validator rejects bad JSON.

### Integration tests
- Wizard flow: happy path + moved path.
- Ask-Why: uses canned KB snippets; validates JSON output and rendering.

### Golden fixtures
- Store small JSON fixtures for Civic API in repo (tiny, <1MB total).

## 11) Deployment on Cloud Run
- Container: Python FastAPI
- Config: env vars + Secret Manager
- Logging: structured logs (JSON)
- Health checks: `/healthz`

## 12) Repo size constraint (<10MB)
- No large datasets, no binaries
- KB docs: small curated markdown snippets
- Fixtures: minimal, compressed JSON

## 13) Open questions (explicit)
1. India provider: which official portal(s) should be the canonical link targets for each state/UT?
2. Minimum UX: do we require ZIP for US, or allow “state-only” mode for faster onboarding?

---

References (local research)
- `C:\Users\rushd\Downloads\ele\research\create-an-assistant-that-helps-users-understand-th.md`
