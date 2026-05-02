import re
import html
import time
import os
import secrets
from dotenv import load_dotenv
load_dotenv()  # Load .env before any env var lookups

from typing import Optional, List
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.analytics import increment, record_endpoint_time
from app.models import (
    TimelineResult, AskWhyRequest, Jurisdiction, RegistrationStatus,
    QuizSession, QuizAttempt, ReadinessProgress
)
from app.timeline import generate_timeline
from app.ask_why import ask_why
from app.quiz import get_quiz_questions, grade_quiz, get_quiz_recommendations
from app.readiness import calculate_readiness_score, get_readiness_color, get_readiness_emoji

app = FastAPI(title="Election Process Education Assistant")
templates = Jinja2Templates(directory="templates")

# ── Session Middleware (signed cookies, 30-min TTL) ──
_session_secret = os.getenv("SESSION_SECRET")
if not _session_secret:
    _session_secret = secrets.token_hex(32)  # Auto-generated for local dev

app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    max_age=1800,  # 30 minutes
    https_only=True,
    same_site="strict",
)

# ── Analytics import (moved to top) ──

# ── Feature Routers ──
from app import chat, checklist, map as map_module, stats

app.include_router(chat.router)
app.include_router(checklist.router)
app.include_router(map_module.router)
app.include_router(stats.router)

@app.middleware("http")
async def stats_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Only track API and page routes, not static/assets if they existed
    stats.stats_data["total_queries"] += 1
    endpoint = request.url.path
    stats.stats_data["endpoints"][endpoint] += 1
    stats.stats_data["response_times"][endpoint].append(process_time)
    
    return response



# ── Input Sanitization (XSS Prevention — Bug #18) ──
_MAX_INPUT_LEN = 50  # No state/zip ever exceeds this

def sanitize(value: str, max_len: int = _MAX_INPUT_LEN) -> str:
    """Strip HTML tags, enforce max length, escape special chars."""
    if not value:
        return ""
    # Remove any HTML tags
    cleaned = re.sub(r'<[^>]*>', '', value)
    # Enforce max length before escaping (Bug #23 / Pre-Mortem #2)
    cleaned = cleaned[:max_len].strip()
    # HTML-escape remaining special chars
    cleaned = html.escape(cleaned, quote=True)
    return cleaned


# ── Custom Error Handlers (Bug #19, #26) ──
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request=request, name="errors/404.html", context= {
        "request": request, "active_nav": ""
    }, status_code=404)

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request=request, name="errors/405.html", context= {
        "request": request, "active_nav": ""
    }, status_code=405)

@app.exception_handler(StarletteHTTPException)
async def generic_http_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(request=request, name="errors/404.html", context= {
            "request": request, "active_nav": ""
        }, status_code=404)
    if exc.status_code == 405:
        return templates.TemplateResponse(request=request, name="errors/405.html", context= {
            "request": request, "active_nav": ""
        }, status_code=405)
    # Fallback for other HTTP errors
    return templates.TemplateResponse(request=request, name="errors/404.html", context= {
        "request": request, "active_nav": ""
    }, status_code=exc.status_code)


# ── Health ──
@app.get("/healthz", response_class=JSONResponse)
async def healthz():
    return {"status": "ok", "version": "1.0.0"}


# ── Landing ──
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context= {"request": request, "active_nav": "home"})


# ── Quick-Start Timeline (POST from homepage form) ──
@app.post("/timeline", response_class=HTMLResponse)
async def get_timeline(
    request: Request,
    country: str = Form(...),
    state: str = Form(...),
    registration_status: str = Form(...),
    voting_method: str = Form(...),
    moved_recently: bool = Form(False),
    voting_elsewhere: bool = Form(False),
    zip_code: Optional[str] = Form(None)
):
    # Sanitize all user inputs
    safe_country = sanitize(country, 5)
    safe_state = sanitize(state, 30)
    safe_zip = sanitize(zip_code or "", 10)
    safe_reg = sanitize(registration_status, 20)
    safe_method = sanitize(voting_method, 30)

    timeline = await generate_timeline(
        country=safe_country,
        state=safe_state,
        registration_status=safe_reg,
        voting_method=safe_method,
        moved_recently=moved_recently,
        voting_elsewhere=voting_elsewhere,
        zip_code=safe_zip or None
    )
    return templates.TemplateResponse(request=request, name="timeline.html", context= {
        "request": request,
        "timeline": timeline.model_dump(),
        "active_nav": "wizard"
    })


