import re
import html
import time
import os
import logging
import secrets
import asyncio
from dotenv import load_dotenv
load_dotenv()

from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Structured Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from app.analytics import increment, record_endpoint_time
from app.models import (
    TimelineResult, AskWhyRequest, Jurisdiction, RegistrationStatus,
    QuizSession, QuizAttempt, ReadinessProgress
)
from app.timeline import generate_timeline
from app.ask_why import ask_why
from app.quiz import get_quiz_questions, grade_quiz, get_quiz_recommendations
from app.readiness import calculate_readiness_score, get_readiness_color, get_readiness_emoji
from app.scenarios import SCENARIOS, generate_scenario_solution

# ── MongoDB Integration ──
from app import db as mongo_db
from app.db import create_chat_message_doc, create_quiz_result_doc, create_checklist_doc
from app.querylog import QueryLogMiddleware

# ── AI Chain ──
from app.ai_chain import ai_chain

# ── Auth ──
from app import auth

# ── Feature Routers ──
from app import chat, checklist, map as map_module, stats
from app.translate_service import translation_service
from app.nlp_service import nlp_service


# ── Application Lifespan (Startup/Shutdown) ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Election Process Education Assistant v2.0.0")
    try:
        await mongo_db.connect_to_mongo()
        ai_chain.set_mongo_db(mongo_db.db)
        logger.info("MongoDB persistent cache enabled for AI chain")
    except Exception as e:
        logger.warning(f"MongoDB connection failed (running without persistent storage): {e}")
    yield
    # Shutdown
    await mongo_db.close_mongo()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Election Process Education Assistant",
    version="2.0.0",
    lifespan=lifespan,
)
templates = Jinja2Templates(directory="templates")

# ── Response Compression ──
app.add_middleware(GZipMiddleware, minimum_size=500)

# ── CSRF Middleware (before session so CSRF cookie is set on responses) ──
from app.csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

# ── 3-Tier Rate Limiter ──
# Tier 1: General endpoints (100 req/15min)
# Tier 2: Auth endpoints (20 req/15min)
# Tier 3: AI endpoints (30 req/15min)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Session Middleware (signed cookies, 30-min TTL) ──
_session_secret = os.getenv("SESSION_SECRET")
if not _session_secret:
    _session_secret = secrets.token_hex(32)

app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    max_age=1800,
    https_only=True,
    same_site="strict",
)

# ── Security Headers Middleware ──
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; style-src 'self' 'unsafe-inline' https:; font-src 'self' data: https:;"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ── QueryLog Middleware (logs all requests to MongoDB) ──
app.add_middleware(QueryLogMiddleware)

# ── Feature Routers ──
from app import chat, checklist, map as map_module, stats, auth

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(checklist.router)
app.include_router(map_module.router)
app.include_router(stats.router)

# ── Translation Router ──
from app.translate_service import translation_service

