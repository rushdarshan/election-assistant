"""JWT-based authentication for FastAPI.

Provides:
- Password hashing with bcrypt
- JWT token generation and verification
- FastAPI dependency for protected routes
- Auth router with register, login, me, and Google OAuth endpoints
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
import bcrypt
from slowapi import Limiter
from slowapi.util import get_remote_address

import uuid

limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

# ── Configuration ──
_raw_secret = os.getenv("JWT_SECRET", "")
if not _raw_secret and os.getenv("VERCEL"):
    raise RuntimeError("JWT_SECRET environment variable is required in production. Set it in Vercel project settings.")
JWT_SECRET = _raw_secret or os.urandom(32).hex()  # dev-only fallback
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_CLIENT_ID = os.getenv("FIREBASE_CLIENT_ID", "")

# ── User store (in-memory, MongoDB-backed if available) ──
_users: dict[str, dict] = {}
_email_to_id: dict[str, str] = {}


def _get_mongo_db():
    """Get MongoDB database if available."""
    try:
        from app.db import db as mongo_db
        return mongo_db
    except ImportError:
        return None


async def _save_user_to_mongo(user: dict):
    """Save user to MongoDB if available."""
    mongo_db = _get_mongo_db()
    if mongo_db:
        try:
            await mongo_db.users.update_one(
                {"email": user["email"]},
                {"$set": user},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Failed to save user to MongoDB: {e}")


async def _find_user_by_email(email: str) -> Optional[dict]:
    """Find user in MongoDB if available, fallback to memory."""
    mongo_db = _get_mongo_db()
    if mongo_db:
        try:
            doc = await mongo_db.users.find_one({"email": email.lower().strip()})
            if doc:
                doc.pop("_id", None)
                return doc
        except Exception as e:
            logger.warning(f"MongoDB user lookup failed: {e}")
    return _email_to_id.get(email) and _users.get(_email_to_id[email])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_jwt(user_id: str) -> str:
    import jwt
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_jwt(token: str) -> dict:
    import jwt
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["exp", "sub", "iat"]},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = _decode_jwt(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id or user_id not in _users:
            # Try MongoDB fallback
            mongo_db = _get_mongo_db()
            if mongo_db:
                doc = await mongo_db.users.find_one({"id": user_id})
                if doc:
                    doc.pop("_id", None)
                    _users[user_id] = doc
                    return doc
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return _users[user_id]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ── Request Models ──

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v.lower().strip()


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., description="Firebase ID token from client")


# ── Routes ──

@router.post("/register")
@limiter.limit("20/15minutes")
async def register(request: Request, req: RegisterRequest):
    email = req.email.lower().strip()
    if email in _email_to_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    _users[user_id] = {
        "id": user_id,
        "email": email,
        "name": req.name,
        "hashed_password": _hash_password(req.password),
        "auth_provider": "email",
        "state": "",
        "country": "US",
        "registration_status": None,
        "voting_method": None,
        "readiness_score": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _email_to_id[email] = user_id
    token = _create_jwt(user_id)
    await _save_user_to_mongo(_users[user_id])
    logger.info(f"User registered: {email}")
    return JSONResponse(content={
        "message": "Registration successful",
        "token": token,
        "user": {
            "id": user_id,
            "email": email,
            "name": req.name,
        },
    })


@router.post("/login")
@limiter.limit("20/15minutes")
async def login(request: Request, req: LoginRequest):
    email = req.email.lower().strip()
    user_id = _email_to_id.get(email)
    if not user_id or user_id not in _users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    user = _users[user_id]
    if not _verify_password(req.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = _create_jwt(user_id)
    logger.info(f"User logged in: {email}")
    return JSONResponse(content={
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user_id,
            "email": email,
            "name": user["name"],
        },
    })


@router.post("/google")
@limiter.limit("20/15minutes")
async def google_auth(request: Request, req: GoogleAuthRequest):
    """Authenticate with Firebase Google ID token.
    
    Verifies the Firebase ID token, extracts user info,
    and returns a JWT for the application.
    """
    id_token_str = req.id_token

    # Verify Firebase ID token
    user_info = _verify_firebase_token(id_token_str)

    email = user_info["email"].lower().strip()
    name = user_info.get("name", email.split("@")[0])
    firebase_uid = user_info.get("firebase_uid", email)

    # Check if user exists
    if email not in _email_to_id:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        _users[user_id] = {
            "id": user_id,
            "email": email,
            "name": name,
            "auth_provider": "google",
            "firebase_uid": firebase_uid,
            "state": "",
            "country": "US",
            "registration_status": None,
            "voting_method": None,
            "readiness_score": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _email_to_id[email] = user_id
        await _save_user_to_mongo(_users[user_id])
        logger.info(f"New user via Google OAuth: {email}")
    else:
        user_id = _email_to_id[email]
        # Update existing user's firebase_uid if not set
        if not _users[user_id].get("firebase_uid"):
            _users[user_id]["firebase_uid"] = firebase_uid
            await _save_user_to_mongo(_users[user_id])

    token = _create_jwt(user_id)
    return JSONResponse(content={
        "message": "Google authentication successful",
        "token": token,
        "user": {
            "id": user_id,
            "email": email,
            "name": _users[user_id]["name"],
            "auth_provider": "google",
        },
    })


def _verify_firebase_token(id_token_str: str) -> dict:
    """Verify Firebase ID token and extract user info.
    
    In production, use firebase-admin SDK:
        import firebase_admin
        from firebase_admin import auth
        decoded_token = auth.verify_id_token(id_token_str)
    
    For development, performs basic JWT decoding without crypto verification
    if FIREBASE_PROJECT_ID is not set.
    """
    try:
        if FIREBASE_PROJECT_ID:
            import firebase_admin
            from firebase_admin import auth as firebase_auth
            # Initialize Firebase Admin SDK if not already initialized
            try:
                firebase_admin.initialize_app()
            except ValueError:
                pass  # Already initialized
            decoded_token = firebase_auth.verify_id_token(id_token_str)
            return {
                "email": decoded_token.get("email", ""),
                "name": decoded_token.get("name", ""),
                "firebase_uid": decoded_token.get("uid", ""),
            }
        else:
            # Google auth is not configured — refuse rather than silently accept unverified tokens
            logger.error("Google OAuth endpoint called but FIREBASE_PROJECT_ID is not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google authentication is not configured on this server",
            )
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return JSONResponse(content={
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "state": current_user.get("state", ""),
        "country": current_user.get("country", "US"),
        "registration_status": current_user.get("registration_status"),
        "voting_method": current_user.get("voting_method"),
        "readiness_score": current_user.get("readiness_score", 0),
        "created_at": current_user.get("created_at"),
    })


@router.post("/profile/update")
async def update_profile(
    req: Request,
    current_user: dict = Depends(get_current_user),
):
    data = await req.json()
    user_id = current_user["id"]
    if "state" in data:
        _users[user_id]["state"] = data["state"]
    if "country" in data:
        _users[user_id]["country"] = data["country"]
    if "registration_status" in data:
        _users[user_id]["registration_status"] = data["registration_status"]
    if "voting_method" in data:
        _users[user_id]["voting_method"] = data["voting_method"]
    if "name" in data:
        _users[user_id]["name"] = data["name"]
    await _save_user_to_mongo(_users[user_id])
    return JSONResponse(content={
        "message": "Profile updated",
        "user": {
            "id": user_id,
            "email": _users[user_id]["email"],
            "name": _users[user_id]["name"],
            "state": _users[user_id]["state"],
            "country": _users[user_id]["country"],
        },
    })
