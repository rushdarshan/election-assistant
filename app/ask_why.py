import json
import google.generativeai as genai
import os
from app.models import AskWhyResponse, TimelineResult
from app.kb import retrieve_snippets
from typing import Optional

# Initialize Gemini AI
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_CIVIC_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    # Using gemini-1.5-flash for speed
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

SYSTEM_PROMPT = """You are an election education assistant. Your job is to explain processes clearly and safely.

Hard rules:
1) You MUST answer using ONLY the provided Knowledge Base snippets and the provided timeline_context.
2) Do NOT invent deadlines, ID rules, or state-specific requirements. If not present in snippets/context, say it varies and direct the user to official links.
3) Output MUST be valid JSON matching the required schema. Output NOTHING else.
4) Provide citations: every key claim must be supported by at least one citations[].quote drawn from the KB snippets.
5) Be neutral and nonpartisan.
6) Do not request sensitive personal data.

Style rules:
- Use plain language.
- Keep summary under 30 words.
- Prefer bullet-like short sentences in arrays."""

def build_user_prompt(country: str, state: str, topic_id: str, timeline_context: TimelineResult, snippets: list) -> str:
    kb_snippets_with_ids = ""
    for snippet in snippets:
        kb_snippets_with_ids += f"ID: {snippet['id']}\nContent: {snippet['body']}\n\n"
        
    prompt = f"""Context:
- country: {country}
- state: {state}
- topic_id: {topic_id}
- timeline_context: {timeline_context.model_dump_json()}

Knowledge Base Snippets:
{kb_snippets_with_ids}

Task:
Return a JSON object matching the required schema. Include:
- explanation (3–6 items)
- what_varies (2–5 items)
- next_steps: link only to URLs that appear in timeline_context OR in KB snippet source_url fields.
- if_something_goes_wrong (2–4 items)
- disclaimer: always remind user to confirm with official election office."""
    return prompt

from app.security import validate_llm_output
import time
import hashlib

_CACHE = {}
_CACHE_TTL = 3600

async def ask_why(country: str, state: str, topic_id: str, timeline_context: TimelineResult) -> AskWhyResponse:
    snippets = retrieve_snippets(country, state, topic_id)
    user_prompt = build_user_prompt(country, state, topic_id, timeline_context, snippets)
    
    # ── Efficiency: Cache layer ──
    cache_key = hashlib.md5(user_prompt.encode('utf-8')).hexdigest()
    now = time.time()
    if cache_key in _CACHE:
        entry, timestamp = _CACHE[cache_key]
        if now - timestamp < _CACHE_TTL:
            return AskWhyResponse(**entry)

    
    fallback_kwargs = {
        "topic_id": topic_id,
        "summary": "We are unable to generate an explanation at this time.",
        "explanation": ["Please check the official links provided in your timeline for more information."],
        "what_varies": [],
        "next_steps": [],
        "if_something_goes_wrong": [],
        "citations": [],
        "disclaimer": "Always refer to official sources."
    }

    if not model:
        # Return fallback mock if Vertex AI is not configured
        fallback_kwargs["summary"] = "Fallback summary. Vertex AI not configured."
        return AskWhyResponse(**fallback_kwargs)

    try:
        model_with_sys = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
        response = model_with_sys.generate_content(
            contents=user_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Security: Use the security layer for JSON schema validation and parsing
        valid_response = validate_llm_output(response.text, AskWhyResponse, fallback_kwargs=fallback_kwargs)
        _CACHE[cache_key] = (valid_response.model_dump(), time.time())
        return valid_response
        
    except Exception as e:
        print(f"Agentic RAG generation failed: {e}")
        return AskWhyResponse(**fallback_kwargs)
