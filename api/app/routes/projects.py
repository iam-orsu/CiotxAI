"""
CIOTX API — Project Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.schemas.project import CreateProjectRequest, ProjectListResponse, ProjectResponse
from app.services.auth import decode_access_token, get_user_by_id

router = APIRouter(prefix="/projects", tags=["projects"])


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


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    result = await db.execute(
        select(Project)
        .where(Project.created_by == user.id)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    project_list = []
    for p in projects:
        project_list.append(ProjectResponse(
            id=p.id,
            name=p.name,
            repo_url=p.repo_url,
            repo_provider=p.repo_provider,
            github_repo_id=p.github_repo_id,
            github_owner=p.github_owner,
            github_repo_name=p.github_repo_name,
            default_branch=p.default_branch,
            scan_schedule=p.scan_schedule,
            project_type=p.project_type,
            vuln_counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            last_scan_at=None,
            created_at=p.created_at,
        ))

    return ProjectListResponse(projects=project_list, total=len(project_list))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: CreateProjectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    project = Project(
        name=body.name,
        repo_url=body.repo_url,
        repo_provider=body.repo_provider,
        github_repo_id=body.github_repo_id,
        created_by=user.id,
        project_type="github" if body.github_repo_id else "manual",
    )

    if body.repo_url and "github.com" in body.repo_url:
        parts = body.repo_url.rstrip("/").split("/")
        if len(parts) >= 2:
            project.github_owner = parts[-2]
            project.github_repo_name = parts[-1].removesuffix(".git")

    db.add(project)
    await db.flush()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        repo_url=project.repo_url,
        repo_provider=project.repo_provider,
        github_repo_id=project.github_repo_id,
        github_owner=project.github_owner,
        github_repo_name=project.github_repo_name,
        default_branch=project.default_branch,
        scan_schedule=project.scan_schedule,
        project_type=project.project_type,
        vuln_counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        last_scan_at=None,
        created_at=project.created_at,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    return ProjectResponse(
        id=project.id,
        name=project.name,
        repo_url=project.repo_url,
        repo_provider=project.repo_provider,
        github_repo_id=project.github_repo_id,
        github_owner=project.github_owner,
        github_repo_name=project.github_repo_name,
        default_branch=project.default_branch,
        scan_schedule=project.scan_schedule,
        project_type=project.project_type,
        vuln_counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        last_scan_at=None,
        created_at=project.created_at,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    await db.delete(project)
    await db.flush()
