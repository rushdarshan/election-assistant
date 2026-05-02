import pytest
from app.renderers.html_timeline import render_html_timeline
from app.renderers.svg_timeline import render_svg_timeline
from app.models import Milestone

@pytest.mark.asyncio
async def test_html_timeline_renders():
    milestones = [
        Milestone(id="test1", label="Register by", date="2026-10-19", confidence="verified",
                 confidence_level="high", source_count=2, needs_manual_verify=False),
        Milestone(id="test2", label="Election Day", date="2026-11-03", confidence="fallback",
                 confidence_level="low", source_count=1, needs_manual_verify=True)
    ]
    html = render_html_timeline(milestones)
    assert "timeline-list" in html
    assert "Register by" in html
    assert "Election Day" in html
    assert "Verify manually" in html

@pytest.mark.asyncio
async def test_html_timeline_empty():
    html = render_html_timeline([])
    assert "No timeline events" in html

@pytest.mark.asyncio
async def test_svg_timeline_has_aria():
    milestones = [
        Milestone(id="test1", label="Election Day", date="2026-11-03", confidence="verified",
                 confidence_level="high", source_count=2, needs_manual_verify=False)
    ]
    svg = render_svg_timeline(milestones)
    assert "<title>" in svg
    assert "Election Day" in svg
    assert "role=\"img\"" in svg

def test_confidence_badge_high():
    milestones = [
        Milestone(id="t1", label="Test", date="2026-11-03", confidence="verified",
                 confidence_level="high", source_count=2, needs_manual_verify=False)
    ]
    html = render_html_timeline(milestones)
    assert "HIGH" in html
    assert "2 sources" in html

def test_confidence_badge_low():
    milestones = [
        Milestone(id="t1", label="Test", date="TBD", confidence="fallback",
                 confidence_level="low", source_count=1, needs_manual_verify=True)
    ]
    html = render_html_timeline(milestones)
    assert "LOW" in html
    assert "Verify" in html