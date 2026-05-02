from typing import List, Dict, Any
from app.models import Milestone

def _confidence_style(confidence: str) -> Dict[str, str]:
    conf = str(confidence).lower()
    if conf in ["verified", "high", "0.95"]:
        return {"bg": "#d4edda", "color": "#006837", "icon": "✓", "label": "HIGH", "level": "high"}
    elif conf in ["api_data", "medium", "0.6"]:
        return {"bg": "#fff3cd", "color": "#a66100", "icon": "◐", "label": "MEDIUM", "level": "medium"}
    elif conf in ["fallback", "low", "mismatch"]:
        return {"bg": "#f8d7da", "color": "#b30000", "icon": "⚠", "label": "LOW", "level": "low"}
    else:
        return {"bg": "#e0e0e0", "color": "#333333", "icon": "?", "label": "UNKNOWN", "level": "low"}

def render_html_timeline(milestones: List[Milestone]) -> str:
    if not milestones:
        return '<p class="no-milestones">No timeline events found.</p>'
    
    items_html = ""
    for ms in milestones:
        style = _confidence_style(ms.confidence)
        source_count = getattr(ms, 'source_count', 2) if style["level"] == "high" else (getattr(ms, 'source_count', 1) if style["level"] == "medium" else 1)
        needs_verify = style["level"] == "low"
        
        items_html += f'''
        <li class="timeline-item" tabindex="0" role="listitem"
            aria-label="{ms.label}: {ms.date}. Confidence: {style["label"]} ({source_count} sources).{' Verify manually.' if needs_verify else ''}"
            data-milestone-id="{ms.id}">
            <div class="timeline-marker" style="background:{style['color']}">
                <span class="marker-icon">{style['icon']}</span>
            </div>
            <div class="timeline-content">
                <div class="timeline-header">
                    <span class="timeline-label">{ms.label}</span>
                    <span class="confidence-badge" style="background:{style['bg']};color:{style['color']}">
                        {style['icon']} {style['label']} ({source_count} sources)
                    </span>
                </div>
                <div class="timeline-date">{ms.date}</div>
                {"<div class='verify-warning' role='alert'>⚠ Verify this date with your state election office</div>" if needs_verify else ""}
            </div>
        </li>'''
    
    return f'''
    <ul class="timeline-list" role="list" aria-label="Election timeline">
        {items_html}
    </ul>
    <div class="timeline-legend" role="note" aria-label="Timeline confidence legend">
        <span class="legend-item" style="color:#006837">✓ HIGH</span> — 2+ verified sources
        <span class="legend-item" style="color:#a66100">◐ MEDIUM</span> — 1 source, verify
        <span class="legend-item" style="color:#b30000">⚠ LOW</span> — fallback only
    </div>'''