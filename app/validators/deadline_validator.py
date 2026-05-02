# app/validators/deadline_validator.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class DeadlineResult:
    date: Optional[str]
    confidence: str
    sources: List[str]
    warning: Optional[str] = None
    error: Optional[str] = None

class DeadlineValidator:
    def __init__(self, anchor_dates: Dict[str, Any]):
        self.anchor_dates = anchor_dates
        
    def validate(self, state: str, api_date: Optional[str], deadline_type: str = "General Election") -> DeadlineResult:
        manual_result = self.anchor_dates.get(deadline_type)
        
        if api_date and manual_result and api_date == manual_result:
            return DeadlineResult(date=api_date, confidence="verified", sources=["google", "manual"])
        elif api_date and not manual_result:
            return DeadlineResult(date=api_date, confidence="api_data", sources=["google"], warning="Verify with state office")
        elif api_date and manual_result and api_date != manual_result:
            return DeadlineResult(date=None, confidence="conflict", sources=["google", "manual"], error="Conflicting sources")
        elif manual_result:
            return DeadlineResult(date=manual_result, confidence="manual", sources=["manual"])
        else:
            return DeadlineResult(date=None, confidence="low", sources=[])
