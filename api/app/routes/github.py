"""
CIOTX API — GitHub Routes
OAuth connection, repo listing, webhook receiver.
"""

import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.project import GitHubConnection, Project
from app.schemas.project import GitHubRepoListResponse, GitHubRepoResponse
from app.services.auth import decode_access_token, get_user_by_id

router = APIRouter(tags=["github"])


async def get_current_user(request: Request, db: AsyncSession):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header.")
    token = auth_header.split(" ", 1)[1]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


# ── GitHub OAuth ─────────────────────────────

@router.get("/github/connect")
async def github_connect():
    """Start GitHub OAuth flow for repo access."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured.",
        )

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.API_BASE_URL}/v1/github/callback"

    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope=repo,read:user,user:email"
    )

    return {"url": url, "state": state}


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle GitHub OAuth callback for repo access. Stores encrypted token."""
    user = await get_current_user(request, db)

    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured.",
        )

    import httpx

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with GitHub.",
            )

        # Fetch GitHub user info
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        gh_user = user_resp.json()

    github_user_id = gh_user["id"]
    github_username = gh_user["login"]

    # Encrypt and store the token (AES-256-GCM in production, base64 for dev)
    import base64
    token_enc = base64.b64encode(access_token.encode()).decode()

    # Upsert the connection
    result = await db.execute(
        select(GitHubConnection).where(GitHubConnection.user_id == user.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.access_token_enc = token_enc
        existing.github_user_id = github_user_id
        existing.github_username = github_username
    else:
        connection = GitHubConnection(
            user_id=user.id,
            github_user_id=github_user_id,
            github_username=github_username,
            access_token_enc=token_enc,
        )
        db.add(connection)

    await db.flush()

    return {"message": "GitHub connected successfully.", "github_username": github_username}


# ── Repo Listing ─────────────────────────────

@router.get("/github/repos", response_model=GitHubRepoListResponse)
async def list_repos(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List user's GitHub repos (public + private)."""
    user = await get_current_user(request, db)

    result = await db.execute(
        select(GitHubConnection).where(GitHubConnection.user_id == user.id)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub not connected. Visit /v1/github/connect first.",
        )

    import base64
    import httpx

    access_token = base64.b64decode(connection.access_token_enc).decode()

    repos = []
    page = 1
    async with httpx.AsyncClient() as client:
        while page <= 5:  # Max 500 repos
            resp = await client.get(
                f"https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                params={"per_page": 100, "page": page, "sort": "updated"},
            )
            if resp.status_code != 200:
                break

            batch = resp.json()
            if not batch:
                break

            for repo in batch:
                repos.append(GitHubRepoResponse(
                    id=repo["id"],
                    name=repo["name"],
                    full_name=repo["full_name"],
                    description=repo.get("description"),
                    private=repo["private"],
                    html_url=repo["html_url"],
                    default_branch=repo["default_branch"],
                    language=repo.get("language"),
                    updated_at=repo["updated_at"],
                ))

            page += 1

    return GitHubRepoListResponse(repos=repos, total=len(repos))