@app.post("/translate", response_class=JSONResponse)
async def translate_text(req: Request):
    """Translate text to a target language."""
    try:
        data = await req.json()
        text = data.get("text", "")
        target_language = data.get("target_language", "en")
        source_language = data.get("source_language", "en")

        if not text or target_language == source_language:
            return {"translated_text": text, "target_language": target_language}

        translated = translation_service.translate(text, target_language, source_language)
        return {
            "translated_text": translated,
            "target_language": target_language,
            "source_language": source_language,
            "service_available": translation_service.available,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/translate/languages", response_class=JSONResponse)
async def get_languages():
    """List supported translation languages."""
    return {"languages": translation_service.get_supported_languages()}


# ── NLP Endpoint (non-blocking sentiment analysis) ──
from app.nlp_service import nlp_service

@app.post("/nlp/analyze", response_class=JSONResponse)
async def analyze_nlp(req: Request):
    """Analyze text sentiment and extract entities."""
    try:
        data = await req.json()
        text = data.get("text", "")
        if not text:
            return {"sentiment": {"score": 0.0, "magnitude": 0.0, "label": "neutral"}, "entities": []}
        return nlp_service.analyze_query(text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.middleware("http")
async def stats_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    stats.stats_data["total_queries"] += 1
    endpoint = request.url.path
    stats.stats_data["endpoints"][endpoint] += 1
    stats.stats_data["response_times"][endpoint].append(process_time)

    return response


# ── Input Sanitization (XSS Prevention) ──
_MAX_INPUT_LEN = 50

def sanitize(value: str, max_len: int = _MAX_INPUT_LEN) -> str:
    """Strip HTML tags, enforce max length, escape special chars."""
    if not value:
        return ""
    cleaned = re.sub(r'<[^>]*>', '', value)
    cleaned = cleaned[:max_len].strip()
    cleaned = html.escape(cleaned, quote=True)
    return cleaned


# ── Custom Error Handlers ──
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request=request, name="errors/404.html", context={
        "request": request, "active_nav": ""
    }, status_code=404)

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request=request, name="errors/405.html", context={
        "request": request, "active_nav": ""
    }, status_code=405)

@app.exception_handler(StarletteHTTPException)
async def generic_http_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(request=request, name="errors/404.html", context={
            "request": request, "active_nav": ""
        }, status_code=404)
    if exc.status_code == 405:
        return templates.TemplateResponse(request=request, name="errors/405.html", context={
            "request": request, "active_nav": ""
        }, status_code=405)
    if exc.status_code == 403:
        return JSONResponse(
            status_code=403,
            content={"detail": exc.detail or "Forbidden"},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail or "Internal server error"},
    )


# ── Health ──
@app.get("/healthz", response_class=JSONResponse)
async def healthz():
    mongo_status = "connected" if mongo_db.db else "disconnected"
    return {
        "status": "ok",
        "version": "2.0.0",
        "services": {
            "translate": translation_service.available,
            "nlp": nlp_service.available,
            "mongodb": mongo_status,
        },
    }


# ── Landing ──
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request, "active_nav": "home"
    })


# ── Quick-Start Timeline ──
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
    return templates.TemplateResponse(request=request, name="timeline.html", context={
        "request": request,
        "timeline": timeline.model_dump(),
        "active_nav": "wizard"
    })


# ── Ask-Why (JSON API) ──
@app.post("/ask-why", response_class=JSONResponse)
@limiter.limit("30/15minutes")
async def ask_why_endpoint(request: Request, req: AskWhyRequest):
    response = await ask_why(
        country=req.country,
        state=req.state,
        topic_id=req.topic_id,
        timeline_context=req.timeline_context
    )
    return response.model_dump()


# ── Ask-Why (HTMX partial) ──
@app.post("/ask-why/partial", response_class=HTMLResponse)
@limiter.limit("30/15minutes")
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
        return templates.TemplateResponse(request=request, name="ask_why_partial.html", context={
            "request": request,
            "result": result,
            "topic_id": topic_id
        })
    except Exception:
        return HTMLResponse("<p style='color:var(--civic-danger)'>Error loading explanation. Please try again.</p>")


# ──────────────────────────────────
# Wizard Flow
# ──────────────────────────────────

@app.get("/wizard", response_class=HTMLResponse)
async def wizard_landing(request: Request):
    return templates.TemplateResponse(request=request, name="wizard/step1.html", context={
        "request": request, "step": 1, "total_steps": 4, "active_nav": "wizard"
    })


@app.get("/wizard/step/1", response_class=HTMLResponse)
async def wizard_step1(request: Request):
    return templates.TemplateResponse(request=request, name="wizard/step1.html", context={
        "request": request, "step": 1, "total_steps": 4, "active_nav": "wizard"
    })


