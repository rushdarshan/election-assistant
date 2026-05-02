import os
import httpx
import json
from typing import Optional, Dict, Any, List


class USProvider:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_CIVIC_API_KEY", "")
        self.base_url = "https://civicinfo.googleapis.com/civicinfo/v2"
        self.anchor_dates = self._load_anchor_dates()

    def _load_anchor_dates(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "anchor_dates.json")
        try:
            with open(path, "r") as f:
                return json.load(f).get("US", {})
        except Exception:
            return {}

    def _build_personalized_checklist(
        self,
        registration_status: str,
        voting_method: str,
        moved_recently: bool,
        voting_elsewhere: bool
    ) -> List[Dict[str, Any]]:
        """Build a checklist that actually adapts to user answers (Bug #20, #25)."""
        checklist: List[Dict[str, Any]] = []

        # Registration-aware items
        if registration_status == "no":
            checklist.append({
                "id": "register_now",
                "label": "Register to vote (you indicated you are NOT registered)",
                "link": "https://www.nass.org/can-i-vote/register-to-vote"
            })
        elif registration_status == "unsure":
            checklist.append({
                "id": "check_registration",
                "label": "Check your registration status (you're unsure)",
                "link": "https://www.nass.org/can-i-vote/voter-registration-status"
            })
        else:
            checklist.append({
                "id": "verify_registration",
                "label": "Confirm your registration is current",
                "link": "https://www.nass.org/can-i-vote/voter-registration-status"
            })

        # Voting-method-aware items
        if voting_method == "mail":
            checklist.append({
                "id": "request_ballot",
                "label": "Request your mail-in / absentee ballot",
                "link": "https://www.nass.org/can-i-vote/absentee-early-voting"
            })
            checklist.append({
                "id": "mail_deadline",
                "label": "Check your state's ballot return deadline",
                "link": "https://www.vote.org/absentee-voting-rules/"
            })
        elif voting_method == "early":
            checklist.append({
                "id": "early_dates",
                "label": "Find early voting dates & locations in your area",
                "link": "https://www.nass.org/can-i-vote/absentee-early-voting"
            })
        else:
            # election_day
            checklist.append({
                "id": "find_polling",
                "label": "Find your Election Day polling place",
                "link": "https://www.vote.org/polling-place-locator/"
            })

        # Moved recently
        if moved_recently:
            checklist.append({
                "id": "update_address",
                "label": "Update your voter registration address (you moved recently)",
                "link": "https://www.nass.org/can-i-vote/register-to-vote"
            })

        # Voting from elsewhere (student / military / overseas)
        if voting_elsewhere:
            checklist.append({
                "id": "voting_elsewhere",
                "label": "Apply for UOCAVA absentee ballot (military / overseas / student)",
                "link": "https://www.fvap.gov/"
            })

        # Always include ID check
        checklist.append({
            "id": "check_id",
            "label": "Check your state's voter ID requirements",
            "link": "https://www.vote.org/voter-id-laws/"
        })

        return checklist

    def _build_personalized_milestones(
        self,
        registration_status: str,
        voting_method: str,
        moved_recently: bool,
        api_milestones: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build milestones that adapt to user input (Bug #20)."""
        milestones = []

        # If we have API data, use it
        if api_milestones:
            return api_milestones

        # Fallback: generate personalized milestones based on input
        if registration_status in ("no", "unsure") or moved_recently:
            milestones.append({
                "id": "register_by",
                "label": "Register / Update Registration",
                "date": "Check state site",
                "confidence": "fallback",
                "confidence_level": "low",
                "source_count": 1,
                "needs_manual_verify": True
            })

        if voting_method == "mail":
            milestones.append({
                "id": "request_ballot",
                "label": "Request Mail-in Ballot by",
                "date": "Check state site",
                "confidence": "fallback",
                "confidence_level": "low",
                "source_count": 1,
                "needs_manual_verify": True
            })
            milestones.append({
                "id": "return_ballot",
                "label": "Return Ballot by",
                "date": "Check state site",
                "confidence": "fallback",
                "confidence_level": "low",
                "source_count": 1,
                "needs_manual_verify": True
            })
        elif voting_method == "early":
            milestones.append({
                "id": "early_start",
                "label": "Early Voting Opens",
                "date": "Check state site",
                "confidence": "fallback",
                "confidence_level": "low",
                "source_count": 1,
                "needs_manual_verify": True
            })
            milestones.append({
                "id": "early_end",
                "label": "Early Voting Ends",
                "date": "Check state site",
                "confidence": "fallback",
                "confidence_level": "low",
                "source_count": 1,
                "needs_manual_verify": True
            })

        # Always include Election Day
        milestones.append({
            "id": "election_day",
            "label": "Election Day",
            "date": "Check state site",
            "confidence": "fallback",
            "confidence_level": "low",
            "source_count": 1,
            "needs_manual_verify": True
        })

        return milestones

    async def get_timeline_data(
        self,
        state: str,
        zip_code: Optional[str],
        registration_status: str,
        voting_method: str,
        moved_recently: bool,
        voting_elsewhere: bool = False
    ) -> Dict[str, Any]:
        address = state
        if zip_code:
            address += f" {zip_code}"

        api_milestones = []
        official_links = []
        source_notes = []

        if self.api_key:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(
                        f"{self.base_url}/voterinfo",
                        params={"address": address, "key": self.api_key}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        elections = data.get("otherElections", []) + ([data.get("election")] if data.get("election") else [])
                        state_anchors = self.anchor_dates.get("states", {}).get(state, {})
                        for el in elections:
                            if el and "electionDay" in el:
                                date_str = el["electionDay"]
                                confidence = "api_data"

                                # Verification Layer (Failure Mode #1 Mitigation)
                                gen_election_anchor = self.anchor_dates.get("General Election")
                                if "General Election" in el.get("name", "") and gen_election_anchor:
                                    if date_str != gen_election_anchor:
                                        confidence = "mismatch"
                                        source_notes.append({
                                            "source": "verification_layer",
                                            "details": f"API reported {date_str} for General Election, but anchor date is {gen_election_anchor}. Flagging for manual review."
                                        })
                                    else:
                                        confidence = "verified"

                                source_count = 2 if confidence == "verified" else 1
                                api_milestones.append({
                                    "id": f"election_{el['id']}",
                                    "label": el["name"],
                                    "date": date_str,
                                    "confidence": confidence,
                                    "confidence_level": "high" if confidence == "verified" else "medium",
                                    "source_count": source_count,
                                    "needs_manual_verify": confidence != "verified"
                                })

                        state_info_list = data.get("state", [])
                        if state_info_list:
                            state_node = state_info_list[0]

                            # 1. Check for Local Jurisdiction (County/City)
                            local_jurisdiction = state_node.get("local_jurisdiction", {})
                            local_admin = local_jurisdiction.get("electionAdministrationBody", {})
                            state_admin = state_node.get("electionAdministrationBody", {})

                            local_name = local_jurisdiction.get("name", "Local")

                            def is_safe_url(url: str) -> bool:
                                if not url: return False
                                # Mitigating "Local Hijack" by whitelisting trusted domains
                                return any(ext in url.lower() for ext in [".gov", ".org", ".us"])

                            # Registration URL (usually state level, but use local if available)
                            reg_url = local_admin.get("electionRegistrationUrl") or state_admin.get("electionRegistrationUrl")
                            if reg_url and is_safe_url(reg_url):
                                official_links.append({"label": "Voter Registration", "url": reg_url})

                            # Election Info URL (prioritize local)
                            if "electionInfoUrl" in local_admin and is_safe_url(local_admin["electionInfoUrl"]):
                                official_links.append({"label": f"{local_name} Election Info", "url": local_admin["electionInfoUrl"]})
                            elif "electionInfoUrl" in state_admin and is_safe_url(state_admin["electionInfoUrl"]):
                                official_links.append({"label": "State Election Info", "url": state_admin["electionInfoUrl"]})

                            # Absentee Voting URL (prioritize local)
                            if "absenteeVotingInfoUrl" in local_admin and is_safe_url(local_admin["absenteeVotingInfoUrl"]):
                                official_links.append({"label": f"{local_name} Absentee Voting", "url": local_admin["absenteeVotingInfoUrl"]})
                            elif "absenteeVotingInfoUrl" in state_admin and is_safe_url(state_admin["absenteeVotingInfoUrl"]):
                                official_links.append({"label": "State Absentee Voting", "url": state_admin["absenteeVotingInfoUrl"]})

                        source_notes.append({"source": "google_civic", "details": "Data retrieved from Google Civic Information API."})
                except Exception as e:
                    source_notes.append({"source": "google_civic_error", "details": str(e)})

        # Build personalized milestones (Bug #20)
        milestones = self._build_personalized_milestones(
            registration_status=registration_status,
            voting_method=voting_method,
            moved_recently=moved_recently,
            api_milestones=api_milestones
        )

        if not official_links:
            official_links = [
                {"label": "Find your local election office", "url": "https://www.usvotefoundation.org/election-offices"}
            ]
        if not source_notes:
            source_notes = [{"source": "fallback", "details": "Using fallback dates — verify with state election office."}]
        else:
            if not api_milestones:
                source_notes.append({"source": "fallback", "details": "Using fallback dates — verify with state election office."})

        # Build personalized checklist (Bug #20, #25)
        checklist = self._build_personalized_checklist(
            registration_status=registration_status,
            voting_method=voting_method,
            moved_recently=moved_recently,
            voting_elsewhere=voting_elsewhere
        )

        return {
            "milestones": milestones,
            "checklist": checklist,
            "official_links": official_links,
            "source_notes": source_notes
        }

    async def get_kb_context(self, state: str) -> Optional[Dict[str, Any]]:
        return {"state": state, "context": "US context mock"}
