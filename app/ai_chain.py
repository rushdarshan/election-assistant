"""AI Provider fallback chain.

Fallback order:
1. In-memory cache (MD5-keyed, TTL-based)
2. Persistent MongoDB cache (if available)
3. Vertex AI (primary, if configured)
4. Direct Gemini API with key rotation (fallback)
5. Hardcoded responses (keyword-matched, US election content)

Tracks provider health, cooldowns, and response times.
"""

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_TTL = 3600  # 1 hour
MONGO_CACHE_TTL = 86400  # 24 hours for persistent cache


@dataclass
class ProviderStats:
    total_requests: int = 0
    cache_hits: int = 0
    mongo_cache_hits: int = 0
    successes: int = 0
    failures: int = 0
    fallback_used: int = 0
    avg_response_time: float = 0.0
    _response_times: list[float] = field(default_factory=list)

    def record_response_time(self, ms: float):
        self._response_times.append(ms)
        if len(self._response_times) > 10:
            self._response_times.pop(0)
        self.avg_response_time = sum(self._response_times) / len(self._response_times)


class GeminiKeyRotator:
    """Manages rotation of multiple Gemini API keys with cooldown."""

    def __init__(self):
        keys_raw = os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", ""))
        self._keys = [k.strip() for k in keys_raw.split(",") if k.strip()] if keys_raw else []
        self._cooldowns: dict[str, float] = {}
        self._current_index = 0
        logger.info(f"Gemini key rotator initialized with {len(self._keys)} key(s)")

    @property
    def has_keys(self) -> bool:
        return len(self._keys) > 0

    @property
    def current_key(self) -> Optional[str]:
        for _ in range(len(self._keys)):
            key = self._keys[self._current_index]
            if not self._is_key_on_cooldown(key):
                return key
            self._current_index = (self._current_index + 1) % len(self._keys)
        return self._keys[0] if self._keys else None

    def _is_key_on_cooldown(self, key: str) -> bool:
        cooldown_until = self._cooldowns.get(key, 0)
        if time.time() < cooldown_until:
            return True
        if cooldown_until > 0:
            del self._cooldowns[key]
        return False

    def mark_key_failed(self, key: Optional[str], seconds: int = 300):
        if key:
            self._cooldowns[key] = time.time() + seconds
            logger.warning(f"Gemini key {key[-6:]} marked on cooldown for {seconds}s")
            # Rotate to next key
            self._current_index = (self._current_index + 1) % len(self._keys)

    def rotate_key(self):
        """Manually rotate to the next key."""
        if self._keys:
            self._current_index = (self._current_index + 1) % len(self._keys)


