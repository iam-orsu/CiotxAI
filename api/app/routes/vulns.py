"""CIOTX API — Vulnerability Routes"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.scan import Vulnerability
from app.services.auth import decode_access_token, get_user_by_id

router = APIRouter(tags=["vulnerabilities"])


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


@router.get("/projects/{project_id}/vulns")
async def list_vulns(
    project_id: str,
    request: Request,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    # Verify ownership
    proj = await db.execute(select(Project).where(Project.id == project_id, Project.created_by == user.id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found.")

    query = select(Vulnerability).where(Vulnerability.project_id == project_id)
    if severity:
        query = query.where(Vulnerability.severity == severity.lower())
    if status:
        query = query.where(Vulnerability.status == status.lower())

    severity_order = sa_func.case(
        {"critical": 1, "high": 2, "medium": 3, "low": 4, "info": 5},
        value=Vulnerability.severity,
        else_=99,
    )
    query = query.order_by(
        severity_order.asc(),
        Vulnerability.created_at.desc(),
    ).offset(offset).limit(limit)

    result = await db.execute(query)
    vulns = result.scalars().all()

    # Count total
    count_query = select(sa_func.count(Vulnerability.id)).where(Vulnerability.project_id == project_id)
    if severity:
        count_query = count_query.where(Vulnerability.severity == severity.lower())
    if status:
        count_query = count_query.where(Vulnerability.status == status.lower())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "vulns": [
            {
                "id": v.id,
                "title": v.title,
                "severity": v.severity,
                "cwe_id": v.cwe_id,
                "cvss_score": v.cvss_score,
                "file_path": v.file_path,
                "line_start": v.line_start,
                "line_end": v.line_end,
                "status": v.status,
                "source_agent": v.source_agent,
                "confidence": v.confidence,
                "created_at": v.created_at.isoformat(),
            }
            for v in vulns
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/vulns/{vuln_id}")
async def get_vuln(
    vuln_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    result = await db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id))
    vuln = result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found.")

    # Verify ownership
    proj = await db.execute(select(Project).where(Project.id == vuln.project_id, Project.created_by == user.id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Vulnerability not found.")

    return {
        "id": vuln.id,
        "scan_id": vuln.scan_id,
        "project_id": vuln.project_id,
        "title": vuln.title,
        "description": vuln.description,
        "severity": vuln.severity,
        "cwe_id": vuln.cwe_id,
        "cvss_score": vuln.cvss_score,
        "file_path": vuln.file_path,
        "line_start": vuln.line_start,
        "line_end": vuln.line_end,
        "vulnerable_code": vuln.vulnerable_code,
        "fix_suggestion": vuln.fix_suggestion,
        "fix_diff": vuln.fix_diff,
        "status": vuln.status,
        "source_agent": vuln.source_agent,
        "confidence": vuln.confidence,
        "metadata": vuln.metadata,
        "created_at": vuln.created_at.isoformat(),
    }


@router.patch("/vulns/{vuln_id}")
async def update_vuln_status(
    vuln_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    body = await request.json()
    new_status = body.get("status")
    if new_status not in ("open", "false_positive", "fixed", "wont_fix"):
        raise HTTPException(status_code=400, detail="Invalid status.")

    result = await db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id))
    vuln = result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found.")

    # Verify ownership
    proj = await db.execute(select(Project).where(Project.id == vuln.project_id, Project.created_by == user.id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Vulnerability not found.")

    vuln.status = new_status
    await db.flush()

    return {"id": vuln.id, "status": vuln.status, "message": "Status updated."}
