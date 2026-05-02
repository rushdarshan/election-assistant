"""MongoDB integration for FastAPI.

Provides:
- Async MongoDB client via Motor
- Collection accessors
- Document models for User, ChatHistory, QuizResult, Checklist, QueryLog, CacheEntry
- Startup/shutdown lifecycle management
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# ── Configuration ──
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "election_assistant")

# ── Global client ──
client: Optional[AsyncIOMotorClient] = None
db: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo():
    """Create MongoDB connection."""
    global client, db
    client = AsyncIOMotorClient(MONGODB_URI, maxPoolSize=20, serverSelectionTimeoutMS=5000)
    db = client[MONGODB_DB]
    # Verify connection
    await client.admin.command("ping")
    logger.info(f"Connected to MongoDB: {MONGODB_DB}")
    await _ensure_indexes()


async def close_mongo():
    """Close MongoDB connection."""
    global client, db
    if client:
        client.close()
        client = None
        db = None
        logger.info("MongoDB connection closed")


async def _ensure_indexes():
    """Create indexes for performance."""
    if not db:
        return
    await db.users.create_index("email", unique=True)
    await db.users.create_index("auth_provider")
    await db.chat_history.create_index("user_id")
    await db.chat_history.create_index("session_id")
    await db.chat_history.create_index("created_at")
    await db.quiz_results.create_index("user_id")
    await db.quiz_results.create_index("created_at")
    await db.checklists.create_index("user_id")
    await db.query_logs.create_index("endpoint")
    await db.query_logs.create_index("created_at")
    await db.query_logs.create_index([("endpoint", 1), ("created_at", -1)])
    await db.cache_entries.create_index("key", unique=True)
    await db.cache_entries.create_index("expires_at")


# ── Document Models ──

def create_user_doc(
    email: str,
    name: str,
    auth_provider: str = "email",
    hashed_password: Optional[str] = None,
    firebase_uid: Optional[str] = None,
    state: str = "",
    country: str = "US",
) -> dict:
    """Create a new user document."""
    return {
        "email": email.lower().strip(),
        "name": name,
        "auth_provider": auth_provider,
        "hashed_password": hashed_password,
        "firebase_uid": firebase_uid,
        "state": state,
        "country": country,
        "registration_status": None,
        "voting_method": None,
        "readiness_score": 0,
        "last_login": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }


def create_chat_message_doc(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
    topic_id: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
) -> dict:
    """Create a chat message document."""
    return {
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "topic_id": topic_id,
        "country": country,
        "state": state,
        "created_at": datetime.now(timezone.utc),
    }


def create_quiz_result_doc(
    user_id: str,
    quiz_type: str,
    score: int,
    total: int,
    answers: list,
    state: Optional[str] = None,
    country: Optional[str] = None,
) -> dict:
    """Create a quiz result document."""
    return {
        "user_id": user_id,
        "quiz_type": quiz_type,
        "score": score,
        "total": total,
        "percentage": round((score / total) * 100, 1) if total > 0 else 0,
        "answers": answers,
        "state": state,
        "country": country,
        "created_at": datetime.now(timezone.utc),
    }


def create_checklist_doc(
    user_id: str,
    state: str,
    country: str,
    items: list,
) -> dict:
    """Create a checklist document."""
    return {
        "user_id": user_id,
        "state": state,
        "country": country,
        "items": items,
        "completed": [False] * len(items),
        "updated_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }


def create_query_log_doc(
    endpoint: str,
    method: str,
    ip_address: Optional[str] = None,
    user_id: Optional[str] = None,
    request_payload: Optional[dict] = None,
    status_code: int = 200,
    response_time_ms: float = 0.0,
    error: Optional[str] = None,
) -> dict:
    """Create a query log document."""
    return {
        "endpoint": endpoint,
        "method": method,
        "ip_address": ip_address,
        "user_id": user_id,
        "request_payload": request_payload,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "error": error,
        "created_at": datetime.now(timezone.utc),
    }


def create_cache_entry_doc(
    key: str,
    response: dict,
    provider: str,
    response_time_ms: float,
    ttl: int = 3600,
) -> dict:
    """Create a cache entry document."""
    now = datetime.now(timezone.utc).timestamp()
    return {
        "key": key,
        "response": response,
        "provider": provider,
        "response_time_ms": response_time_ms,
        "created_at": now,
        "expires_at": now + ttl,
    }
