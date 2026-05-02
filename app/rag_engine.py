# app/rag_engine.py
import os
from typing import List

class RAGEngine:
    """Agentic RAG Engine for election knowledge."""
    def __init__(self, kb_path: str = "knowledge_base"):
        self.kb_path = kb_path
        self._load_kb()

    def _load_kb(self):
        self.kb_docs = {}
        if os.path.exists(self.kb_path):
            for file in os.listdir(self.kb_path):
                if file.endswith(".md"):
                    with open(os.path.join(self.kb_path, file), "r", encoding="utf-8") as f:
                        content = f.read()
                        self.kb_docs[file] = content

    def retrieve_context(self, topic_id: str, state: str, country: str = "US") -> str:
        """Simple retrieval logic matching keywords and filenames."""
        relevant_docs = []
        # Normalization
        topic_clean = topic_id.replace("_", "-").lower()
        state_lower = state.lower()
        
        for file, content in self.kb_docs.items():
            content_lower = content.lower()
            if topic_clean in file.lower() or topic_clean in content_lower or state_lower in content_lower:
                relevant_docs.append(content)
                
        if not relevant_docs:
            return "No specific rules found in knowledge base."
            
        return "\n\n".join(relevant_docs[:3])