# ── Ask-Why (JSON API for JS fetch) ──
@app.post("/ask-why", response_class=JSONResponse)
async def ask_why_endpoint(req: AskWhyRequest):
    response = await ask_why(
        country=req.country,
        state=req.state,
        topic_id=req.topic_id,
        timeline_context=req.timeline_context
    )
    return response.model_dump()


# ── Ask-Why (HTMX partial for wizard flow) ──
@app.post("/ask-why/partial", response_class=HTMLResponse)
async def ask_why_partial(
    request: Request,
    topic_id: str = Form(...),
    country: str = Form("US"),
    state: str = Form("")
):
    timeline_data = TimelineResult(
        jurisdiction=Jurisdiction(country=country, state=state),
        milestones=[],
        checklist=[],
        official_links=[],
        source_notes=[]
    )
    try:
        result = await ask_why(
            country=country,
            state=state,
            topic_id=topic_id,
            timeline_context=timeline_data
        )
        return templates.TemplateResponse(request=request, name="ask_why_partial.html", context= {
            "request": request,
            "result": result,
            "topic_id": topic_id
        })
    except Exception:
        return HTMLResponse("<p style='color:var(--civic-danger)'>Error loading explanation. Please try again.</p>")


# ──────────────────────────────────
# Wizard Flow (4 Steps)
# ──────────────────────────────────

@app.get("/wizard", response_class=HTMLResponse)
async def wizard_landing(request: Request):
    return templates.TemplateResponse(request=request, name="wizard/step1.html", context= {
        "request": request, "step": 1, "total_steps": 4, "active_nav": "wizard"
    })


@app.get("/wizard/step/1", response_class=HTMLResponse)
async def wizard_step1(request: Request):
    return templates.TemplateResponse(request=request, name="wizard/step1.html", context= {
        "request": request, "step": 1, "total_steps": 4, "active_nav": "wizard"
    })


@app.post("/wizard/step/1", response_class=HTMLResponse)
async def wizard_step1_post(request: Request, country: str = Form(...)):
    safe_country = sanitize(country, 5)
    return templates.TemplateResponse(request=request, name="wizard/step2.html", context= {
        "request": request, "step": 2, "total_steps": 4,
        "country": safe_country, "active_nav": "wizard"
    })


@app.post("/wizard/step/2", response_class=HTMLResponse)
async def wizard_step2_post(
    request: Request,
    state: str = Form(...),
    country: str = Form("US"),
    zip_code: Optional[str] = Form(None)
):
    safe_state = sanitize(state, 30)
    safe_country = sanitize(country, 5)
    safe_zip = sanitize(zip_code or "", 10)
    return templates.TemplateResponse(request=request, name="wizard/step3.html", context= {
        "request": request, "step": 3, "total_steps": 4,
        "country": safe_country, "state": safe_state, "zip_code": safe_zip,
        "active_nav": "wizard"
    })


@app.post("/wizard/step/3", response_class=HTMLResponse)
async def wizard_step3_post(
    request: Request,
    registration_status: str = Form(...),
    country: str = Form("US"),
    state: str = Form(""),
    zip_code: str = Form("")
):
    safe_reg = sanitize(registration_status, 20)
    safe_country = sanitize(country, 5)
    safe_state = sanitize(state, 30)
    safe_zip = sanitize(zip_code, 10)

    show_moved = safe_reg in (RegistrationStatus.UNSURE.value, RegistrationStatus.NO.value)
    return templates.TemplateResponse(request=request, name="wizard/step4.html", context= {
        "request": request, "step": 4, "total_steps": 4,
        "country": safe_country, "state": safe_state, "zip_code": safe_zip,
        "registration_status": safe_reg,
        "show_moved_question": show_moved,
        "active_nav": "wizard"
    })


@app.post("/wizard/step/4", response_class=HTMLResponse)
async def wizard_step4_post(
    request: Request,
    voting_method: str = Form(...),
    moved_recently: bool = Form(False),
    voting_elsewhere: bool = Form(False),
    country: str = Form("US"),
    state: str = Form(""),
    registration_status: str = Form("yes"),
    zip_code: Optional[str] = Form(None)
):
    safe_country = sanitize(country, 5)
    safe_state = sanitize(state, 30)
    safe_zip = sanitize(zip_code or "", 10)
    safe_reg = sanitize(registration_status, 20)
    safe_method = sanitize(voting_method, 30)

    timeline_data = await generate_timeline(
        country=safe_country,
        state=safe_state,
        registration_status=safe_reg,
        voting_method=safe_method,
        moved_recently=moved_recently,
        voting_elsewhere=voting_elsewhere,
        zip_code=safe_zip or None
    )
    return templates.TemplateResponse(request=request, name="timeline.html", context= {
        "request": request,
        "timeline": timeline_data.model_dump(),
        "active_nav": "wizard"
    })


