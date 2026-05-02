# Development & Contributing Guide

*How to set up a local development environment, understand the codebase, and contribute to the Election Process Education Assistant.*

---

## Quick Start for Developers

### 1. Fork & Clone

```bash
# Fork on GitHub (click "Fork" button)
git clone https://github.com/YOUR_USERNAME/election-assistant.git
cd election-assistant

# Add upstream remote to stay synced
git remote add upstream https://github.com/[original-owner]/election-assistant.git
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Verify
which python  # Should show path inside venv/
```

### 3. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development tools (linting, testing, formatting)
pip install black flake8 mypy pytest pytest-cov pytest-asyncio

# Optionally: pre-commit hooks (auto-format on commit)
pip install pre-commit
pre-commit install
```

### 4. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Google API keys
nano .env
# (Or open in VS Code, paste your keys)

# Verify it's ignored
cat .gitignore | grep .env  # Should show ".env"
```

### 5. Run Locally

```bash
# Start FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# In another terminal, run tests
pytest tests/ -v

# Check code quality
black --check app/ tests/
flake8 app/ tests/
mypy app/

# Generate coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html  # View in browser
```

---

## Project Structure Deep Dive

### `/app` — Core Application Logic

```
app/
├── main.py              # FastAPI app, route handlers, middleware
├── models.py            # Pydantic schemas (TimelineResult, AskWhyRequest, etc.)
├── timeline.py          # Deadline validation logic (multi-source consensus)
├── ask_why.py           # RAG engine + Vertex AI integration
├── providers/           # External service integrations
│   ├── civic.py         # Google Civic API wrapper
│   ├── vertex_ai.py     # Vertex AI Gemini wrapper
│   └── knowledge_base.py # KB search (embeddings, semantic search)
├── validators/          # Input validation & constraints
│   ├── states.py        # US state codes
│   ├── dates.py         # Election deadline validation
│   └── forms.py         # Wizard form validation
└── renderers/           # HTML/SVG generation
    ├── timeline.py      # Timeline SVG rendering
    └── helpers.py       # Template helpers
```

### `/templates` — Jinja2 Templates

```
templates/
├── base.html            # Master layout (CSS, nav, footer)
├── index.html           # Homepage (hero, wizard, Q&A)
├── timeline.html        # Timeline results view
├── wizard/
│   ├── step1.html       # Country selection
│   ├── step2.html       # State selection
│   ├── step3.html       # Registration status
│   └── step4.html       # Voting method
├── ask_why_partial.html # HTMX response template
└── errors/
    ├── 404.html         # Not found
    └── 405.html         # Method not allowed
```

### `/tests` — Test Suite

```
tests/
├── test_timeline.py     # Deadline validation tests (15 tests)
├── test_ask_why.py      # RAG + Vertex AI tests (12 tests)
├── test_models.py       # Pydantic model validation (8 tests)
├── test_integration.py  # E2E user flows (10 tests)
└── fixtures.py          # Shared test data & mocks
```

### `/config` — Configuration

```
config/
└── anchor_dates.json    # Ground-truth deadlines (manually maintained)
    # Example:
    # {
    #   "2026": {
    #     "US": {
    #       "CA": {
    #         "voter_registration_deadline": "2026-10-19",
    #         "election_day": "2026-11-03",
    #         ...
    #       }
    #     }
    #   }
    # }
```

### `/knowledge_base` — RAG Data

```
knowledge_base/
├── absentee_vs_inperson.md      # Mail vs in-person guide
├── moved_wrong_precinct.md      # Moving & re-registration
├── signature_verification.md    # Mail ballot signature process
└── us-eligibility-pollbooks.md  # ID requirements
# Each file: YAML frontmatter + plain-text body (~400-600 words)
```

---

## Key Concepts

### 1. Multi-Source Consensus Validation

**Problem**: LLMs hallucinate deadlines. A single API source is unreliable.

**Solution**: Require ≥2 independent sources before returning HIGH confidence.

```python
# app/timeline.py
def validate_deadline(milestone_id, state, sources):
    """
    sources = {
        "civic_api": {...},
        "anchor_dates": {...},
        "vip_feeds": {...}
    }
    """
    valid_sources = [s for s in sources.values() if s is not None]
    
    if len(valid_sources) < 2:
        return {"date": None, "confidence": "low", "warning": "..."}
    
    # Check if sources agree
    dates = [s.get("date") for s in valid_sources]
    if all(d == dates[0] for d in dates):
        confidence = "high"
    else:
        confidence = "medium"
    
    return {"date": dates[0], "confidence": confidence, "sources": len(valid_sources)}
```

