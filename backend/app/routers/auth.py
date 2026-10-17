"""Auth endpoints: Google Sign-In token exchange + current user."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_jwt, get_current_user, get_or_create_user, verify_google_token
from ..database import get_session
from ..models import User
from ..schemas import TokenResponse, UserResponse

router = APIRouter(tags=["auth"])


class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token from client-side Sign In With Google

@router.post("/auth/google")
async def google_auth(req: GoogleAuthRequest, session: AsyncSession = Depends(get_session)):
    """Exchange Google ID token for JWT. Create user if not exists."""
    try:
        google_data = await verify_google_token(req.credential)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

    user, created = await get_or_create_user(session, google_data)
    await session.commit()

    token = create_jwt(user.id, user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
        ),
    )


@router.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    """Get current user info from JWT."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )
