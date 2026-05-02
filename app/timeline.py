from typing import Optional, List
from app.models import TimelineResult, Jurisdiction, Milestone
from app.providers import get_provider
from app.renderers.svg_timeline import render_svg_timeline

async def generate_timeline(
    country: str,
    state: str,
    registration_status: str,
    voting_method: str,
    moved_recently: bool,
    voting_elsewhere: bool = False,
    zip_code: Optional[str] = None
) -> TimelineResult:
    provider = get_provider(country)
    
    data = await provider.get_timeline_data(
        state=state,
        zip_code=zip_code,
        registration_status=registration_status,
        voting_method=voting_method,
        moved_recently=moved_recently,
        voting_elsewhere=voting_elsewhere
    )
    
    milestones_raw = data.get("milestones", [])
    milestones: List[Milestone] = [
        Milestone(**m) for m in milestones_raw
    ]
    svg_content = render_svg_timeline(milestones)
    
    return TimelineResult(
        jurisdiction=Jurisdiction(country=country, state=state),
        milestones=milestones,
        checklist=data.get("checklist", []),
        official_links=data.get("official_links", []),
        source_notes=data.get("source_notes", []),
        svg=svg_content,
        gemini_enrichment=data.get("gemini_enrichment")
    )