### 2. Wizard State Management

**Problem**: 4-step form needs to preserve state across page reloads.

**Solution**: Encrypted server-side session.

```python
# app/main.py
@app.post("/wizard/step/{step_num}")
async def wizard_step(request: Request, step_num: int, form: WizardForm):
    # Validate current step
    if not validate_step(step_num, form):
        return templates.TemplateResponse(f"wizard/step{step_num}.html", {...})
    
    # Store in session (encrypted)
    request.session[f"step_{step_num}"] = form.dict()
    
    # Render next step (pre-filled with prior responses)
    if step_num < 4:
        return RedirectResponse(url=f"/wizard/step/{step_num + 1}")
    else:
        return await generate_timeline(request)
```

### 3. RAG (Retrieval-Augmented Generation)

**Problem**: LLMs can't be trusted to answer election questions without sources.

**Solution**: Retrieve relevant KB documents first; use them to ground the LLM response.

```python
# app/ask_why.py
async def ask_why(question: str, state: str, user_context: dict):
    # Step 1: Semantic search over KB
    kb_results = await search_knowledge_base(
        query=question,
        top_k=3,
        filters={"state": state}
    )
    
    # Step 2: If high-confidence KB result, return it
    if kb_results[0]["score"] > 0.85:
        return format_kb_answer(kb_results)
    
    # Step 3: Fallback to Vertex AI with KB context
    rag_context = "\n".join([r["content"] for r in kb_results])
    response = await vertex_ai_client.generate(
        messages=[
            {"role": "system", "content": CIVIC_SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{rag_context}\n\nQ: {question}"}
        ],
        temperature=0.3  # Low creativity
    )
    
    return response
```

### 4. HTMX for Dynamic Sidebar

**Problem**: Asking a question shouldn't reload the entire page.

**Solution**: HTMX sends POST request; server returns HTML fragment; JS inserts it.

```html
<!-- templates/timeline.html -->
<button class="chip" 
    hx-post="/ask-why"
    hx-target="#ask_response"
    hx-swap="innerHTML"
    hx-vals='{"question_id": "us_no_id_how_verified"}'>
  Do I need an ID?
</button>

<div id="ask_response">
  <!-- Response inserted here -->
</div>
```

```python
# app/main.py
@app.post("/ask-why")
async def ask_why_endpoint(request: Request, question_id: str = Form(...)):
    answer = await ask_why_logic(question_id, request.session)
    return templates.TemplateResponse(
        "ask_why_partial.html",
        {"request": request, "answer": answer}
    )
```

---

## Making Your First Contribution

### Pick a Task

Look for issues labeled:
- `good-first-issue` (beginner-friendly)
- `help-wanted` (open to community)
- `enhancement` (new features)
- `bug` (fixes)

### Create a Feature Branch

```bash
git fetch upstream
git checkout -b feat/improve-timeline

# Make your changes
# ...

git add app/timeline.py tests/test_timeline.py
git commit -m "feat: improve timeline validation confidence scoring"
```

### Write Tests

Every change should have tests:

```python
# tests/test_timeline.py
def test_timeline_validation_requires_two_sources():
    """High confidence requires ≥2 sources."""
    result = validate_deadline(
        milestone_id="registration",
        state="CA",
        sources={
            "civic_api": {"date": "2026-10-19"},
            "anchor_dates": None,
            "vip_feeds": None
        }
    )
    assert result["confidence"] == "low"
    assert "single source" in result["warning"]

def test_timeline_validation_with_agreement():
    """Sources agree → high confidence."""
    result = validate_deadline(
        milestone_id="registration",
        state="CA",
        sources={
            "civic_api": {"date": "2026-10-19"},
            "anchor_dates": {"date": "2026-10-19"},
            "vip_feeds": None
        }
    )
    assert result["confidence"] == "high"
    assert result["date"] == "2026-10-19"
```

### Run Quality Checks

```bash
# Format code
black app/ tests/

# Check for issues
flake8 app/ tests/
mypy app/

# Run tests
pytest tests/test_timeline.py -v

# Check coverage
pytest --cov=app --cov-report=term | grep -A5 "TOTAL"
```

### Submit Pull Request

```bash
git push origin feat/improve-timeline
# Go to GitHub and click "New Pull Request"
```

