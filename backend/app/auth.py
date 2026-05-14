from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from datetime import datetime, timedelta
import os

from .database import get_session
from .models import User, Subscription, Tariff
from .schemas import AuthUser

# ---- Config ----
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "396621788757-qed19nu6sheoo8119slsbeqa2kor6436.apps.googleusercontent.com")
JWT_SECRET = os.getenv("JWT_SECRET", "isdelal-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 168  # 7 days

security = HTTPBearer()


def create_jwt(user_id: int, email: str) -> str:
    """Create a JWT token for the authenticated user."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def verify_google_token(google_token: str) -> dict:
    """Verify Google ID token and return user info."""
    google_request = google_requests.Request()
    id_info = id_token.verify_oauth2_token(
        google_token,
        google_request,
        GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=60,
    )
    return id_info


async def get_or_create_user(session: AsyncSession, google_data: dict) -> tuple[User, bool]:
    """Get existing user or create a new one from Google data. Returns (user, created)."""
    email = google_data.get("email")
    google_id = google_data.get("sub")

    # Try to find by Google ID
    stmt = select(User).where(User.google_id == google_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # Update info
        user.name = google_data.get("name", user.name)
        user.avatar_url = google_data.get("picture", user.avatar_url)
        await session.flush()
        return user, False

    # Try by email (user might have logged in before with same email)
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.google_id = google_id
        user.name = google_data.get("name", user.name)
        user.avatar_url = google_data.get("picture", user.avatar_url)
        await session.flush()
        return user, False

    # Create new user
    user = User(
        email=email,
        google_id=google_id,
        name=google_data.get("name"),
        avatar_url=google_data.get("picture"),
    )
    session.add(user)
    await session.flush()

    # Assign free tariff
    stmt = select(Tariff).where(Tariff.name == "free")
    result = await session.execute(stmt)
    free_tariff = result.scalar_one_or_none()

    if free_tariff:
        subscription = Subscription(
            user_id=user.id,
            tariff_id=free_tariff.id,
            active=True,
        )
        session.add(subscription)
        await session.flush()

    return user, True


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """FastAPI dependency: extract and validate the current user from JWT."""
    payload = decode_jwt(credentials.credentials)
    user_id = int(payload.get("sub"))

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user_or_none(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Like get_current_user but returns None instead of 401 (for optional auth)."""
    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None