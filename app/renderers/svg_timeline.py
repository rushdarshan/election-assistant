from typing import List, Dict, Any
from app.models import Milestone

def _get_confidence_meta(confidence: str) -> Dict[str, Any]:
    conf = str(confidence).lower()
    if conf in ["verified", "high", "0.95"]:
        return {"color": "#059669", "label": "HIGH", "level": "high"}
    elif conf in ["api_data", "medium", "0.6"]:
        return {"color": "#D97706", "label": "MEDIUM", "level": "medium"}
    else:
        return {"color": "#DC2626", "label": "LOW", "level": "low"}

def render_svg_timeline(milestones: List[Milestone]) -> str:
    if not milestones:
        return '<p>No timeline events found.</p>'
    
    svg_width = 800
    svg_height = max(200, len(milestones) * 100 + 50)
    
    svg = f'''<svg width="100%" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" 
         xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Election Timeline with key dates">
    <title>Your Election Timeline</title>
    <desc>A visual timeline showing election deadlines with confidence indicators</desc>'''
    
    # Removed hardcoded white background so it respects the app's theme
    svg += f'<line x1="150" y1="40" x2="150" y2="{svg_height - 40}" stroke="var(--civic-accent)" stroke-width="6" />'
    
    y_offset = 60
    for ms in milestones:
        meta = _get_confidence_meta(ms.confidence)
        conf_level = getattr(ms, 'confidence_level', meta["level"])
        source_count = getattr(ms, 'source_count', 2)
        needs_verify = getattr(ms, 'needs_manual_verify', conf_level == "low")
        aria_label = f"{ms.label}: {ms.date}. Confidence: {meta['label']} ({source_count} sources).{' Verify manually.' if needs_verify else ''}"
        
        svg += f'''
        <g class="milestone" tabindex="0" role="button" aria-label="{aria_label}">
            <title>{ms.label}: {ms.date}</title>
            <desc>Confidence: {meta['label']}, {source_count} source{'s' if source_count != 1 else ''}.{' WARNING: Verify this date.' if needs_verify else ''}</desc>
            <circle cx="150" cy="{y_offset}" r="14" fill="{meta['color']}" stroke="var(--civic-white)" stroke-width="3" />
            <text x="190" y="{y_offset + 5}" font-family="'Work Sans', sans-serif" font-size="20" font-weight="700" fill="currentColor">{ms.label}</text>
            <text x="190" y="{y_offset + 28}" font-family="'Work Sans', sans-serif" font-size="16" fill="var(--civic-gray)">Date: {ms.date}</text>
            <rect x="190" y="{y_offset + 38}" width="180" height="24" rx="12" fill="{meta['color']}" fill-opacity="0.15" />
            <text x="200" y="{y_offset + 55}" font-family="'Work Sans', sans-serif" font-size="13" font-weight="600" fill="{meta['color']}">{meta['label']} ({source_count} src)</text>
            {f'<text x="380" y="{y_offset + 55}" font-family="\'Work Sans\', sans-serif" font-size="14" fill="var(--civic-danger)" font-weight="bold">Verify Date</text>' if needs_verify else ''}
        </g>'''
        y_offset += 100
    
    svg += '</svg>'
    return svg