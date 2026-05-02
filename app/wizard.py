from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta


class WizardSession(BaseModel):
    country: str = ""
    state: str = ""
    registration_status: str = ""
    voting_method: str = ""
    moved_recently: bool = False
    current_step: int = 0
    updated_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        if self.updated_at is None:
            return True
        return datetime.now() - self.updated_at > timedelta(minutes=timeout_minutes)
    
    def clear(self):
        self.country = ""
        self.state = ""
        self.registration_status = ""
        self.voting_method = ""
        self.moved_recently = False
        self.current_step = 0
        self.updated_at = None


# In-memory session storage (for production, use Redis or database)
_session_store: dict[str, WizardSession] = {}


def get_session(session_id: str) -> Optional[WizardSession]:
    """Get session by ID, returns None if expired or not found."""
    session = _session_store.get(session_id)
    if session and session.is_expired():
        clear_session(session_id)
        return None
    return session


def create_session(session_id: str) -> WizardSession:
    """Create new session."""
    session = WizardSession(current_step=0)
    _session_store[session_id] = session
    return session


def update_session(session_id: str, **kwargs) -> WizardSession:
    """Update session fields."""
    session = get_session(session_id)
    if session is None:
        session = create_session(session_id)
    
    for key, value in kwargs.items():
        if hasattr(session, key):
            setattr(session, key, value)
    
    session.updated_at = datetime.now()
    _session_store[session_id] = session
    return session


def clear_session(session_id: str):
    """Clear session data."""
    if session_id in _session_store:
        del _session_store[session_id]


def should_show_moved_question(session: WizardSession) -> bool:
    """Check if conditional 'moved recently' question should show."""
    return session.registration_status == "unsure"