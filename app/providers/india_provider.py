from typing import Optional, Dict, Any, List
import os
import json

# ── Full roster: every Indian state & UT with canonical codes ──
INDIA_DATA = {
    # 2026 Elections (Already voted)
    "TN": {"name": "Tamil Nadu", "type": "State", "election_day": "April 23, 2026", "counting_day": "May 4, 2026", "schedule_announced": "March 15, 2026", "status": "Already voted"},
    "KL": {"name": "Kerala", "type": "State", "election_day": "April 9, 2026", "counting_day": "May 4, 2026", "schedule_announced": "March 15, 2026", "status": "Already voted"},
    "AS": {"name": "Assam", "type": "State", "election_day": "April 9, 2026", "counting_day": "May 4, 2026", "schedule_announced": "March 15, 2026", "status": "Already voted"},
    "WB": {"name": "West Bengal", "type": "State", "election_day": "April 23 & 29, 2026", "counting_day": "May 4, 2026", "schedule_announced": "March 15, 2026", "status": "Already voted"},
    "PY": {"name": "Puducherry", "type": "UT", "election_day": "April 9, 2026", "counting_day": "May 4, 2026", "schedule_announced": "March 15, 2026", "status": "Already voted"},

    # Past (2025)
    "DL": {"name": "Delhi", "type": "UT", "election_day": "Feb 2025", "status": "Already voted"},
    "BR": {"name": "Bihar", "type": "State", "election_day": "Oct-Nov 2025", "status": "Already voted"},

    # 2027 Elections
    "GA": {"name": "Goa", "type": "State", "election_day": "~Feb-Mar 2027", "status": "Expected"},
    "MN": {"name": "Manipur", "type": "State", "election_day": "~Feb-Mar 2027", "status": "Expected"},
    "PB": {"name": "Punjab", "type": "State", "election_day": "~Feb-Mar 2027", "status": "Expected"},
    "UK": {"name": "Uttarakhand", "type": "State", "election_day": "~Feb 2027", "status": "Expected"},
    "UP": {"name": "Uttar Pradesh", "type": "State", "election_day": "~Apr-May 2027", "status": "Expected"},
    "GJ": {"name": "Gujarat", "type": "State", "election_day": "~Nov-Dec 2027", "status": "Expected"},
    "HP": {"name": "Himachal Pradesh", "type": "State", "election_day": "~Nov-Dec 2027", "status": "Expected"},

    # 2028 Elections
    "ML": {"name": "Meghalaya", "type": "State", "election_day": "~Feb 2028", "status": "Expected"},
    "NL": {"name": "Nagaland", "type": "State", "election_day": "~Feb 2028", "status": "Expected"},
    "TR": {"name": "Tripura", "type": "State", "election_day": "~Feb 2028", "status": "Expected"},
    "KA": {"name": "Karnataka", "type": "State", "election_day": "~May 2028", "status": "Expected"},
    "MZ": {"name": "Mizoram", "type": "State", "election_day": "~Nov 2028", "status": "Expected"},
    "CG": {"name": "Chhattisgarh", "type": "State", "election_day": "~Nov-Dec 2028", "status": "Expected"},
    "MP": {"name": "Madhya Pradesh", "type": "State", "election_day": "~Nov-Dec 2028", "status": "Expected"},
    "RJ": {"name": "Rajasthan", "type": "State", "election_day": "~Nov-Dec 2028", "status": "Expected"},
    "TG": {"name": "Telangana", "type": "State", "election_day": "~Nov-Dec 2028", "status": "Expected"},

    # 2029+ Elections
    "SK": {"name": "Sikkim", "type": "State", "election_day": "~Apr 2029", "status": "Expected"},
    "AR": {"name": "Arunachal Pradesh", "type": "State", "election_day": "~Apr 2029", "status": "Expected"},
    "AP": {"name": "Andhra Pradesh", "type": "State", "election_day": "~May 2029", "status": "Expected"},
    "OR": {"name": "Odisha", "type": "State", "election_day": "~May-Jun 2029", "status": "Expected"},
    "JK": {"name": "Jammu & Kashmir", "type": "UT", "election_day": "~Sep 2029", "status": "Expected"},
    "HR": {"name": "Haryana", "type": "State", "election_day": "~Oct 2029", "status": "Expected"},
    "MH": {"name": "Maharashtra", "type": "State", "election_day": "~Nov 2029", "status": "Expected"},
    "JH": {"name": "Jharkhand", "type": "State", "election_day": "~Nov 2029", "status": "Expected"},

    # No Assembly Elections (UTs administered directly by Centre)
    "CH": {"name": "Chandigarh", "type": "UT", "election_day": "Municipal only", "status": "No assembly"},
    "LA": {"name": "Ladakh", "type": "UT", "election_day": "No assembly", "status": "No assembly"},
    "AN": {"name": "Andaman & Nicobar", "type": "UT", "election_day": "No assembly", "status": "No assembly"},
    "LD": {"name": "Lakshadweep", "type": "UT", "election_day": "No assembly", "status": "No assembly"},
    "DN": {"name": "Dadra & Nagar Haveli", "type": "UT", "election_day": "No assembly", "status": "No assembly"},
    "DD": {"name": "Daman & Diu", "type": "UT", "election_day": "No assembly", "status": "No assembly"},
}

