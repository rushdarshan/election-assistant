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


# State-specific official links for scenario guidance
STATE_ELECTION_LINKS = {
    "AL": "https://www.sos.alabama.gov/elections",
    "AK": "https://www.elections.alaska.gov/",
    "AZ": "https://azsos.gov/elections",
    "AR": "https://www.voter-view.ar.gov/",
    "CA": "https://www.sos.ca.gov/elections/",
    "CO": "https://www.sos.state.co.us/pubs/elections/",
    "CT": "https://portal.ct.gov/sots/voter-registration",
    "DE": "https://elections.delaware.gov/",
    "FL": "https://dos.myflorida.com/hes/",
    "GA": "https://sos.ga.gov/index.php/elections",
    "HI": "https://elections.hawaii.gov/",
    "ID": "https://voteid.idaho.gov/",
    "IL": "https://www.elections.il.gov/",
    "IN": "https://www.in.gov/sos/elections/",
    "IA": "https://sos.iowa.gov/elections/",
    "KS": "https://www.sos.ks.gov/elections/",
    "KY": "https://elect.ky.gov/",
    "LA": "https://www.sos.la.gov/ElectionsAndVoting/",
    "ME": "https://www.maine.gov/sos/cec/elec/",
    "MD": "https://elections.maryland.gov/",
    "MA": "https://www.sec.state.ma.us/ele/",
    "MI": "https://www.michigan.gov/sos/elections",
    "MN": "https://www.sos.state.mn.us/elections-voting/",
    "MS": "https://www.sos.ms.gov/elections/",
    "MO": "https://www.sos.mo.gov/elections/",
    "MT": "https://sosmt.gov/elections/",
    "NE": "https://sos.nebraska.gov/elections",
    "NV": "https://www.nvsos.gov/sos/elections",
    "NH": "https://www.sos.nh.gov/elections/",
    "NJ": "https://www.nj.gov/state/elections/",
    "NM": "https://www.sos.nm.gov/voting-elections/",
    "NY": "https://www.elections.ny.gov/",
    "NC": "https://www.ncsbe.gov/",
    "ND": "https://www.sos.nd.gov/elections/",
    "OH": "https://www.ohiosos.gov/elections/",
    "OK": "https://elections.ok.gov/",
    "OR": "https://sos.oregon.gov/elections/",
    "PA": "https://www.dos.pa.gov/VotingElections/",
    "RI": "https://vote.sos.ri.gov/",
    "SC": "https://scvotes.gov/",
    "SD": "https://sdsos.gov/elections-voting/",
    "TN": "https://tnsos.gov/elections/",
    "TX": "https://www.sos.state.tx.us/elections/",
    "UT": "https://vote.utah.gov/",
    "VT": "https://sos.vermont.gov/elections/",
    "VA": "https://www.elections.virginia.gov/",
    "WA": "https://www.sos.wa.gov/elections/",
    "WV": "https://sos.wv.gov/elections/",
    "WI": "https://elections.wi.gov/",
    "WY": "https://sos.wyo.gov/Elections/",
    "DC": "https://dcboe.org/",
}

