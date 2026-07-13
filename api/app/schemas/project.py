"""
CIOTX API — Project Schemas
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    repo_url: str | None = Field(default=None, max_length=2048)
    repo_provider: str = Field(default="github")
    github_repo_id: int | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    repo_url: str | None
    repo_provider: str
    github_repo_id: int | None
    github_owner: str | None
    github_repo_name: str | None
    default_branch: str
    scan_schedule: str | None
    project_type: str
    vuln_counts: dict | None = None
    last_scan_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


class GitHubRepoResponse(BaseModel):
    id: int
    name: str
    full_name: str
    description: str | None
    private: bool
    html_url: str
    default_branch: str
    language: str | None
    updated_at: datetime


class GitHubRepoListResponse(BaseModel):
    repos: list[GitHubRepoResponse]
    total: int