@app.post("/wizard/step/1", response_class=HTMLResponse)
async def wizard_step1_post(request: Request, country: str = Form(...)):
    safe_country = sanitize(country, 5)
    return templates.TemplateResponse(request=request, name="wizard/step2.html", context={
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
    return templates.TemplateResponse(request=request, name="wizard/step3.html", context={
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
    return templates.TemplateResponse(request=request, name="wizard/step4.html", context={
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
    return templates.TemplateResponse(request=request, name="timeline.html", context={
        "request": request,
        "timeline": timeline_data.model_dump(),
        "active_nav": "wizard"
    })


# ──────────────────────────────────
# Quiz & Readiness
# ──────────────────────────────────

@app.get("/quiz", response_class=HTMLResponse)
async def quiz_landing(request: Request):
    return templates.TemplateResponse(request=request, name="quiz/landing.html", context={
        "request": request, "active_nav": "quiz"
    })


@app.post("/quiz/start", response_class=HTMLResponse)
@limiter.limit("100/15minutes")
async def quiz_start(
    request: Request,
    country: str = Form("US"),
    state: str = Form(""),
    category: str = Form(""),
    difficulty: str = Form("mixed"),
    count: int = Form(5)
):
    safe_country = sanitize(country, 5)
    safe_state = sanitize(state, 30)
    safe_category = sanitize(category or "", 20)
    safe_difficulty = sanitize(difficulty, 10)

    questions = await get_quiz_questions(
        country=safe_country,
        state=safe_state or None,
        category=safe_category or None,
        difficulty=safe_difficulty,
        count=min(count, 10)
    )

    if not questions:
        return templates.TemplateResponse(request=request, name="quiz/no_questions.html", context={
            "request": request, "country": safe_country, "state": safe_state
        }, status_code=404)

    import json
    questions_json = json.dumps([q.model_dump() for q in questions])

    return templates.TemplateResponse(request=request, name="quiz/question.html", context={
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
    try:
        data = await req.json()
        attempts = [QuizAttempt(
            question_id=q["id"],
            selected_idx=a,
            is_correct=False
        ) for q, a in zip(data["questions"], data["answers"])]

        from app.quiz import QUIZ_BANK
        questions = []
        for q_data in data["questions"]:
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

        score_color = "#22c55e" if result.percentage >= 70 else "#d97706" if result.percentage >= 50 else "#dc2626"
        score_emoji = "\U0001F7E2" if result.percentage >= 70 else "\U0001F7E1" if result.percentage >= 50 else "\U0001F534"
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
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────
# Scenario Simulator
# ──────────────────────────────────

from app.scenarios import SCENARIOS, generate_scenario_solution


@app.get("/scenarios", response_class=HTMLResponse)
async def scenarios_page(request: Request):
    start = time.time()
    increment("total_page_views")
    response = templates.TemplateResponse(request=request, name="scenarios.html", context={
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
    start = time.time()
    increment("scenarios_viewed")

    session_state = request.session.get("wizard_state", {})
    state = session_state.get("state", "")

    result = await generate_scenario_solution(scenario_id, state or None)

    record_endpoint_time("/scenarios/partial", (time.time() - start) * 1000)
    return templates.TemplateResponse(request=request, name="scenarios_partial.html", context={
        "request": request,
        "result": result.model_dump() if result else None
    })


@app.get("/quiz/results", response_class=HTMLResponse)
async def quiz_results(request: Request):
    return templates.TemplateResponse(request=request, name="quiz/results.html", context={
        "request": request,
        "active_nav": "quiz"
    })


# ──────────────────────────────────
# Readiness
# ──────────────────────────────────

@app.get("/readiness", response_class=HTMLResponse)
async def readiness_dashboard(
    request: Request,
    country: str = "US",
    state: str = ""
):
    safe_country = sanitize(country, 5)
    safe_state = sanitize(state, 30)

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

    return templates.TemplateResponse(request=request, name="readiness/dashboard.html", context={
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
    try:
        data = await req.json()

        progress = ReadinessProgress(
            country=data["country"],
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
        raise HTTPException(status_code=400, detail=str(e))
