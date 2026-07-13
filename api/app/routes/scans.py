"""CIOTX API — Scan Routes"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.scan import Scan, ScanAgentLog, Vulnerability
from app.services.auth import decode_access_token, get_user_by_id

router = APIRouter(tags=["scans"])


async def get_current_user(request: Request, db: AsyncSession):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header.")
    payload = decode_access_token(auth.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.post("/projects/{project_id}/scans", status_code=201)
async def trigger_scan(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    scan = Scan(
        project_id=project_id,
        trigger_type="manual",
        status="queued",
    )
    db.add(scan)
    await db.flush()

    # Fire-and-forget: enqueue scan job
    from app.services.scanner import run_scan
    import asyncio
    asyncio.create_task(run_scan(scan.id, project_id, project.repo_url))

    return {
        "scan_id": scan.id,
        "status": "queued",
        "message": "Scan queued. It will run shortly.",
    }


@router.get("/projects/{project_id}/scans")
async def list_scans(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    result = await db.execute(
        select(Scan)
        .where(Scan.project_id == project_id)
        .order_by(Scan.created_at.desc())
        .limit(20)
    )
    scans = result.scalars().all()

    return {
        "scans": [
            {
                "id": s.id,
                "status": s.status,
                "trigger_type": s.trigger_type,
                "branch": s.branch,
                "commit_sha": s.commit_sha,
                "files_scanned": s.files_scanned,
                "total_findings": s.total_findings,
                "critical_count": s.critical_count,
                "high_count": s.high_count,
                "medium_count": s.medium_count,
                "low_count": s.low_count,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in scans
        ],
        "total": len(scans),
    }


@router.get("/scans/{scan_id}")
async def get_scan(
    scan_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await get_current_user(request, db)

    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")

    # Get agent logs
    logs_result = await db.execute(
        select(ScanAgentLog).where(ScanAgentLog.scan_id == scan_id)
    )
    logs = logs_result.scalars().all()

    return {
        "id": scan.id,
        "project_id": scan.project_id,
        "status": scan.status,
        "trigger_type": scan.trigger_type,
        "branch": scan.branch,
        "commit_sha": scan.commit_sha,
        "files_scanned": scan.files_scanned,
        "total_findings": scan.total_findings,
        "critical_count": scan.critical_count,
        "high_count": scan.high_count,
        "medium_count": scan.medium_count,
        "low_count": scan.low_count,
        "total_cost_cents": scan.total_cost_cents,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "created_at": scan.created_at.isoformat(),
        "agents": [
            {
                "name": l.agent_name,
                "status": l.status,
                "input_tokens": l.input_tokens,
                "output_tokens": l.output_tokens,
                "cost_cents": l.llm_cost_cents,
                "findings_count": l.findings_count,
                "error_message": l.error_message,
            }
            for l in logs
        ],
    }