class AIProviderChain:
    """Manages the AI provider fallback chain."""

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._cooldowns: dict[str, float] = {}
        self.stats = ProviderStats()
        self._key_rotator = GeminiKeyRotator()
        self._gemini_available = False
        self._gemini_models: list = []

        # Vertex AI (primary)
        self._vertex_available = False
        self._vertex_project = os.getenv("GOOGLE_PROJECT_ID")
        self._vertex_region = os.getenv("VERTEX_AI_REGION", "us-central1")
        if self._vertex_project:
            try:
                import google.cloud.aiplatform as aip
                aip.init(project=self._vertex_project, location=self._vertex_region)
                self._vertex_available = True
                logger.info("Vertex AI initialized (primary provider)")
            except Exception as e:
                logger.warning(f"Vertex AI unavailable: {e}")

        # Direct Gemini with key rotation (fallback)
        self._init_gemini()

        # MongoDB persistent cache (optional)
        self._mongo_db = None

    def _init_gemini(self):
        """Initialize Gemini API with key rotation support."""
        if self._key_rotator.has_keys:
            try:
                import google.generativeai as genai
                # Configure with first available key
                key = self._key_rotator.current_key
                if key:
                    genai.configure(api_key=key)
                    self._gemini_models.append(genai.GenerativeModel("gemini-1.5-flash"))
                    self._gemini_available = True
                    logger.info(f"Gemini API initialized with {len(self._key_rotator._keys)} key(s) for rotation")
            except Exception as e:
                logger.warning(f"Gemini API unavailable: {e}")

    def set_mongo_db(self, mongo_db):
        """Set MongoDB database reference for persistent cache."""
        self._mongo_db = mongo_db
        logger.info("MongoDB persistent cache enabled")

    async def _get_mongo_cached(self, key: str) -> Optional[dict]:
        """Check MongoDB persistent cache."""
        if not self._mongo_db:
            return None
        try:
            entry = await self._mongo_db.cache_entries.find_one({
                "key": key,
                "expires_at": {"$gt": time.time()},
            })
            if entry:
                return {
                    "response": entry["response"],
                    "provider": entry.get("provider", "mongo_cache"),
                    "response_time_ms": entry.get("response_time_ms", 0),
                }
        except Exception as e:
            logger.warning(f"MongoDB cache read failed: {e}")
        return None

    async def _set_mongo_cache(self, key: str, response: dict):
        """Store response in MongoDB persistent cache."""
        if not self._mongo_db:
            return
        try:
            doc = {
                "key": key,
                "response": response.get("response", response),
                "provider": response.get("provider", "mongo_cache"),
                "response_time_ms": response.get("response_time_ms", 0),
                "created_at": time.time(),
                "expires_at": time.time() + MONGO_CACHE_TTL,
            }
            await self._mongo_db.cache_entries.update_one(
                {"key": key},
                {"$set": doc},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"MongoDB cache write failed: {e}")

    def _cache_key(self, prompt: str, system_prompt: str = "") -> str:
        return hashlib.md5(f"{system_prompt}|{prompt}".encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[dict]:
        entry = self._cache.get(key)
        if entry and time.time() < entry["expires_at"]:
            return {
                "response": entry["response"],
                "provider": entry.get("provider", "cached"),
                "response_time_ms": entry.get("response_time_ms", 0),
            }
        if entry:
            del self._cache[key]
        return None

    def _set_cache(self, key: str, response: dict):
        self._cache[key] = {
            "response": response.get("response", response),
            "provider": response.get("provider", "cached"),
            "response_time_ms": response.get("response_time_ms", 0),
            "expires_at": time.time() + CACHE_TTL,
        }

    def _is_on_cooldown(self, provider: str) -> bool:
        cooldown_until = self._cooldowns.get(provider, 0)
        if time.time() < cooldown_until:
            return True
        if cooldown_until > 0:
            del self._cooldowns[provider]
        return False

    def _set_cooldown(self, provider: str, seconds: int = 60):
        self._cooldowns[provider] = time.time() + seconds

    def _clean_cache(self):
        now = time.time()
        expired = [k for k, v in self._cache.items() if v["expires_at"] < now]
        for k in expired:
            del self._cache[k]

    def get_response(
        self,
        prompt: str,
        system_prompt: str = "",
        response_mime_type: Optional[str] = None,
    ) -> dict:
        """Get AI response through the fallback chain (sync for backward compatibility)."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            # Already in async context, use sync fallback
            return self._get_response_sync(prompt, system_prompt, response_mime_type)
        else:
            return asyncio.run(self.get_response_async(prompt, system_prompt, response_mime_type))

    async def get_response_async(
        self,
        prompt: str,
        system_prompt: str = "",
        response_mime_type: Optional[str] = None,
    ) -> dict:
        """Get AI response through the fallback chain (async with MongoDB cache)."""
        self.stats.total_requests += 1

        # Step 1: Check in-memory cache
        cache_key = self._cache_key(prompt, system_prompt)
        cached = self._get_cached(cache_key)
        if cached:
            self.stats.cache_hits += 1
            return {**cached, "cached": True}

        # Step 2: Check MongoDB persistent cache
        mongo_cached = await self._get_mongo_cached(cache_key)
        if mongo_cached:
            self.stats.mongo_cache_hits += 1
            self._set_cache(cache_key, mongo_cached)
            return {**mongo_cached, "cached": True}

        # Step 3: Try Vertex AI
        if self._vertex_available and not self._is_on_cooldown("vertex"):
            try:
                start = time.time()
                response = self._call_vertex(prompt, system_prompt, response_mime_type)
                elapsed = (time.time() - start) * 1000
                self.stats.record_response_time(elapsed)
                self.stats.successes += 1
                result = {"response": response, "provider": "vertex_ai", "response_time_ms": elapsed}
                self._set_cache(cache_key, result)
                await self._set_mongo_cache(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"Vertex AI failed: {e}")
                self.stats.failures += 1
                self._set_cooldown("vertex", 120)

        # Step 4: Try Direct Gemini with key rotation
        if self._gemini_available and self._key_rotator.current_key:
            try:
                start = time.time()
                response = await self._call_gemini_async(prompt, system_prompt, response_mime_type)
                elapsed = (time.time() - start) * 1000
                self.stats.record_response_time(elapsed)
                self.stats.successes += 1
                result = {"response": response, "provider": "gemini_direct", "response_time_ms": elapsed}
                self._set_cache(cache_key, result)
                await self._set_mongo_cache(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"Gemini API failed: {e}")
                current_key = self._key_rotator.current_key
                self._key_rotator.mark_key_failed(current_key)
                self.stats.failures += 1
                self._set_cooldown("gemini", 60)

        # Step 5: Hardcoded fallback
        self.stats.fallback_used += 1
        logger.info("Using hardcoded fallback response")
        fallback_response = self._get_hardcoded_response(prompt)
        self._set_cache(cache_key, {"response": fallback_response, "provider": "hardcoded"})
        return {
            "response": fallback_response,
            "provider": "hardcoded",
            "response_time_ms": 0,
        }

    def _get_response_sync(
        self,
        prompt: str,
        system_prompt: str = "",
        response_mime_type: Optional[str] = None,
    ) -> dict:
        """Synchronous fallback for when we're already in an async context."""
        self.stats.total_requests += 1

        # Step 1: Check in-memory cache
        cache_key = self._cache_key(prompt, system_prompt)
        cached = self._get_cached(cache_key)
        if cached:
            self.stats.cache_hits += 1
            return {**cached, "cached": True}

        # Step 2: Try Vertex AI
        if self._vertex_available and not self._is_on_cooldown("vertex"):
            try:
                start = time.time()
                response = self._call_vertex(prompt, system_prompt, response_mime_type)
                elapsed = (time.time() - start) * 1000
                self.stats.record_response_time(elapsed)
                self.stats.successes += 1
                result = {"response": response, "provider": "vertex_ai", "response_time_ms": elapsed}
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"Vertex AI failed: {e}")
                self.stats.failures += 1
                self._set_cooldown("vertex", 120)

        # Step 3: Try Direct Gemini with key rotation
        if self._gemini_available and self._key_rotator.current_key:
            try:
                import google.generativeai as genai
                key = self._key_rotator.current_key
                genai.configure(api_key=key)
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_prompt or None,
                )
                config = genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1024,
                )
                if response_mime_type:
                    config.response_mime_type = response_mime_type
                start = time.time()
                response = model.generate_content(prompt, generation_config=config)
                elapsed = (time.time() - start) * 1000
                self.stats.record_response_time(elapsed)
                self.stats.successes += 1
                result = {"response": response.text, "provider": "gemini_direct", "response_time_ms": elapsed}
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"Gemini API failed: {e}")
                current_key = self._key_rotator.current_key
                self._key_rotator.mark_key_failed(current_key)
                self.stats.failures += 1
                self._set_cooldown("gemini", 60)

        # Step 4: Hardcoded fallback
        self.stats.fallback_used += 1
        logger.info("Using hardcoded fallback response")
        fallback_response = self._get_hardcoded_response(prompt)
        self._set_cache(cache_key, {"response": fallback_response, "provider": "hardcoded"})
        return {
            "response": fallback_response,
            "provider": "hardcoded",
            "response_time_ms": 0,
        }

    def _call_vertex(self, prompt: str, system_prompt: str, mime_type: Optional[str]) -> str:
        import google.cloud.aiplatform as aip
        from vertexai.generative_models import GenerativeModel, GenerationConfig

        model = GenerativeModel("gemini-1.5-flash", system_instruction=system_prompt or None)
        config_kwargs = {"temperature": 0.3, "max_output_tokens": 1024}
        if mime_type:
            config_kwargs["response_mime_type"] = mime_type

        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(**config_kwargs),
        )
        return response.text

    async def _call_gemini_async(self, prompt: str, system_prompt: str, mime_type: Optional[str]) -> str:
        import google.generativeai as genai

        key = self._key_rotator.current_key
        if not key:
            raise RuntimeError("No available Gemini API key")

        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt or None,
        )

        config = genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=1024,
        )
        if mime_type:
            config.response_mime_type = mime_type

        response = model.generate_content(prompt, generation_config=config)
        if not response.text:
            raise RuntimeError("Empty response from Gemini API")
        return response.text

    def _get_hardcoded_response(self, prompt: str) -> dict:
        prompt_lower = prompt.lower()

        fallbacks = {
            "registration": {
                "text": "To register to vote in the US, you must be a US citizen, meet your state's age requirement (usually 18 by Election Day), and meet your state's residency requirements. You can register online at vote.gov, by mail using the National Mail Voter Registration Form, or in person at your local election office. Check your state's specific deadline — many states require registration 15-30 days before an election.",
                "source": "vote.gov",
            },
            "voting": {
                "text": "On Election Day, bring a valid ID if your state requires one. Find your polling place at vote.gov or contact your local election office. Polls are typically open from early morning (6-7 AM) to evening (7-9 PM). If you're in line when polls close, you have the right to vote. If you encounter problems, call the Election Protection hotline at 1-866-OUR-VOTE.",
                "source": "vote.gov",
            },
            "polling": {
                "text": "Find your polling place by visiting vote.gov and entering your address, or contact your local election office. Your polling place may have changed since the last election, so verify before Election Day. Bring any required ID and be prepared for possible wait times.",
                "source": "vote.gov",
            },
            "deadline": {
                "text": "Voting deadlines vary by state. Generally, voter registration closes 15-30 days before an election, and mail ballot requests must be received several days before Election Day. Check your specific state's deadlines at vote.gov or your Secretary of State's website.",
                "source": "vote.gov",
            },
            "id": {
                "text": "Voter ID requirements vary by state. Some states require photo ID, some accept non-photo ID, and some have no ID requirement. If you don't have ID, you may be able to vote a provisional ballot. Check your state's requirements at vote.gov.",
                "source": "vote.gov",
            },
            "mail": {
                "text": "To vote by mail, you may need to request a mail ballot in advance (requirements vary by state). Some states automatically send mail ballots to all registered voters. Return your completed ballot by mail or at an official drop-off location before the deadline. Track your ballot if your state offers tracking.",
                "source": "vote.gov",
            },
        }

        for keyword, response in fallbacks.items():
            if keyword in prompt_lower:
                return response

        return {
            "text": "I can help with questions about voter registration, voting methods, polling places, deadlines, voter ID requirements, and mail-in voting. Please ask about any of these topics for detailed guidance based on your state.",
            "source": "vote.gov",
        }


# Singleton instance
ai_chain = AIProviderChain()