# ──────────────────────────────────
# Quiz & Readiness Features
# ──────────────────────────────────

@app.get("/quiz", response_class=HTMLResponse)
async def quiz_landing(request: Request):
    """Quiz selection page."""
    return templates.TemplateResponse(request=request, name="quiz/landing.html", context= {
        "request": request, "active_nav": "quiz"
    })


@app.post("/quiz/start", response_class=HTMLResponse)
async def quiz_start(
    request: Request,
    country: str = Form("US"),
    state: str = Form(""),
    category: str = Form(""),
    difficulty: str = Form("mixed"),
    count: int = Form(5)
):
    """Start a new quiz session."""
    safe_country = sanitize(country, 5)
    safe_state = sanitize(state, 30)
    safe_category = sanitize(category or "", 20)
    safe_difficulty = sanitize(difficulty, 10)
    
    questions = await get_quiz_questions(
        country=safe_country,
        state=safe_state or None,
        category=safe_category or None,
        difficulty=safe_difficulty,
        count=min(count, 10)  # Max 10 questions per quiz
    )
    
    if not questions:
        return templates.TemplateResponse(request=request, name="quiz/no_questions.html", context= {
            "request": request, "country": safe_country, "state": safe_state
        }, status_code=404)
    
    import json
    questions_json = json.dumps([q.model_dump() for q in questions])
    
    return templates.TemplateResponse(request=request, name="quiz/question.html", context= {
        "request": request,
        "country": safe_country,
        "state": safe_state,
        "category": safe_category,
        "difficulty": safe_difficulty,
        "current_question": questions[0],
        "current_index": 0,
        "total_questions": len(questions),
        "questions_json": questions_json,
        "active_nav": "quiz"
    })


@app.post("/quiz/submit", response_class=JSONResponse)
async def quiz_submit(req: Request):
    """Submit quiz answers and receive grading."""
    try:
        data = await req.json()
        
        # Parse attempts
        attempts = [QuizAttempt(
            question_id=q["id"],
            selected_idx=a,
            is_correct=False  # Will be set during grading
        ) for q, a in zip(data["questions"], data["answers"])]
        
        # Reconstruct questions for grading
        from app.quiz import QUIZ_BANK
        questions = []
        for q_data in data["questions"]:
            # Find in quiz bank
            for bank_questions in QUIZ_BANK.values():
                for q in bank_questions:
                    if q.id == q_data["id"]:
                        questions.append(q)
                        break
        
        result = await grade_quiz(
            session=QuizSession(
                country=data["country"],
                state=data.get("state", ""),
                question_count=len(questions)
            ),
            attempts=attempts,
            questions=questions
        )
        
        recommendations = await get_quiz_recommendations(result)
        
        # Format category breakdown with colors
        breakdown_with_colors = {}
        colors = {
            "registration": "#0891B2",
            "voting": "#059669",
            "deadline": "#D97706",
            "security": "#7C3AED",
            "civics": "#4F46E5"
        }
        
        for category, stats in result.category_breakdown.items():
            breakdown_with_colors[category] = {
                "correct": stats.get("correct", 0),
                "total": stats.get("total", 0),
                "percentage": stats.get("percentage", 0),
                "color": colors.get(category.lower(), "#2563EB")
            }
        
        # Determine result status
        score_color = "#22c55e" if result.percentage >= 70 else "#d97706" if result.percentage >= 50 else "#dc2626"
        score_emoji = "🟢" if result.percentage >= 70 else "🟡" if result.percentage >= 50 else "🔴"
        score_label = "Excellent!" if result.percentage >= 80 else "Good Work" if result.percentage >= 70 else "Keep Learning"
        
        return {
            "score": result.score,
            "total": result.total,
            "percentage": result.percentage,
            "passed": result.passed,
            "color_hex": score_color,
            "emoji": score_emoji,
            "label": score_label,
            "time_taken_seconds": data.get("time_taken_seconds", 0),
            "category_breakdown": breakdown_with_colors,
            "recommendations": recommendations
        }
    except Exception as e:
        return {"error": str(e)}, 400


