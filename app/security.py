# app/security.py
import json
from pydantic import ValidationError
from typing import Any, Dict

def validate_llm_output(response: str, schema_class: Any, fallback_kwargs: Dict[str, Any] = None) -> Any:
    """Validates raw LLM string output against a Pydantic schema."""
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1)
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    
    try:
        parsed = json.loads(cleaned.strip())
        return schema_class(**parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Validation error: {e}")
        if fallback_kwargs is not None:
            return schema_class(**fallback_kwargs)
        raise ValueError("Failed to validate LLM output against strict schema")
