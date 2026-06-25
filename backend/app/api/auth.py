"""
LinkedIn OAuth2 — Login with LinkedIn.
Flow:
  1. GET /api/auth/linkedin          → redirect to LinkedIn
  2. LinkedIn redirects to /api/auth/linkedin/callback?code=...
  3. Backend exchanges code → access_token → fetches profile
  4. Creates/updates User in DB, issues JWT
  5. Redirects to frontend with token
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.core.auth import create_access_token
from app.models.base import User
import uuid

router = APIRouter()

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"


@router.get("/linkedin")
async def linkedin_login():
    """Redirect user to LinkedIn OAuth consent page."""
    if not settings.linkedin_client_id:
        raise HTTPException(503, "LinkedIn OAuth not configured. Set LINKEDIN_CLIENT_ID.")
    params = (
        f"?response_type=code"
        f"&client_id={settings.linkedin_client_id}"
        f"&redirect_uri={settings.linkedin_redirect_uri}"
        f"&scope=openid%20profile%20email"
    )
    return RedirectResponse(LINKEDIN_AUTH_URL + params)


@router.get("/linkedin/callback")
async def linkedin_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Exchange LinkedIn auth code for user profile, create/update user, return JWT."""
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.linkedin_redirect_uri,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(400, "Failed to exchange LinkedIn code")

        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        # Fetch LinkedIn profile (OpenID Connect userinfo)
        profile_resp = await client.get(
            LINKEDIN_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_resp.status_code != 200:
            raise HTTPException(400, "Failed to fetch LinkedIn profile")

        profile = profile_resp.json()

    linkedin_id = profile.get("sub")
    email = profile.get("email", "")
    name = profile.get("name", "")
    avatar = profile.get("picture", "")

    # Find or create user
    result = await db.execute(select(User).where(User.linkedin_id == linkedin_id))
    user = result.scalar_one_or_none()

    if not user:
        # Try to find by email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user:
        user.linkedin_id = linkedin_id
        user.linkedin_access_token = access_token
        user.name = name
        user.avatar_url = avatar
    else:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            linkedin_id=linkedin_id,
            linkedin_access_token=access_token,
            avatar_url=avatar,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    jwt_token = create_access_token(user.id, user.email)
    # Redirect to frontend with token in query param (frontend stores it in localStorage)
    return RedirectResponse(f"{settings.app_url}?token={jwt_token}")


@router.get("/me")
async def get_me(token: str, db: AsyncSession = Depends(get_db)):
    """Return current user profile from JWT token."""
    from app.core.auth import decode_token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    user = (await db.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "linkedin_profile_url": user.linkedin_profile_url,
        "email_notifications": user.email_notifications,
    }
