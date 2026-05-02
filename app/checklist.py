from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.models import ReadinessProgress
from app.readiness import calculate_readiness_score, get_readiness_color, get_readiness_emoji
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CHECKLIST_ITEMS = [
    {"id": "c1", "text": "Verified registration status"},
    {"id": "c2", "text": "Chosen voting method (in-person / early / mail)"},
    {"id": "c3", "text": "Reviewed personalized timeline"},
    {"id": "c4", "text": "Located polling place"},
    {"id": "c5", "text": "Checked ID requirements for state"},
    {"id": "c6", "text": "Requested mail ballot (if applicable)"},
    {"id": "c7", "text": "Researched candidates/measures on ballot"},
    {"id": "c8", "text": "Arranged transportation/time off work"},
    {"id": "c9", "text": "Reviewed voter rights and rules"},
    {"id": "c10", "text": "Taken readiness quiz"}
]

@router.get("/checklist", response_class=HTMLResponse)
async def checklist_page(request: Request):
    state = request.session.get("checklist_state", {})
    progress = ReadinessProgress(
        country="US",
        state="",
        checklist_items_completed=sum(state.values()),
        last_updated=datetime.now().isoformat()
    )
    score_obj = await calculate_readiness_score(progress)
    
    return templates.TemplateResponse(request=request, name="checklist.html", context= {
        "request": request,
        "active_nav": "checklist",
        "items": CHECKLIST_ITEMS,
        "state": state,
        "score": score_obj,
        "color": get_readiness_color(score_obj.overall_score),
        "emoji": get_readiness_emoji(score_obj.overall_score)
    })

@router.post("/checklist/toggle/{item_id}", response_class=HTMLResponse)
async def checklist_toggle(request: Request, item_id: str):
    state = request.session.get("checklist_state", {})
    state[item_id] = not state.get(item_id, False)
    request.session["checklist_state"] = state
    
    progress = ReadinessProgress(
        country="US",
        state="",
        checklist_items_completed=sum(state.values()),
        last_updated=datetime.now().isoformat()
    )
    score_obj = await calculate_readiness_score(progress)
    
    return templates.TemplateResponse(request=request, name="checklist_score.html", context= {
        "request": request,
        "score": score_obj,
        "color": get_readiness_color(score_obj.overall_score),
        "emoji": get_readiness_emoji(score_obj.overall_score)
    })
