# Requirements: Election-Assistant Score Maximization (85.75% → #1)

**Created:** 2026-05-02  
**Updated:** 2026-05-02  
**Scope:** Deep — feature (cross-cutting improvements)  
**Project:** election-assistant (FastAPI/HTMX/Jinja2)  
**Deadline:** 2026-05-03 23:59 IST  
**Target:** Beat VotePath-AI's 97% score (currently rank 766/16918)

## Overview

Transform election-assistant from a stateless FastAPI demo into a production-grade application matching the quality bar set by VotePath-AI (#1 at 97%). Focus areas map directly to the AI scoring criteria: Code Quality, Security, Efficiency, Testing, Accessibility, and Google Services.

The architecture stays FastAPI + HTMX + Jinja2. We add: MongoDB for persistence, JWT-based authentication, Google Cloud Translate + NLP, a multi-tier AI fallback chain, CSRF protection, property-based test expansion, CI/CD, and fix all critical bugs.

## Current State Analysis

### What Works Well
- 14 test files with Hypothesis property-based tests
- Strong accessibility (skip links, ARIA, reduced motion, WCAG 2.5.8 touch targets)
- Security headers middleware, signed sessions, input sanitization
- Google Civic API integration, Gemini AI integration
- Clean Pydantic models, typed data structures
- HTMX for efficient partial updates
- Provider pattern (US + India country-specific)

### Critical Gaps (Must Fix)
| Gap | Criteria Impact | Severity |
|-----|-----------------|----------|
| Syntax error in `main.py:563` (`readiness_update` endpoint) | Code Quality | Critical |
| Exposed API keys in `.env` file | Security | Critical |
| No CSRF protection despite README claiming it exists | Security | Critical |
| `google-cloud-aiplatform` installed but never imported | Google Services | High |
| No Google Translate service | Google Services | High |
| No Google Cloud NLP service | Google Services | High |
| No authentication system | Code Quality, Security | High |
| No database (all state lost on restart) | Efficiency, Code Quality | High |
| `cachetools` dependency never used | Code Quality | Medium |
| No `conftest.py` — duplicated test fixtures | Testing | Medium |
| `rag_engine.py` dead code — never imported | Code Quality | Medium |
| No CI/CD pipeline | Code Quality | Medium |
| Bare `print()` for logging, no structured logging | Code Quality | Low |
| No response compression | Efficiency | Low |

## Required Changes

### 1. Fix Critical Bugs (P0 — Must Do First)

**1a. Syntax Error in `main.py:563`**  
The `readiness_update` endpoint has a corrupted multi-line statement mixing `country=data["country"]` with a malformed `genai.GenerativeModel` constructor. Must be fixed to a proper async call or removed.

**1b. Remove Exposed API Keys**  
The `.env` file contains what appear to be real Google API keys. Must:
- Remove `.env` from git (verify `.gitignore` has `.env`)
- Create `.env.example` with placeholder values
- If keys are real, they should be rotated externally (out of scope for this repo)

**1c. Add CSRF Protection**  
FastAPI has no built-in CSRF. Must implement:
- Double-submit cookie pattern or CSRF token in forms
- Middleware that validates CSRF tokens on all POST/PUT/DELETE requests
- Skip CSRF for API endpoints that use Bearer tokens (if auth is added)

### 2. Add Authentication System

**Scope:** JWT-based auth with session support. Keep it simple — no OAuth for now (adds Firebase dependency).

**What to add:**
- Password hashing with `bcrypt` or `passlib`
- JWT token generation (HS256, 7-day expiry)
- `/auth/register` endpoint (email + password)
- `/auth/login` endpoint
- `/auth/me` endpoint (returns current user)
- Dependency injection `get_current_user()` for protected routes
- User model stored in MongoDB
- Optional: Google OAuth via `google-auth` library (lower priority than core JWT)

**Routes that become protected:**
- `/readiness/update` — save readiness to user profile
- `/checklist/toggle/{item_id}` — persist checklist state
- `/chat` (POST) — save chat history per user
- `/quiz/submit` — save quiz results per user

**Routes that stay public:**
- `/`, `/healthz`, `/timeline`, `/wizard/*`, `/quiz` (GET), `/scenarios` (GET), `/map`, `/stats`, `/auth/*`

### 3. Add MongoDB for Persistence

**Scope:** Replace in-memory state with MongoDB for user data. Keep session-based flow for anonymous users; persist for authenticated users.

**Models needed:**
- `User` — email (unique), hashed_password, name, state, country, registration_status, voting_method, readiness_score, created_at, updated_at
- `ChatMessage` — user_id (ref), messages[] (role, content, timestamp), capped at 50
- `QuizResult` — user_id (ref), score, total, answers[], completed_at
- `Checklist` — user_id (ref), items[] (key, completed, completed_at)
- `QueryLog` — user_id, query, response, provider, endpoint, category, response_time_ms, cached (indexed on user_id + created_at)

**Connection:** Use `motor` (async MongoDB driver for Python) or synchronous `pymongo` with `run_in_executor`. Motor is preferred for FastAPI async compatibility.

### 4. Add Google Cloud Services

**4a. Google Cloud Translate**  
- Use `google-cloud-translate` Python SDK
- Support translation of AI responses into common languages (Hindi, Spanish, etc.)
- New endpoint: `/translate` (POST) — accepts text + target language, returns translated text
- Add language selector to UI (header or chat page)
- Graceful fallback if API key not configured

**4b. Google Cloud Natural Language API**  
- Use `google-cloud-language` Python SDK
- Run sentiment analysis on chat messages (non-blocking, fire-and-forget)
- Use for content classification of user queries
- Log sentiment results to QueryLog for analytics
- Graceful fallback if API key not configured

**4c. Wire Up Vertex AI Properly**  
The `google-cloud-aiplatform` dependency is installed but never used. Either:
- Use Vertex AI as the primary AI provider (calls `gemini-1.5-flash` through Vertex AI endpoint), OR
- Remove the dependency and document that direct Gemini API is used
- Recommended: Use Vertex AI as primary, direct Gemini as fallback (matches VotePath-AI's multi-provider pattern)

### 5. Implement AI Fallback Chain

**Current state:** Single provider (Gemini via `google-generativeai`). No fallback.

**Target chain:**
```
1. In-memory cache (MD5-keyed, 1-hour TTL) — expand to MongoDB-backed cache if auth+DB added
2. Vertex AI (primary) — via google-cloud-aiplatform
3. Direct Gemini API (fallback) — via google-generativeai  
4. Hardcoded responses (final fallback) — keyword-matched, US election content
```

**Requirements:**
- Provider cooldown tracking (skip failed providers for 60-300 seconds)
- Response time tracking per provider
- Cache hit/miss tracking for analytics
- All providers return structured JSON validated against Pydantic schemas
- Hardcoded fallback covers: registration, voting methods, deadlines, polling places, ID requirements, mail ballots

### 6. Improve Testing

**6a. Add `conftest.py`**  
Centralize test fixtures:
- `client` fixture (TestClient with test config)
- `mock_gemini` fixture (mock Gemini API responses)
- `mock_civic_api` fixture (mock Google Civic API)
- `mock_translate` fixture (mock Google Translate)
- `mock_nlp` fixture (mock Google Cloud NLP)

**6b. Expand Test Coverage**
- Auth flow tests (register, login, JWT verification, protected routes)
- CSRF validation tests
- Translation endpoint tests
- AI fallback chain tests (cache hit, primary fail, fallback success, all fail)
- MongoDB integration tests (use `mongomock` or `pytest-mongodb`)
- Property-based tests for new models

**6c. Add `pyproject.toml`**  
Configure pytest, coverage, and linting tool settings in one place.

### 7. Add CI/CD

**GitHub Actions workflow** (`.github/workflows/ci.yml`):
- Trigger on push and pull_request
- Steps:
  1. Check out code
  2. Set up Python 3.13
  3. Install dependencies from `requirements.txt`
  4. Run linting (if ruff/flake8 added)
  5. Run tests with coverage
  6. Upload coverage report
- Use environment variables for API keys (from GitHub secrets)

### 8. Code Quality Improvements

**8a. Structured Logging**  
Replace `print()` with `logging` module:
- Configure logger with level, format, handlers
- Log requests, errors, AI provider stats
- No stack traces in production error responses

**8b. Remove Dead Code**  
- `rag_engine.py` — delete or integrate
- `cachetools` — remove from requirements.txt if not used, or add LRU cache implementation
- Unused imports across modules

**8c. Add Type Hints to Route Handlers**  
- Return type annotations on all FastAPI routes
- Use `Annotated` for path/query parameters

**8d. Add `ruff` for Linting**  
- Install `ruff` as dev dependency
- Configure in `pyproject.toml`
- Run in CI pipeline

### 9. Performance Improvements

**9a. Response Compression**  
- Add `gzip` compression middleware (FastAPI supports via `starlette.middleware.gzip.GZipMiddleware`)
- Minimum size threshold: 500 bytes

**9b. Expand Caching**  
- Use `cachetools` for LRU caching of KB docs (currently re-read from disk on every query)
- Cache Google Civic API responses per ZIP code (5-minute TTL)
- Cache rendered timeline HTML per jurisdiction (session-scoped)

### 10. Accessibility Maintained

- All new pages must maintain existing WCAG 2.2 AAA standards
- New auth forms: proper labels, focus states, error messages
- Language selector: accessible dropdown with keyboard navigation
- No regression in existing accessibility features

## Non-Goals (Explicitly Deferred)

- **React/SPA frontend** — keep HTMX + Jinja2
- **Firebase Hosting / Functions** — keep Vercel deployment
- **Real-time features** (WebSockets, SSE)
- **Admin panel**
- **Multi-tenant / organization support**
- **Email notifications**
- **Mobile app**
- **OAuth with providers other than Google** (if Google OAuth is added at all)
- **Payment integration**

## Dependencies to Add

| Package | Purpose |
|---------|---------|
| `motor` | Async MongoDB driver |
| `bcrypt` or `passlib[bcrypt]` | Password hashing |
| `PyJWT` | JWT token generation/verification |
| `google-cloud-translate` | Translation service |
| `google-cloud-language` | NLP sentiment analysis |
| `ruff` | Linting (dev) |
| `mongomock` | MongoDB mocking for tests (dev) |

## Dependencies to Remove

| Package | Reason |
|---------|--------|
| `cachetools` | Either use it (LRU cache) or remove |
| `google-cloud-aiplatform` | Either wire it up or remove |

## Success Criteria

1. **All critical bugs fixed** — syntax errors, exposed keys, CSRF
2. **Auth system functional** — register, login, JWT verification, protected routes
3. **MongoDB integrated** — User, ChatMessage, QuizResult, Checklist, QueryLog models
4. **Google Services active** — Translate (22+ languages), NLP (sentiment), Vertex AI (primary AI)
5. **AI fallback chain works** — cache → Vertex AI → Gemini → hardcoded
6. **Tests pass** — all existing + new tests, coverage > 80%
7. **CI/CD green** — GitHub Actions workflow passes on push
8. **App starts and runs** — `uvicorn app.main:app` works with mock services (no real API keys required)
9. **No regression in accessibility** — all new pages meet existing standards
10. **Score improvement** — submission scores > 95% (target: beat 97%)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Time pressure (1 day deadline) | High | Prioritize P0/P1 items first; skip nice-to-haves if needed |
| MongoDB integration breaks existing stateless flow | High | Keep session-based flow as fallback for anonymous users; only persist for authenticated users |
| Google API keys not available for testing | Medium | Provide mock services; make all Google services optional via env vars |
| CSRF implementation breaks HTMX POST requests | Medium | Use double-submit cookie pattern compatible with HTMX's `hx-headers` |
| Too many changes increase regression risk | Medium | Fix critical bugs first, then add features incrementally; run tests after each change |

## Execution Priority

```
P0 (Fix first, before anything else):
  1. Fix syntax error in main.py:563
  2. Remove exposed API keys, add .env.example
  3. Add CSRF protection

P1 (Score-impacting features):
  4. Add Google Cloud Translate
  5. Add Google Cloud NLP
  6. Wire up Vertex AI properly OR remove dependency
  7. Add AI fallback chain

P2 (Production readiness):
  8. Add JWT authentication
  9. Add MongoDB persistence
  10. Add conftest.py + expand tests
  11. Add CI/CD pipeline

P3 (Polish):
  12. Structured logging
  13. Remove dead code
  14. Type hints on route handlers
  15. Response compression
  16. Expand caching with cachetools
```