# ──────────────────────────────────
# Scenario Simulator
# ──────────────────────────────────

from app.scenarios import SCENARIOS, generate_scenario_solution


@app.get("/scenarios", response_class=HTMLResponse)
async def scenarios_page(request: Request):
    """Scenario simulator landing page with grid of scenario cards."""
    start = time.time()
    increment("total_page_views")
    response = templates.TemplateResponse(request=request, name="scenarios.html", context= {
        "request": request,
        "scenarios": SCENARIOS,
        "active_nav": "scenarios"
    })
    record_endpoint_time("/scenarios", (time.time() - start) * 1000)
    return response


@app.post("/scenarios/partial", response_class=HTMLResponse)
async def scenario_partial(
    request: Request,
    scenario_id: str = Form(...)
):
    """Generate AI solution for a selected scenario (HTMX partial)."""
    start = time.time()
    increment("scenarios_viewed")

    # Get state from session if available
    session_state = request.session.get("wizard_state", {})
    state = session_state.get("state", "")

    result = await generate_scenario_solution(scenario_id, state or None)

    record_endpoint_time("/scenarios/partial", (time.time() - start) * 1000)
    return templates.TemplateResponse(request=request, name="scenarios_partial.html", context= {
        "request": request,
        "result": result.model_dump() if result else None
    })


@app.get("/quiz/results", response_class=HTMLResponse)
async def quiz_results(request: Request):
    """Display quiz results page."""
    # Note: Result data is passed via sessionStorage from frontend
    # This page displays the results template - actual data rendering happens client-side
    return templates.TemplateResponse(request=request, name="quiz/results.html", context= {
        "request": request,
        "active_nav": "quiz"
    })


@app.get("/readiness", response_class=HTMLResponse)
async def readiness_dashboard(
    request: Request,
    country: str = "US",
    state: str = ""
):
    """Show voter readiness dashboard."""
    safe_country = sanitize(country, 5)
    safe_state = sanitize(state, 30)
    
    # Reconstruct progress from session/forms (simplified - would use DB in production)
    progress = ReadinessProgress(
        country=safe_country,
        state=safe_state,
        registration_status=None,
        voting_method=None,
        timeline_viewed=False,
        questions_asked=0,
        quiz_attempts=0,
        quiz_best_score=None,
        checklist_items_completed=0,
        last_updated=datetime.now().isoformat()
    )
    
    readiness = await calculate_readiness_score(progress)
    color_class = get_readiness_color(readiness.overall_score)
    emoji = get_readiness_emoji(readiness.overall_score)
    
    return templates.TemplateResponse(request=request, name="readiness/dashboard.html", context= {
        "request": request,
        "readiness": readiness,
        "color_class": color_class,
        "emoji": emoji,
        "country": safe_country,
        "state": safe_state,
        "active_nav": "readiness"
    })


@app.post("/readiness/update", response_class=JSONResponse)
async def readiness_update(req: Request):
    """Update readiness progress (HTMX call)."""
    try:
        data = await req.json()
        
        progress = ReadinessProgress(
            country=data["country"],
            model = genai.GenerativeModel('gemini-pro',
            system_instruction="You are a non-partisan election assistant..."),
            state=data.get("state", ""),
            registration_status=data.get("registration_status"),
            voting_method=data.get("voting_method"),
            timeline_viewed=data.get("timeline_viewed", False),
            questions_asked=data.get("questions_asked", 0),
            quiz_attempts=data.get("quiz_attempts", 0),
            quiz_best_score=data.get("quiz_best_score"),
            checklist_items_completed=data.get("checklist_items_completed", 0),
            last_updated=datetime.now().isoformat()
        )
        
        readiness = await calculate_readiness_score(progress)
        color_class = get_readiness_color(readiness.overall_score)
        emoji = get_readiness_emoji(readiness.overall_score)
        
        return {
            "overall_score": readiness.overall_score,
            "registration_ready": readiness.registration_ready,
            "voting_ready": readiness.voting_ready,
            "knowledge_ready": readiness.knowledge_ready,
            "color_class": color_class,
            "emoji": emoji,
            "next_steps": readiness.next_steps,
            "completion_percentage": readiness.completion_percentage
        }
    except Exception as e:
        return {"error": str(e)}, 400

