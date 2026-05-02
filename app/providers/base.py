from typing import Protocol, Optional, Dict, Any

class JurisdictionProvider(Protocol):
    async def get_timeline_data(
        self,
        state: str,
        zip_code: Optional[str],
        registration_status: str,
        voting_method: str,
        moved_recently: bool,
        voting_elsewhere: bool = False
    ) -> Dict[str, Any]:
        """Return dict with milestones, checklist, official_links, source_notes."""
        ...
        
    async def get_kb_context(self, state: str) -> Optional[Dict[str, Any]]:
        """Return context for Ask-Why (state-specific rules, etc.)."""
        ...
