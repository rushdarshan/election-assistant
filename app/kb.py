import os
import yaml
from typing import List, Dict, Any

KB_DIR = "knowledge_base"

def load_kb_docs() -> List[Dict[str, Any]]:
    docs = []
    if not os.path.exists(KB_DIR):
        return docs
        
    for filename in os.listdir(KB_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(KB_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple frontmatter parser
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                    docs.append({
                        "id": frontmatter.get("id"),
                        "country": frontmatter.get("country"),
                        "topics": frontmatter.get("topics", []),
                        "source_url": frontmatter.get("source_url"),
                        "body": body
                    })
    return docs

def retrieve_snippets(country: str, state: str, topic_id: str) -> List[Dict[str, Any]]:
    """Retrieve top snippets based on country and topic_id."""
    all_docs = load_kb_docs()
    
    # Filter
    filtered = []
    for doc in all_docs:
        if doc["country"].upper() == country.upper() and topic_id in doc["topics"]:
            filtered.append(doc)
            
    # Top 3-5 (In this simple case, just return all filtered)
    return filtered[:5]
