"""
CIOTX API — Auth Routes
Signup, login, email verification, GitHub OAuth, PKCE for CLI.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import CliAuthRequest, User
from app.schemas.auth import (
    CliInitRequest,
    CliInitResponse,
    CliTokenRequest,
    LoginRequest,
    RefreshTokenRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth import (
    create_access_token,
    decode_access_token,
    generate_verification_code,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    rotate_refresh_token,
    store_refresh_token,
    verify_email_code,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Temp Email Detection ─────────────────────

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.org", "10minutemail.com",
    "trashmail.com", "sharklasers.com", "yopmail.com", "temp-mail.org",
    "disposablemail.com", "throwaway.email", "maildrop.cc", "getnada.com",
    "fakeinbox.com", "tempmailaddress.com", "guerrillamail.info",
    "guerrillamail.biz", "guerrillamail.org", "guerrillamail.net",
    "guerrillamail.de", "guerrillamailblock.com", "pokemail.net",
    "spam4.me", "wegwerfmail.de", "wegwerfmail.net", "wegwerfmail.org",
    "fake-mail.com", "fakeinbox.info", "emailondeck.com", "emailfake.com",
    "mohmal.com", "mohmal.in", "moakt.com", "mailnesia.com",
}


def is_disposable_email(email: str) -> bool:
    domain = email.lower().split("@")[-1]
    if domain in DISPOSABLE_DOMAINS:
        return True
    # Pattern detection
    if any(term in domain for term in ["temp", "disposable", "throwaway", "trash", "guerrilla", "10minute"]):
        return True
    return False


# ── Signup ───────────────────────────────────

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()

    if is_disposable_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use a permanent email address. Disposable email addresses are not allowed.",
        )

    existing = await get_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    trial_days = 7
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        name=body.name,
        email_verified=False,
        plan=settings.DEV_AUTO_PLAN if settings.DEV_MODE else "free",
        plan_status="trial",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=trial_days),
    )
    db.add(user)
    await db.flush()

    code = generate_verification_code(email)
    if settings.DEV_MODE:
        # Auto-verify in dev mode
        user.email_verified = True
        await db.flush()
        return {"message": "Account created (dev mode — auto-verified).", "user_id": user.id}

    # In production, send email with verification code
    # TODO: integrate email service (Resend/SES)
    return {
        "message": "Account created. Check your email for a 6-digit verification code.",
        "user_id": user.id,
    }


# ── Email Verification ───────────────────────

@router.post("/verify")
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()

    if not verify_email_code(email, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.email_verified = True
    await db.flush()

    return {"message": "Email verified successfully."}


# ── Login ────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()

    user = await get_user_by_email(db, email)
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    access_token = create_access_token(user.id, user.email, user.plan)
    refresh_token = await store_refresh_token(db, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ── Token Refresh ────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await rotate_refresh_token(db, body.refresh_token)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please log in again.",
        )

    new_refresh_token, user_id, _ = result

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    access_token = create_access_token(user.id, user.email, user.plan)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


# ── Current User ─────────────────────────────

@router.get("/me", response_model=UserResponse)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
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

    return UserResponse.model_validate(user)


# ── GitHub OAuth ─────────────────────────────

@router.get("/github")
async def github_login():
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured.",
        )

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.API_BASE_URL}/v1/auth/github/callback"

    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope=read:user,user:email"
    )

    return {"url": github_url, "state": state}


@router.get("/github/callback")
async def github_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """
    Handle GitHub OAuth callback. Exchange code for access token,
    fetch user info, create or link account.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured.",
        )

    import httpx

    # Exchange code for access token
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

        # Fetch GitHub user
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        gh_user = user_resp.json()

        # Fetch emails (for primary email if user has no public email)
        emails_resp = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        emails = emails_resp.json()

    github_user_id = gh_user["id"]
    github_username = gh_user["login"]
    github_email = gh_user.get("email")
    github_name = gh_user.get("name") or github_username
    github_avatar = gh_user.get("avatar_url")

    # Find primary email
    if not github_email and isinstance(emails, list):
        for email_entry in emails:
            if email_entry.get("primary"):
                github_email = email_entry["email"]
                break

    if not github_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find a verified email for your GitHub account.",
        )

    # Find existing user by GitHub ID or email
    from sqlalchemy import select as sa_select

    result = await db.execute(sa_select(User).where(User.github_user_id == github_user_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(sa_select(User).where(User.email == github_email.lower()))
        user = result.scalar_one_or_none()

    if user:
        # Link GitHub account if not already linked
        if not user.github_user_id:
            user.github_user_id = github_user_id
            user.github_username = github_username
            if not user.avatar_url:
                user.avatar_url = github_avatar
            await db.flush()
    else:
        # Create new user
        trial_days = 7
        user = User(
            email=github_email.lower(),
            name=github_name,
            avatar_url=github_avatar,
            github_user_id=github_user_id,
            github_username=github_username,
            email_verified=True,  # GitHub verified
            plan=settings.DEV_AUTO_PLAN if settings.DEV_MODE else "free",
            plan_status="trial",
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=trial_days),
        )
        db.add(user)
        await db.flush()

    access_token_jwt = create_access_token(user.id, user.email, user.plan)
    refresh_token = await store_refresh_token(db, user.id)

    return TokenResponse(
        access_token=access_token_jwt,
        refresh_token=refresh_token,
    )


# ── PKCE for CLI ─────────────────────────────

@router.post("/cli/init", response_model=CliInitResponse)
async def cli_init(body: CliInitRequest, db: AsyncSession = Depends(get_db)):
    device_code = secrets.token_urlsafe(32)
    user_code = f"{secrets.randbelow(1000000):06d}"

    auth_request = CliAuthRequest(
        device_code=device_code,
        user_code=user_code,
        code_challenge=body.code_challenge,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(auth_request)
    await db.flush()

    return CliInitResponse(
        device_code=device_code,
        user_code=user_code,
        verification_uri=f"{settings.DASHBOARD_URL}/verify?code={user_code}",
        expires_in=600,
    )


@router.post("/cli/verify")
async def cli_verify(user_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Called from the browser after user confirms. Links the PKCE request to the user."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = auth_header.split(" ", 1)[1]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(CliAuthRequest).where(
            CliAuthRequest.user_code == user_code,
            CliAuthRequest.expires_at > datetime.now(timezone.utc),
        )
    )
    auth_request = result.scalar_one_or_none()

    if not auth_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired user code.")

    auth_request.user_id = payload["sub"]
    auth_request.verified = True
    await db.flush()

    return {"message": "Authorization confirmed. You can close this page."}


@router.post("/cli/token", response_model=TokenResponse)
async def cli_token(body: CliTokenRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(CliAuthRequest).where(
            CliAuthRequest.device_code == body.device_code,
            CliAuthRequest.expires_at > datetime.now(timezone.utc),
        )
    )
    auth_request = result.scalar_one_or_none()

    if not auth_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired device code.",
        )

    # Verify code_challenge
    computed_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(body.code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    if computed_challenge != auth_request.code_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code verifier.",
        )

    if not auth_request.verified or not auth_request.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization not yet confirmed in browser. Waiting for you to approve.",
        )

    user = await get_user_by_id(db, auth_request.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    access_token = create_access_token(user.id, user.email, user.plan)
    refresh_token = await store_refresh_token(db, user.id)

    # Clean up the PKCE request
    await db.delete(auth_request)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ── Password Reset ───────────────────────────

RESET_TOKENS: dict[str, tuple[str, datetime]] = {}


@router.post("/forgot-password")
async def forgot_password(body: dict, db: AsyncSession = Depends(get_db)):
    """Request a password reset. In dev mode, returns the reset token directly."""
    email = body.get("email", "").lower().strip()
    user = await get_user_by_email(db, email)

    if not user:
        return {"message": "If an account exists with that email, a reset link has been sent."}

    if not user.password_hash:
        return {"message": "This account uses GitHub OAuth. Please sign in with GitHub."}

    token = secrets.token_urlsafe(32)
    RESET_TOKENS[email] = (token, datetime.now(timezone.utc) + timedelta(hours=1))

    if settings.DEV_MODE:
        return {
            "message": "Password reset token generated (DEV MODE).",
            "reset_token": token,
        }

    return {"message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: dict, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid reset token."""
    email = body.get("email", "").lower().strip()
    token = body.get("token", "")
    new_password = body.get("new_password", "")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    stored = RESET_TOKENS.get(email)
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    stored_token, expires_at = stored
    if stored_token != token or datetime.now(timezone.utc) > expires_at:
        del RESET_TOKENS[email]
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password_hash = hash_password(new_password)
    del RESET_TOKENS[email]
    await db.flush()

    return {"message": "Password reset successfully. You can now log in."}
