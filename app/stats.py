from typing import Callable, Dict, Any
from collections import defaultdict
import time
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# In-memory statistics
stats_data = {
    "total_queries": 0,
    "endpoints": defaultdict(int),
    "response_times": defaultdict(list),
    "topics": defaultdict(int),
    "ai_provider": {
        "vertex_ai": 0,
        "fallback": 0
    }
}

def categorize_query(text: str) -> str:
    text = text.lower()
    if any(k in text for k in ['id', 'identification', 'license', 'passport']): return "ID Requirements"
    if any(k in text for k in ['register', 'registration', 'deadline']): return "Registration"
    if any(k in text for k in ['mail', 'absentee', 'post', 'ballot']): return "Mail Voting"
    if any(k in text for k in ['where', 'location', 'polling', 'place']): return "Polling Location"
    if any(k in text for k in ['early', 'advance']): return "Early Voting"
    return "General"

def record_topic(query: str):
    category = categorize_query(query)
    stats_data["topics"][category] += 1

def record_ai_usage(provider: str):
    if provider in stats_data["ai_provider"]:
        stats_data["ai_provider"][provider] += 1

@router.get("/stats", response_class=HTMLResponse)
async def view_stats(request: Request):
    # Calculate averages
    avg_times = {}
    for ep, times in stats_data["response_times"].items():
        if times:
            avg_times[ep] = sum(times) / len(times)
        else:
            avg_times[ep] = 0.0
            
    return templates.TemplateResponse(request=request, name="stats.html", context= {
        "request": request,
        "active_nav": "stats",
        "total_queries": stats_data["total_queries"],
        "endpoints": dict(stats_data["endpoints"]),
        "avg_times": avg_times,
        "topics": dict(stats_data["topics"]),
        "ai_provider": stats_data["ai_provider"]
    })
