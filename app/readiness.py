"""
Readiness Scoring - Voter preparedness tracking & visualization
"""
from app.models import ReadinessProgress, ReadinessScore


async def calculate_readiness_score(progress: ReadinessProgress) -> ReadinessScore:
    """
    Calculate voter readiness across 3 dimensions:
    - Registration Ready (0-100): Have they verified registration status?
    - Voting Ready (0-100): Do they know HOW and WHERE to vote?
    - Knowledge Ready (0-100): Have they studied rules via quiz?
    """
    
    # ── Registration Readiness (0-100) ──
    registration_ready = 0.0
    if progress.registration_status:
        if progress.registration_status == "yes":
            registration_ready = 100.0  # Already registered
        elif progress.registration_status == "no":
            registration_ready = 50.0   # Knows they're not - need to register
        else:  # unsure
            registration_ready = 25.0   # Hasn't checked yet
    
    # ── Voting Readiness (0-100) ──
    voting_ready = 0.0
    if progress.voting_method:
        voting_ready = 75.0  # Chosen method
    if progress.timeline_viewed:
        voting_ready = min(voting_ready + 25, 100.0)  # Reviewed timeline
    
    # ── Knowledge Readiness (0-100) ──
    knowledge_ready = 0.0
    if progress.quiz_best_score:
        knowledge_ready = progress.quiz_best_score * 0.7  # Quiz performance (70%)
    
    if progress.questions_asked > 0:
        # Q&A engagement (20%)
        knowledge_ready += min(progress.questions_asked / 5, 1.0) * 20
    
    if progress.quiz_attempts > 1:
        # Learning persistence (10%)
        knowledge_ready += min((progress.quiz_attempts - 1) / 2, 1.0) * 10
    
    knowledge_ready = min(knowledge_ready, 100.0)
    
    # ── Checklist Completion ──
    # Estimated max checklist items: 8 (verify registration, research candidates, find polling location, etc)
    checklist_completion = min((progress.checklist_items_completed / 8) * 100, 100.0) if progress.checklist_items_completed > 0 else 0.0
    
    # ── Overall Score (weighted average) ──
    overall_score = min(
        registration_ready * 0.35 +      # Most critical
        voting_ready * 0.35 +             # How to vote
        knowledge_ready * 0.20 +          # Understanding rules
        checklist_completion * 0.10,      # Execution
        100.0
    )
    
    breakdown = {
        "registration_ready": round(registration_ready, 1),
        "voting_ready": round(voting_ready, 1),
        "knowledge_ready": round(knowledge_ready, 1),
        "checklist_completion": round(checklist_completion, 1),
    }
    
    # ── Next Steps (contextual) ──
    next_steps = []
    if registration_ready < 100:
        if progress.registration_status is None:
            next_steps.append("✅ Check your voter registration status")
        elif progress.registration_status in ("no", "unsure"):
            next_steps.append("✅ Register to vote or verify your registration")
    
    if voting_ready < 75:
        if not progress.voting_method:
            next_steps.append("✅ Choose your voting method (in-person, early, or mail-in)")
        if not progress.timeline_viewed:
            next_steps.append("✅ Review your personalized timeline")
    
    if knowledge_ready < 70:
        next_steps.append("✅ Take the readiness quiz to strengthen your knowledge")
    
    if progress.checklist_items_completed < 3:
        next_steps.append("✅ Work through the voter checklist")
    
    # Default message if fully ready
    if not next_steps:
        next_steps = ["🎉 You're voting-ready! Review the timeline once more before election day."]
    
    completion_percentage = min(
        (registration_ready + voting_ready + knowledge_ready + checklist_completion) / 4,
        100.0
    )
    
    return ReadinessScore(
        overall_score=round(overall_score, 1),
        registration_ready=round(registration_ready, 1),
        voting_ready=round(voting_ready, 1),
        knowledge_ready=round(knowledge_ready, 1),
        breakdown=breakdown,
        next_steps=next_steps,
        completion_percentage=round(completion_percentage, 1)
    )


def get_readiness_color(score: float) -> str:
    """Return semantic color class for readiness score."""
    if score >= 85:
        return "readiness-excellent"  # Green
    elif score >= 65:
        return "readiness-good"  # Yellow
    elif score >= 40:
        return "readiness-fair"  # Orange
    else:
        return "readiness-needs-work"  # Red


def get_readiness_emoji(score: float) -> str:
    """Return emoji indicator for readiness level."""
    if score >= 90:
        return "🟢"
    elif score >= 70:
        return "🟡"
    elif score >= 40:
        return "🟠"
    else:
        return "🔴"


def get_readiness_label(score: float) -> str:
    """Return text label for readiness level."""
    if score >= 85:
        return "Voting-Ready"
    elif score >= 65:
        return "Getting Ready"
    elif score >= 40:
        return "Some Preparation Needed"
    else:
        return "Start Here"
