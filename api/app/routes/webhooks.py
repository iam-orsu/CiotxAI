"""
CIOTX API — GitHub Webhook Receiver
HMAC-SHA256 verification, idempotency, scan trigger dispatching.
"""

import hashlib
import hmac
import json

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        # In dev mode, warn but accept. In production, reject.
        if settings.DEV_MODE:
            return True
        return False

    if not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(request: Request):
    """
    Receive GitHub webhook events.
    Handles: push, pull_request (opened, synchronize).
    Dispatches scan jobs for connected repos.
    """
    payload_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")

    if not verify_signature(payload_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )

    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    if event_type == "ping":
        return {"message": "pong", "delivery_id": delivery_id}

    if event_type == "push":
        repo_id = payload.get("repository", {}).get("id")
        branch = (payload.get("ref") or "").removeprefix("refs/heads/")
        commit_sha = payload.get("after", "")
        # TODO: Find linked project by github_repo_id, enqueue scan
        return {
            "message": "push received",
            "event": "push",
            "repo_id": repo_id,
            "branch": branch,
            "commit_sha": commit_sha,
            "delivery_id": delivery_id,
        }

    if event_type == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize"):
            pr_number = payload.get("number")
            repo_id = payload.get("repository", {}).get("id")
            commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha", "")
            # TODO: Find linked project, enqueue PR scan
            return {
                "message": "pull_request received",
                "event": "pull_request",
                "action": action,
                "repo_id": repo_id,
                "pr_number": pr_number,
                "commit_sha": commit_sha,
                "delivery_id": delivery_id,
            }

    return {"message": f"event {event_type} acknowledged", "delivery_id": delivery_id}