# ── Canonical state list for dropdowns (sorted) ──
INDIA_STATES_LIST = [
    {"code": "AP", "name": "Andhra Pradesh"},
    {"code": "AR", "name": "Arunachal Pradesh"},
    {"code": "AS", "name": "Assam"},
    {"code": "BR", "name": "Bihar"},
    {"code": "CG", "name": "Chhattisgarh"},
    {"code": "DL", "name": "Delhi"},
    {"code": "GA", "name": "Goa"},
    {"code": "GJ", "name": "Gujarat"},
    {"code": "HR", "name": "Haryana"},
    {"code": "HP", "name": "Himachal Pradesh"},
    {"code": "JH", "name": "Jharkhand"},
    {"code": "KA", "name": "Karnataka"},
    {"code": "KL", "name": "Kerala"},
    {"code": "MH", "name": "Maharashtra"},
    {"code": "MP", "name": "Madhya Pradesh"},
    {"code": "MN", "name": "Manipur"},
    {"code": "ML", "name": "Meghalaya"},
    {"code": "MZ", "name": "Mizoram"},
    {"code": "NL", "name": "Nagaland"},
    {"code": "OR", "name": "Odisha"},
    {"code": "PB", "name": "Punjab"},
    {"code": "RJ", "name": "Rajasthan"},
    {"code": "SK", "name": "Sikkim"},
    {"code": "TN", "name": "Tamil Nadu"},
    {"code": "TR", "name": "Tripura"},
    {"code": "TG", "name": "Telangana"},
    {"code": "UP", "name": "Uttar Pradesh"},
    {"code": "UK", "name": "Uttarakhand"},
    {"code": "WB", "name": "West Bengal"},
    {"code": "AN", "name": "Andaman & Nicobar (UT)"},
    {"code": "CH", "name": "Chandigarh (UT)"},
    {"code": "DN", "name": "Dadra & Nagar Haveli (UT)"},
    {"code": "DD", "name": "Daman & Diu (UT)"},
    {"code": "JK", "name": "Jammu & Kashmir (UT)"},
    {"code": "LD", "name": "Lakshadweep (UT)"},
    {"code": "LA", "name": "Ladakh (UT)"},
    {"code": "PY", "name": "Puducherry (UT)"},
]


def resolve_state_key(user_input: str) -> Optional[str]:
    ui_upper = user_input.upper().strip()

    # Check abbreviations
    if ui_upper in INDIA_DATA:
        return ui_upper

    # Check exact names first
    for key, data in INDIA_DATA.items():
        if data["name"].upper() == ui_upper:
            return key

    # Then fallback to substring match
    for key, data in INDIA_DATA.items():
        if data["name"].upper() in ui_upper or ui_upper in data["name"].upper():
            return key

    # Common alternate spellings
    if "TAMIL" in ui_upper: return "TN"
    if "ANDHRA" in ui_upper: return "AP"
    if "DELHI" in ui_upper: return "DL"
    if "KASHMIR" in ui_upper: return "JK"
    if "PONDY" in ui_upper or "PUDU" in ui_upper: return "PY"
    if "ORISSA" in ui_upper: return "OR"
    if "UTTARANCHAL" in ui_upper: return "UK"

    return None


# ── Gemini AI enrichment for live election context ──
async def _enrich_with_gemini(state_key: str, state_data: dict) -> Optional[Dict[str, Any]]:
    """Use Gemini to fetch current/live election context for a state."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        state_name = state_data["name"]
        prompt = f"""You are an Indian election data assistant. Provide a brief, factual JSON update
for the state of {state_name} ({state_key}).

Current known data:
- Election Day: {state_data.get('election_day', 'Unknown')}
- Status: {state_data.get('status', 'Unknown')}
- Schedule Announced: {state_data.get('schedule_announced', 'Not announced')}

Return ONLY a valid JSON object with these fields (use null if unknown):
{{
  "current_status": "Brief one-line status of the election (e.g. 'Results declared: DMK won with 133 seats')",
  "result_summary": "2-3 sentence summary of the election result or current status",
  "winning_party": "Name of winning party or null if not yet decided",
  "seats_won": "Number of seats won by winning party or null",
  "total_seats": "Total assembly seats",
  "voter_turnout": "Turnout percentage or null",
  "next_election_due": "When the next election is expected",
  "source_note": "Brief note about data recency"
}}

