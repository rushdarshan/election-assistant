import pytest
from app.ask_why import ask_why
from app.models import TimelineResult, Jurisdiction

@pytest.mark.asyncio
async def test_ask_why_fallback_when_no_vertex():
    # If Vertex AI is not configured, it returns a fallback
    timeline = TimelineResult(
        jurisdiction=Jurisdiction(country="US", state="CA"),
        milestones=[],
        checklist=[],
        official_links=[],
        source_notes=[]
    )
    response = await ask_why(
        country="US",
        state="CA",
        topic_id="us_no_id_how_verified",
        timeline_context=timeline
    )
    assert response.topic_id == "us_no_id_how_verified"
    assert response.summary != ""
    assert isinstance(response.explanation, list)
