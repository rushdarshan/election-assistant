from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class RegistrationStatus(str, Enum):
    YES = "yes"
    NO = "no"
    UNSURE = "unsure"

class Jurisdiction(BaseModel):
    country: str
    state: str

class Milestone(BaseModel):
    id: str
    label: str
    date: str
    confidence: str
    confidence_level: Optional[str] = "medium"
    source_count: Optional[int] = 1
    needs_manual_verify: Optional[bool] = False

class ChecklistItem(BaseModel):
    id: str
    label: str
    link: Optional[str] = None

class OfficialLink(BaseModel):
    label: str
    url: str

class SourceNote(BaseModel):
    source: str
    details: str

class TimelineResult(BaseModel):
    jurisdiction: Jurisdiction
    milestones: List[Milestone]
    checklist: List[ChecklistItem]
    official_links: List[OfficialLink]
    source_notes: List[SourceNote]
    svg: Optional[str] = None
    gemini_enrichment: Optional[dict] = None

class Citation(BaseModel):
    kb_id: str
    quote: str

class AskWhyResponse(BaseModel):
    topic_id: str
    summary: str = Field(..., max_length=300)
    explanation: List[str]
    what_varies: List[str]
    next_steps: List[OfficialLink]
    if_something_goes_wrong: List[str]
    citations: List[Citation]
    disclaimer: str

class AskWhyRequest(BaseModel):
    country: str
    state: str
    topic_id: str
    timeline_context: TimelineResult

# ──────────────────────────────────────────────────────
# Quiz System Models
# ──────────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    id: str
    question: str
    category: str  # registration, voting, deadline, etc.
    difficulty: str  # easy, medium, hard
    options: List[str]
    correct_answer_idx: int
    explanation: str
    source: str

class QuizAttempt(BaseModel):
    question_id: str
    selected_idx: int
    is_correct: bool

class QuizResult(BaseModel):
    score: int
    total: int
    percentage: float
    category_breakdown: dict  # {category: {correct: int, total: int}}
    time_taken_seconds: int
    passed: bool = True

class QuizSession(BaseModel):
    country: str
    state: str
    category: Optional[str] = None  # None = random mix
    difficulty: Optional[str] = "mixed"
    question_count: int = 5

# ──────────────────────────────────────────────────────
# Readiness Tracking Models
# ──────────────────────────────────────────────────────

class ReadinessProgress(BaseModel):
    country: str
    state: str
    registration_status: Optional[str] = None
    voting_method: Optional[str] = None
    timeline_viewed: bool = False
    questions_asked: int = 0
    quiz_attempts: int = 0
    quiz_best_score: Optional[float] = None
    checklist_items_completed: int = 0
    last_updated: str  # ISO timestamp

class ReadinessScore(BaseModel):
    overall_score: float  # 0-100
    registration_ready: float  # 0-100
    voting_ready: float  # 0-100
    knowledge_ready: float  # 0-100
    breakdown: dict
    next_steps: List[str]
    completion_percentage: float


# ──────────────────────────────────────────────────────
# Scenario Simulator Models
# ──────────────────────────────────────────────────────

class ScenarioStep(BaseModel):
    number: int
    action: str
    details: str
    link: Optional[str] = None

class ScenarioResult(BaseModel):
    scenario_id: str
    title: str
    description: str
    steps: List[ScenarioStep]
    documents_needed: List[str]
    estimated_time: str
    official_links: List[OfficialLink]
    next_action: str


# ──────────────────────────────────────────────────────
# Chat Models
# ──────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str  # ISO timestamp


# ──────────────────────────────────────────────────────
# Polling Place Models
# ──────────────────────────────────────────────────────

class PollingPlaceResult(BaseModel):
    polling_place_name: str
    address: str
    hours: Optional[str] = None
    available_methods: List[str] = []
    google_maps_url: str