**PR Checklist**:
- [ ] Descriptive title (`feat:`, `fix:`, `docs:` prefix)
- [ ] Explain what & why (not just what)
- [ ] Link to related issue
- [ ] All tests passing
- [ ] New code has test coverage >85%
- [ ] No linting errors (black, flake8, mypy clean)
- [ ] Updated README if docs needed

---

## Code Style & Conventions

### Python (PEP 8)

```python
# ✅ Good
def validate_state_code(code: str) -> bool:
    """Check if code is valid US state abbreviation."""
    valid_states = {"CA", "NY", "TX", ...}
    return code.upper() in valid_states

# ❌ Bad
def vs(c):
    s={"CA","NY","TX",...}
    return c.upper() in s
```

### Naming

- **Functions**: `snake_case` (`fetch_civic_data`)
- **Classes**: `PascalCase` (`TimelineResult`)
- **Constants**: `UPPER_SNAKE_CASE` (`MAX_INPUT_LEN`)
- **Private**: `_leading_underscore` (`_validate_internal`)

### Type Hints

```python
# ✅ Always use type hints
def search_knowledge_base(
    query: str,
    state: str,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """Search KB for relevant documents."""
    ...

# ❌ Never omit types
def search_kb(query, state, top_k=3):
    ...
```

### Comments

```python
# ✅ Good: explains *why*
# We require ≥2 sources to avoid single-point-of-failure hallucinations
if agreement_count < 2:
    confidence = "low"

# ❌ Bad: explains *what* (code already says this)
# Set confidence to low
if agreement_count < 2:
    confidence = "low"
```

### Docstrings

```python
# ✅ Google style
def generate_timeline(state: str, voting_method: str) -> TimelineResult:
    """Generate personalized election timeline.
    
    Args:
        state: Two-letter US state code (e.g., "CA")
        voting_method: "in-person", "early", or "mail"
    
    Returns:
        TimelineResult with milestones and confidence scores.
    
    Raises:
        ValueError: If state code invalid or voting method unknown.
    """
    ...
```

---

## Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now logs include DEBUG level info
logger.debug(f"Fetching timeline for state={state}, method={voting_method}")
```

### Use Python Debugger

```python
import pdb

def tricky_function():
    data = fetch_data()
    pdb.set_trace()  # Debugger stops here
    # Type: `c` (continue), `s` (step), `n` (next), `p` (print)
    # Type: `pp data` (pretty-print), `h` (help)
    process(data)
```

### Check API Responses

```python
# Add to any HTTP request:
import json
response = await civic_api.fetch(...)
print(json.dumps(response.json(), indent=2))
```

### Run Single Test

```bash
# Run one test file
pytest tests/test_timeline.py -v

# Run one test function
pytest tests/test_timeline.py::test_consensus_validation -v

# Run with print output
pytest tests/test_timeline.py -v -s
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'app'`
**Solution**: Running from wrong directory. Must be in project root:
```bash
pwd  # Check current directory
# Should end with "election-assistant"
ls app/  # Should list files
```

### Issue: `.env` file not found / API key missing
**Solution**: Copy and configure:
```bash
cp .env.example .env
# Edit .env, add your keys
```

### Issue: Tests fail: `RuntimeError: Event loop closed`
**Solution**: Use `pytest-asyncio`. Already in requirements.txt:
```bash
pip install -r requirements.txt
```

### Issue: Port 8000 already in use
**Solution**: Kill existing process or use different port:
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill it
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

---

## Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://pydantic-settings.readthedocs.io/)
- [Jinja2 Docs](https://jinja.palletsprojects.com/)
- [pytest Docs](https://docs.pytest.org/)

### Google Services
- [Civic Information API](https://developers.google.com/civic-information)
- [Vertex AI Docs](https://cloud.google.com/vertex-ai/docs)
- [Cloud Run Docs](https://cloud.google.com/run/docs)

### Best Practices
- [PEP 8 Style Guide](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [WCAG 2.2 Accessibility](https://www.w3.org/WAI/WCAG22/quickref/)

---

## Getting Help

- **Questions?** Open an issue with label `question`
- **Found a bug?** Open an issue with label `bug` + detailed steps to reproduce
- **Want to discuss?** Start a GitHub Discussion
- **Need clarification?** Comment on the issue or related PR

---

**Welcome to the project! 🎉**

Let's build better civic tech together.
