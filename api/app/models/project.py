"""
CIOTX API — Project & GitHub Models
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    team_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    repo_provider: Mapped[str] = mapped_column(String(50), default="github", nullable=False)
    github_repo_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    github_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_repo_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    scan_schedule: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_type: Mapped[str] = mapped_column(String(50), default="github", nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GitHubConnection(Base):
    __tablename__ = "github_connections"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    github_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    github_username: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    installation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
