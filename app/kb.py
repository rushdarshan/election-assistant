import os
import re
import yaml
from typing import List, Dict, Any, Optional

KB_DIR = "knowledge_base"

# Topic-to-keyword mapping for chatbot retrieval
TOPIC_KEYWORDS = {
    "registration": ["register", "registration", "signup", "sign up", "enroll", "enrollment"],
    "eligibility": ["eligible", "eligibility", "qualify", "qualification", "citizen", "age requirement"],
    "id": ["id", "identification", "driver license", "photo id", "voter id", "identification requirement"],
    "polling": ["polling place", "poll location", "where to vote", "polling station", "precinct"],
    "mail": ["mail", "mail-in", "mail ballot", "absentee", "postal", "drop off", "drop-off"],
    "deadline": ["deadline", "due date", "cutoff", "closing date", "registration deadline"],
    "evm": ["evm", "voting machine", "electronic voting", "machine voting"],
    "vvpat": ["vvpat", "paper trail", "voter verified", "paper record"],
    "provisional": ["provisional ballot", "provisional", "challenge", "disputed"],
    "early_voting": ["early voting", "early vote", "vote early"],
    "absentee": ["absentee voting", "absentee ballot", "absentee"],
    "deadlines": ["deadline", "when is the deadline", "last date"],
}


def _load_single_doc(filepath: str) -> Optional[Dict[str, Any]]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return {
                "id": frontmatter.get("id"),
                "country": frontmatter.get("country"),
                "topics": frontmatter.get("topics", []),
                "source_url": frontmatter.get("source_url"),
                "body": body,
            }
    return None


def load_kb_docs() -> List[Dict[str, Any]]:
    docs = []
    if not os.path.exists(KB_DIR):
        return docs

    for filename in os.listdir(KB_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(KB_DIR, filename)
            doc = _load_single_doc(filepath)
            if doc:
                docs.append(doc)
    return docs


def retrieve_snippets(country: str, state: str, topic_id: str) -> List[Dict[str, Any]]:
    """Retrieve top snippets based on country and topic_id."""
    all_docs = load_kb_docs()

    filtered = []
    for doc in all_docs:
        if doc.get("country", "").upper() == country.upper() and topic_id in doc.get("topics", []):
            filtered.append(doc)

    return filtered[:5]


def retrieve_by_keywords(query: str, country: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve KB snippets matching keywords in a user query."""
    all_docs = load_kb_docs()
    query_lower = query.lower()

    matched_topics = set()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            matched_topics.add(topic)

    if not matched_topics:
        return []

    scored = []
    for doc in all_docs:
        if country and doc.get("country", "").upper() != country.upper():
            continue
        doc_topics = set(doc.get("topics", []))
        overlap = len(doc_topics & matched_topics)
        if overlap > 0:
            scored.append((overlap, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:5]]


def build_kb_context(query: str, country: Optional[str] = None) -> Optional[str]:
    """Build a context string from KB for injection into AI prompts."""
    snippets = retrieve_by_keywords(query, country)
    if not snippets:
        return None

    context_parts = []
    for snippet in snippets:
        source = snippet.get("source_url", "N/A")
        body = snippet.get("body", "")
        context_parts.append(f"[Source: {source}]\n{body}")

    return "\n\n---\n\n".join(context_parts)
