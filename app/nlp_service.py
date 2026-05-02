"""Google Cloud Natural Language service.

Provides sentiment analysis and entity extraction for user queries.
Runs non-blocking so NLP failures never affect the main response.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NLPService:
    """Google Cloud Natural Language wrapper with graceful fallback."""

    def __init__(self):
        self._client = None
        self._api_key = os.getenv("GOOGLE_NLP_API_KEY")
        self._available = False

        if self._api_key:
            try:
                from google.cloud import language_v1
                self._client = language_v1.LanguageServiceClient(
                    client_options={"api_key": self._api_key}
                )
                self._available = True
                logger.info("Google Cloud Natural Language initialized")
            except Exception as e:
                logger.warning(f"Google Cloud Natural Language unavailable: {e}")
                self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def analyze_sentiment(self, text: str) -> dict:
        """Analyze sentiment of text.

        Returns:
            dict with 'score' (-1.0 to 1.0), 'magnitude' (0.0+), and 'label'
        """
        if not self._available:
            return {"score": 0.0, "magnitude": 0.0, "label": "neutral"}

        try:
            from google.cloud import language_v1
            document = language_v1.Document(
                content=text,
                type_=language_v1.Document.Type.PLAIN_TEXT,
            )
            response = self._client.analyze_sentiment(request={"document": document})
            sentiment = response.document_sentiment

            score = sentiment.score
            magnitude = sentiment.magnitude

            if score > 0.25:
                label = "positive"
            elif score < -0.25:
                label = "negative"
            else:
                label = "neutral"

            return {"score": score, "magnitude": magnitude, "label": label}
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {"score": 0.0, "magnitude": 0.0, "label": "neutral"}

    def analyze_entities(self, text: str) -> list[dict]:
        """Extract entities from text.

        Returns list of dicts with 'name', 'type', 'salience', and 'mentions'.
        """
        if not self._available:
            return []

        try:
            from google.cloud import language_v1
            document = language_v1.Document(
                content=text,
                type_=language_v1.Document.Type.PLAIN_TEXT,
            )
            response = self._client.analyze_entities(request={"document": document})
            entities = []
            for entity in response.entities:
                entities.append({
                    "name": entity.name,
                    "type": language_v1.Entity.Type(entity.type_).name,
                    "salience": entity.salience,
                    "mentions": len(entity.mentions),
                })
            return entities
        except Exception as e:
            logger.error(f"Entity analysis failed: {e}")
            return []

    def analyze_query(self, text: str) -> dict:
        """Run full NLP analysis on a user query (sentiment + entities).

        Designed to be called as a non-blocking fire-and-forget operation.
        """
        sentiment = self.analyze_sentiment(text)
        entities = self.analyze_entities(text)
        return {
            "sentiment": sentiment,
            "entities": entities,
        }


# Singleton instance
nlp_service = NLPService()