FALLBACK_SCENARIOS = {
    "lost_voter_id": {
        "scenario_id": "lost_voter_id",
        "title": "Lost Voter ID Card",
        "description": "If you lost your voter registration card, don't worry — you can still vote. Most states don't require the physical card to vote, but you may need an alternate form of ID. Check your state's ID requirements at your Secretary of State website.",
        "steps": [
            {"number": 1, "action": "Verify your registration status online", "details": "Visit your state's election website or use vote.gov to confirm you're still registered. You'll need your name, address, and date of birth.", "link": "https://www.vote.gov/"},
            {"number": 2, "action": "Check your state's voter ID requirements", "details": "Some states require photo ID at the polls, while others accept non-photo ID or have no ID requirement. If you lack acceptable ID, ask about provisional ballots.", "link": None},
            {"number": 3, "action": "Request a replacement card (optional)", "details": "Contact your local election office to request a replacement voter registration card. This is not required to vote but can be helpful.", "link": None},
            {"number": 4, "action": "Bring alternate ID to the polls", "details": "Acceptable alternatives may include a driver's license, passport, utility bill, bank statement, or government check. Check your state's specific requirements.", "link": None},
        ],
        "documents_needed": ["Alternate photo ID (driver's license, passport)", "Proof of address (utility bill, bank statement)"],
        "estimated_time": "Immediate — you can still vote on Election Day",
        "official_links": [
            {"label": "Find your state election office", "url": "https://www.usa.gov/election-office"},
            {"label": "Election Protection Hotline: 1-866-OUR-VOTE", "url": "https://866ourvote.org"},
        ],
        "next_action": "Verify your registration at vote.gov and check your state's voter ID requirements",
    },
    "moved_wrong_precinct": {
        "scenario_id": "moved_wrong_precinct",
        "title": "Moved to a New Address",
        "description": "If you moved, you must update your voter registration to your new address. Deadlines vary by state — some allow online updates up to Election Day, while others require changes 15-30 days before.",
        "steps": [
            {"number": 1, "action": "Update your voter registration immediately", "details": "Use vote.gov or your state's online voter registration portal to update your address. You'll need your driver's license or state ID number.", "link": "https://www.vote.gov/"},
            {"number": 2, "action": "Check your new polling location", "details": "After updating, verify your new polling place through your state's voter lookup tool. Your precinct may have changed.", "link": None},
            {"number": 3, "action": "If you moved within the same county", "details": "Many states allow same-day address updates at your new polling place. Contact your local election office to confirm.", "link": None},
            {"number": 4, "action": "If the deadline has passed", "details": "You may still be able to vote at your old precinct or cast a provisional ballot at your new one. Contact your election office immediately.", "link": None},
        ],
        "documents_needed": ["Proof of new address (lease, utility bill)", "Photo ID"],
        "estimated_time": "Online update takes 10-15 minutes; processing varies by state (1-30 days)",
        "official_links": [
            {"label": "Update your registration at vote.gov", "url": "https://www.vote.gov/"},
            {"label": "Find your state election office", "url": "https://www.usa.gov/election-office"},
            {"label": "Election Protection Hotline: 1-866-OUR-VOTE", "url": "https://866ourvote.org"},
        ],
        "next_action": "Update your voter registration at vote.gov immediately",
    },
    "name_mismatch": {
        "scenario_id": "name_mismatch",
        "title": "Name Mismatch on Voter Roll",
        "description": "If your name doesn't match the voter registration list, you may still be able to vote. Bring documentation showing the name change (marriage certificate, court order) and ask for a provisional ballot if needed.",
        "steps": [
            {"number": 1, "action": "Don't leave — ask to speak with the poll worker supervisor", "details": "Poll workers can often resolve minor name discrepancies. Your registration may be under a previous name or contain a typo.", "link": None},
            {"number": 2, "action": "Provide documentation of the name change", "details": "Bring a marriage certificate, court order, or updated ID that links your current name to your registered name.", "link": None},
            {"number": 3, "action": "Request a provisional ballot if unresolved", "details": "If your identity cannot be verified on the spot, you have the right to cast a provisional ballot. Your eligibility will be verified after Election Day.", "link": None},
            {"number": 4, "action": "Follow up on your provisional ballot", "details": "Contact your local election office within a few days after the election to confirm your provisional ballot was counted.", "link": None},
        ],
        "documents_needed": ["Marriage certificate or court order", "Photo ID with current name", "Any mail from the election office"],
        "estimated_time": "Resolved at polling place, or provisional ballot counted within 10-14 days",
        "official_links": [
            {"label": "Election Protection Hotline: 1-866-OUR-VOTE", "url": "https://866ourvote.org"},
            {"label": "Find your state election office", "url": "https://www.usa.gov/election-office"},
        ],
        "next_action": "Bring documentation of your name change to the polls and ask for a poll worker supervisor",
    },
    "missed_deadline": {
        "scenario_id": "missed_deadline",
        "title": "Missed Registration Deadline",
        "description": "If you missed your state's voter registration deadline, you may still have options. Some states offer Same-Day Registration (SDR), and others allow provisional voting. Check your state's specific rules.",
        "steps": [
            {"number": 1, "action": "Check if your state offers Same-Day Registration", "details": "As of 2024, 21 states and DC allow voters to register and vote on the same day, either during early voting or on Election Day.", "link": "https://www.ncsl.org/elections-and-campaigns/same-day-registration"},
            {"number": 2, "action": "If SDR is available, bring proof of residency", "details": "You'll typically need a driver's license, state ID, or utility bill showing your current address. Go to your polling place or an early voting site.", "link": None},
            {"number": 3, "action": "If your state doesn't offer SDR", "details": "You may be able to cast a provisional ballot, but rules vary widely. Contact your state election office to explore options.", "link": None},
            {"number": 4, "action": "Register now for the next election", "details": "Don't wait — register today so you're ready for the next election cycle. It takes less than 10 minutes at vote.gov.", "link": "https://www.vote.gov/"},
        ],
        "documents_needed": ["Proof of residency (utility bill, lease, bank statement)", "Photo ID"],
        "estimated_time": "Same-Day Registration takes 15-30 minutes at the polling place",
        "official_links": [
            {"label": "Same-Day Registration by state (NCSL)", "url": "https://www.ncsl.org/elections-and-campaigns/same-day-registration"},
            {"label": "Register for next election at vote.gov", "url": "https://www.vote.gov/"},
            {"label": "Election Protection Hotline: 1-866-OUR-VOTE", "url": "https://866ourvote.org"},
        ],
        "next_action": "Check if your state offers Same-Day Registration at the NCSL link above",
    },
    "no_id_at_polling": {
        "scenario_id": "no_id_at_polling",
        "title": "No Acceptable ID at Polling Place",
        "description": "If you arrive at the polls without acceptable ID, don't leave. You may be able to use alternative identification, have your identity vouched for, or cast a provisional ballot.",
        "steps": [
            {"number": 1, "action": "Ask the poll worker about alternative ID options", "details": "Many states accept non-photo ID such as a utility bill, bank statement, government check, or paycheck — even if their law says 'photo ID.'", "link": None},
            {"number": 2, "action": "If another voter can vouch for you", "details": "Some states allow another registered voter from your precinct to sign an affidavit confirming your identity.", "link": None},
            {"number": 3, "action": "Request a provisional ballot", "details": "If no ID alternative works, you have the right to cast a provisional ballot. Election officials will verify your identity after Election Day.", "link": None},
            {"number": 4, "action": "Call the Election Protection Hotline for help", "details": "If you're told you can't vote without ID, call 1-866-OUR-VOTE (1-866-687-8683) for immediate nonpartisan legal assistance.", "link": "https://866ourvote.org"},
        ],
        "documents_needed": ["Any document with your name and address", "Phone to call Election Protection Hotline"],
        "estimated_time": "Provisional ballot counted within 10-14 days after election",
        "official_links": [
            {"label": "Election Protection Hotline: 1-866-OUR-VOTE", "url": "https://866ourvote.org"},
            {"label": "Voter ID requirements by state (NCSL)", "url": "https://www.ncsl.org/elections-and-campaigns/voter-id"},
        ],
        "next_action": "Ask the poll worker about alternative ID options — don't leave without voting",
    },
    "lost_mail_ballot": {
        "scenario_id": "lost_mail_ballot",
        "title": "Mail Ballot Not Received or Lost",
        "description": "If your mail ballot never arrived or was lost, contact your local election office immediately. Most states allow you to request a replacement ballot or vote provisionally.",
        "steps": [
            {"number": 1, "action": "Contact your local election office immediately", "details": "Call or visit your county election office to report the missing ballot. They can check if it was mailed, returned, or cancelled.", "link": None},
            {"number": 2, "action": "Request a replacement mail ballot", "details": "If there's still time before the deadline, most states will issue a replacement ballot. You may need to sign a form confirming the original was not voted.", "link": None},
            {"number": 3, "action": "If the deadline has passed, vote in person", "details": "You may need to vote provisionally at your polling place. Your original mail ballot must not have been counted for your provisional ballot to be valid.", "link": None},
            {"number": 4, "action": "Track your ballot status", "details": "Many states offer online ballot tracking tools. Check your state's election website to see the status of your ballot.", "link": "https://www.vote.gov/"},
        ],
        "documents_needed": ["Photo ID", "Proof of address"],
        "estimated_time": "Replacement ballot processing: 1-3 business days; must be received by your state's deadline",
        "official_links": [
            {"label": "Find your local election office", "url": "https://www.usa.gov/election-office"},
            {"label": "Track your mail ballot", "url": "https://www.vote.gov/"},
            {"label": "Election Protection Hotline: 1-866-OUR-VOTE", "url": "https://866ourvote.org"},
        ],
        "next_action": "Contact your local election office immediately to report the lost ballot",
    },
    "provisional_ballot": {
        "scenario_id": "provisional_ballot",
        "title": "Provisional Ballot Process",
        "description": "A provisional ballot is used when there's a question about your eligibility. Your vote is counted after election officials verify your eligibility. You have the right to cast one if your name isn't on the voter roll or if you lack required ID.",
        "steps": [
            {"number": 1, "action": "Ask for a provisional ballot at your polling place", "details": "Under the Help America Vote Act (HAVA), you have the right to cast a provisional ballot if your eligibility is questioned.", "link": "https://www.eac.gov/voting/help-americans-vote-act"},
            {"number": 2, "action": "Complete the provisional ballot affidavit", "details": "You'll be asked to provide identifying information and sign a statement confirming your eligibility. Follow the poll worker's instructions carefully.", "link": None},
            {"number": 3, "action": "Get your provisional ballot receipt", "details": "You should receive a receipt or tracking number for your provisional ballot. Keep this — you'll need it to check if your vote was counted.", "link": None},
            {"number": 4, "action": "Follow up after Election Day", "details": "Contact your local election office within 1-2 weeks to confirm whether your provisional ballot was counted. If not, ask why and what you can do.", "link": None},
        ],
        "documents_needed": ["Photo ID (if available)", "Proof of address", "Any voter registration confirmation"],
        "estimated_time": "Provisional ballots verified and counted within 10-14 days after the election",
        "official_links": [
            {"label": "Help America Vote Act (EAC)", "url": "https://www.eac.gov/voting/help-americans-vote-act"},
            {"label": "Find your local election office", "url": "https://www.usa.gov/election-office"},
            {"label": "Election Protection Hotline: 1-866-OUR-VOTE", "url": "https://866ourvote.org"},
        ],
        "next_action": "Ask for a provisional ballot at your polling place — you have the right to cast one",
    },
    "accessibility_accommodations": {
        "scenario_id": "accessibility_accommodations",
        "title": "Accessibility Accommodations",
        "description": "Federal law requires polling places to be accessible to voters with disabilities. You have the right to curbside voting, assistance from a poll worker or person of your choice, and accessible voting machines.",
        "steps": [
            {"number": 1, "action": "Know your rights under the ADA and HAVA", "details": "The Americans with Disabilities Act (ADA) and Help America Vote Act (HAVA) guarantee accessible voting. Every polling place must have at least one accessible voting machine.", "link": "https://www.ada.gov/topics/voting/"},
            {"number": 2, "action": "Request accommodations in advance", "details": "Contact your local election office before Election Day to request specific accommodations such as curbside voting, homebound voting, or a specific type of accessible machine.", "link": None},
            {"number": 3, "action": "Bring a person to assist you", "details": "You have the right to bring someone to help you vote (except your employer or union representative). The poll worker can also assist you upon request.", "link": None},
            {"number": 4, "action": "If your polling place is not accessible", "details": "Report the issue to the Election Protection Hotline at 1-866-OUR-VOTE. You may be redirected to an accessible location or offered accommodations on-site.", "link": "https://866ourvote.org"},
        ],
        "documents_needed": ["Photo ID (if required by your state)", "List of accommodations needed"],
        "estimated_time": "Accommodations arranged in advance; curbside voting available on Election Day",
        "official_links": [
            {"label": "ADA Voting Access", "url": "https://www.ada.gov/topics/voting/"},
            {"label": "Accessible voting (EAC)", "url": "https://www.eac.gov/voters/accessibility"},
            {"label": "Election Protection Hotline: 1-866-OUR-VOTE", "url": "https://866ourvote.org"},
        ],
        "next_action": "Contact your local election office to request accommodations before Election Day",
    },
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
