"""
Scenario Simulator — AI-powered "what-if" explorer for voter edge cases.
Generates step-by-step solutions for common voting scenarios.
"""
import json
import os
from typing import Optional
import google.generativeai as genai

from app.models import ScenarioResult, OfficialLink
from app.security import validate_llm_output

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_CIVIC_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

SYSTEM_PROMPT = """You are a helpful election education assistant for US voters.

Hard rules:
1. Be neutral and nonpartisan — never mention parties, candidates, or political positions.
2. Base all guidance on official US election processes and state-specific rules.
3. Give step-by-step, actionable instructions that a first-time voter can follow.
4. Include links ONLY to official government election websites (.gov domains).
5. If unsure about state-specific details, say so and direct to the state election office.
6. Output MUST be valid JSON matching the required schema. Output NOTHING else.

Style rules:
- Use plain language, no jargon.
- Keep steps concise — 1-2 sentences each.
- Always end with a clear next action."""

SCENARIOS = {
    "lost_voter_id": {
        "title": "Lost Voter ID Card",
        "description": "What to do if you lost or misplaced your voter registration card",
        "icon": "🪪",
    },
    "moved_wrong_precinct": {
        "title": "Moved to a New Address",
        "description": "How to update your registration when you've moved",
        "icon": "🏠",
    },
    "name_mismatch": {
        "title": "Name Mismatch on Voter Roll",
        "description": "What to do if your name doesn't match the voter registration list",
        "icon": "✏️",
    },
    "missed_deadline": {
        "title": "Missed Registration Deadline",
        "description": "Options available if you missed the voter registration deadline",
        "icon": "⏰",
    },
    "no_id_at_polling": {
        "title": "No Acceptible ID at Polling Place",
        "description": "What to do if you arrive at the polls without proper identification",
        "icon": "🆔",
    },
    "lost_mail_ballot": {
        "title": "Mail Ballot Not Received or Lost",
        "description": "How to handle a mail-in ballot that was lost in the mail",
        "icon": "📬",
    },
    "provisional_ballot": {
        "title": "Provisional Ballot Process",
        "description": "When and how you may need to cast a provisional ballot",
        "icon": "🗳️",
    },
    "accessibility_accommodations": {
        "title": "Accessibility Accommodations",
        "description": "Available accommodations for voters with disabilities",
        "icon": "♿",
    },
}


def build_scenario_prompt(scenario_id: str, state: Optional[str] = None) -> str:
    scenario = SCENARIOS.get(scenario_id, SCENARIOS["lost_voter_id"])
    state_context = f"State: {state}" if state else "State: Not specified (provide general guidance)"

    return f"""Scenario: {scenario_id}
Title: {scenario['title']}
{state_context}

Provide a detailed, step-by-step solution for this scenario. Address:
1. What the voter should do immediately
2. Required documents and forms
3. Official websites and contact numbers
4. Expected timeline for resolution
5. What to do on election day if the issue isn't resolved

Format your response as JSON:
{{
  "scenario_id": "{scenario_id}",
  "title": "{scenario['title']}",
  "description": "Brief overview of the situation and solution",
  "steps": [
    {{
      "number": 1,
      "action": "Short action title",
      "details": "2-3 sentence explanation of what to do",
      "link": "https://... (official .gov URL, or null if none)"
    }}
  ],
  "documents_needed": ["Document 1", "Document 2"],
  "estimated_time": "e.g., 3-5 business days",
  "official_links": [
    {{
      "label": "Link description",
      "url": "https://..."
    }}
  ],
  "next_action": "One clear immediate next step"
}}"""


FALLBACK_SCENARIOS = {
    sid: {
        "scenario_id": sid,
        "title": SCENARIOS[sid]["title"],
        "description": "Please visit your state's election website for guidance on this scenario.",
        "steps": [
            {"number": 1, "action": "Contact your state election office", "details": "Visit your state's Secretary of State or Board of Elections website for specific guidance.", "link": None},
            {"number": 2, "action": "Call the Election Protection hotline", "details": "Call 1-866-OUR-VOTE (1-866-687-8683) for nonpartisan assistance.", "link": "https://866ourvote.org"},
        ],
        "documents_needed": ["Photo ID (if available)", "Proof of address"],
        "estimated_time": "Varies by state",
        "official_links": [
            {"label": "Find your state election office", "url": "https://www.usa.gov/election-office"},
        ],
        "next_action": "Contact your state election office or call 1-866-OUR-VOTE",
    }
    for sid in SCENARIOS
}


async def generate_scenario_solution(scenario_id: str, state: Optional[str] = None) -> ScenarioResult:
    if scenario_id not in SCENARIOS:
        return ScenarioResult(**FALLBACK_SCENARIOS.get("lost_voter_id", {}))

    prompt = build_scenario_prompt(scenario_id, state)

    fallback = FALLBACK_SCENARIOS.get(scenario_id, FALLBACK_SCENARIOS["lost_voter_id"])

    if not model:
        return ScenarioResult(**fallback)

    try:
        model_with_sys = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
        response = model_with_sys.generate_content(
            contents=prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return validate_llm_output(response.text, ScenarioResult, fallback_kwargs=fallback)
    except Exception as e:
        print(f"Scenario generation failed: {e}")
        return ScenarioResult(**fallback)
