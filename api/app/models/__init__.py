"""Register all models for Alembic auto-detection."""
from app.models.user import User, ApiToken, CliAuthRequest  # noqa: F401
from app.models.project import Project, GitHubConnection  # noqa: F401
from app.models.scan import Scan, ScanAgentLog, Vulnerability  # noqa: F401
from app.models.billing import Subscription, Invoice  # noqa: F401