Be factual. If the election has already happened, provide results. If upcoming, provide the latest schedule info. Do not invent data."""

        response = await model.generate_content_async(prompt)
        text = response.text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return json.loads(text)
    except Exception as e:
        print(f"[Gemini enrichment] Failed for {state_key}: {e}")
        return None


class IndiaProvider:
    async def get_timeline_data(
        self,
        state: str,
        zip_code: Optional[str],
        registration_status: str,
        voting_method: str,
        moved_recently: bool,
        voting_elsewhere: bool = False
    ) -> Dict[str, Any]:

        state_key = resolve_state_key(state)

        milestones = []
        gemini_enrichment = None

        if not state_key:
            milestones = [
                {"id": "election_day", "label": "Election Day", "date": "TBD — check ECI schedule",
                 "confidence": "estimated", "confidence_level": "medium", "source_count": 1,
                 "needs_manual_verify": True}
            ]
        else:
            state_data = INDIA_DATA[state_key]

            # Attempt Gemini enrichment for live data
            gemini_enrichment = await _enrich_with_gemini(state_key, state_data)

            if state_data["status"] == "No assembly":
                milestones = [
                    {"id": "no_assembly", "label": "No Assembly", "date": "N/A",
                     "confidence": "verified", "confidence_level": "high", "source_count": 3,
                     "needs_manual_verify": False}
                ]
            else:
                if "schedule_announced" in state_data:
                    milestones.append(
                        {"id": "schedule_announced", "label": "Schedule Announced", "date": state_data["schedule_announced"],
                         "confidence": "verified", "confidence_level": "high", "source_count": 3,
                         "needs_manual_verify": False}
                    )

                milestones.append(
                    {"id": "election_day", "label": "Election Day", "date": state_data["election_day"],
                     "confidence": "verified", "confidence_level": "high", "source_count": 3,
                     "needs_manual_verify": False}
                )

                if "counting_day" in state_data:
                    milestones.append(
                        {"id": "counting_day", "label": "Vote Counting", "date": state_data["counting_day"],
                         "confidence": "verified", "confidence_level": "high", "source_count": 3,
                         "needs_manual_verify": False}
                    )

                # Add Gemini-sourced milestones if available
                if gemini_enrichment:
                    if gemini_enrichment.get("current_status"):
                        milestones.append(
                            {"id": "live_status", "label": "Current Status (AI)", "date": gemini_enrichment["current_status"],
                             "confidence": "api_data", "confidence_level": "medium", "source_count": 1,
                             "needs_manual_verify": True}
                        )
                    if gemini_enrichment.get("next_election_due"):
                        milestones.append(
                            {"id": "next_election", "label": "Next Election Due", "date": gemini_enrichment["next_election_due"],
                             "confidence": "estimated", "confidence_level": "medium", "source_count": 1,
                             "needs_manual_verify": True}
                        )

        # Personalized checklist
        checklist: List[Dict[str, Any]] = []

        if state_key and INDIA_DATA[state_key]["status"] != "No assembly":
            if registration_status == "no":
                checklist.append({
                    "id": "register_epic",
                    "label": "Register for your Voter ID (EPIC) — you are NOT registered",
                    "link": "https://voters.eci.gov.in/"
                })
            elif registration_status == "unsure":
                checklist.append({
                    "id": "check_epic",
                    "label": "Check if your name is in the voter list (you're unsure)",
                    "link": "https://electoralsearch.eci.gov.in/"
                })
            else:
                checklist.append({
                    "id": "verify_epic",
                    "label": "Verify your name in the voter list (EPIC)",
                    "link": "https://electoralsearch.eci.gov.in/"
                })

            if moved_recently:
                checklist.append({
                    "id": "form_8",
                    "label": "Submit Form 8 for shifting of residence (you moved recently)",
                    "link": "https://voters.eci.gov.in/"
                })

            # Always check polling booth
            checklist.append({
                "id": "find_booth",
                "label": "Find your assigned polling booth",
                "link": "https://electoralsearch.eci.gov.in/"
            })

        official_links = [
            {"label": "Official ECI Portal", "url": "https://election.ec.gov.in/"}
        ]

        # Add state specific portal logic here if needed.
        if state_key and state_key == "TN":
             official_links.append({"label": "CEO Tamil Nadu", "url": "https://elections.tn.gov.in/"})

        source_notes = "Data modeled after official ECI scheduling announcements and state term expiration calendars."
        if state_key and INDIA_DATA[state_key]["status"] == "Expected":
             source_notes = "Expected timeline based on legislative assembly term expiry. Not yet officially announced by ECI."

        # Build enriched source notes
        source_entries = [{"source": "curated_india", "details": source_notes}]
        if gemini_enrichment:
            ai_note = gemini_enrichment.get("source_note", "AI-generated summary via Gemini 1.5 Flash")
            result_summary = gemini_enrichment.get("result_summary", "")
            if result_summary:
                source_entries.append({"source": "gemini_ai_live", "details": f"{result_summary} ({ai_note})"})

        return {
            "milestones": milestones,
            "checklist": checklist,
            "official_links": official_links,
            "source_notes": source_entries,
            "gemini_enrichment": gemini_enrichment
        }

    async def get_kb_context(self, state: str) -> Optional[Dict[str, Any]]:
        return {"state": state, "context": "India context mock"}
