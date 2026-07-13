"""
CIOTX — Scan Orchestrator
Phase 1: Ingest (clone repo, discover files)
Phase 2: AI-First Review (DeepSeek reads every line)
Phase 3: Triage (dedup, score, store)
"""

import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import Scan, ScanAgentLog, Vulnerability
from app.services.deepseek import run_ai_review

# Files to skip during scanning
SKIP_PATTERNS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv", "env",
    ".next", "dist", "build", "target", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "vendor", "bower_components",
}
SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".mp3", ".avi", ".mov", ".pdf", ".zip",
    ".tar", ".gz", ".bz2", ".7z", ".lock", ".log", ".min.js", ".min.css",
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb", ".php",
    ".rs", ".swift", ".kt", ".c", ".h", ".cpp", ".hpp", ".cs", ".vue",
    ".svelte", ".sql", ".yaml", ".yml", ".toml", ".tf", ".dockerfile",
}


def discover_files(root: str) -> dict[str, str]:
    """Walk a directory and return {relative_path: content} for all source files."""
    files = {}
    root_path = Path(root)
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root_path))
        parts = set(rel.split(os.sep))
        if parts & SKIP_PATTERNS:
            continue
        if path.suffix.lower() in SKIP_EXTENSIONS:
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS and path.name.lower() not in ("dockerfile", "makefile"):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content.strip()) > 0:
                files[rel] = content
        except Exception:
            continue
    return files


def detect_project_info(files: dict[str, str]) -> str:
    """Detect tech stack and project structure from discovered files."""
    info_parts = []
    extensions = set()
    for path in files:
        ext = Path(path).suffix.lower()
        if ext:
            extensions.add(ext)

    lang_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".tsx": "React/TypeScript", ".jsx": "React/JavaScript",
        ".go": "Go", ".java": "Java", ".rb": "Ruby", ".php": "PHP",
        ".rs": "Rust", ".swift": "Swift", ".kt": "Kotlin",
        ".vue": "Vue.js", ".svelte": "Svelte",
    }
    detected = []
    for ext, lang in lang_map.items():
        if ext in extensions:
            detected.append(lang)

    info_parts.append(f"Languages detected: {', '.join(detected) if detected else 'unknown'}")
    info_parts.append(f"Total source files: {len(files)}")

    # Check for framework indicators
    if "requirements.txt" in files:
        info_parts.append("Python dependencies: requirements.txt found")
    if "package.json" in files:
        info_parts.append("Node.js: package.json found")
    if "go.mod" in files:
        info_parts.append("Go module: go.mod found")
    if "Dockerfile" in files or "docker-compose.yml" in files:
        info_parts.append("Docker: containerized application")

    return "\n".join(info_parts)


async def run_scan(scan_id: str, project_id: str, repo_url: str | None, local_path: str | None = None):
    """Run the full scan pipeline for a scan job."""
    from app.database import async_session

    async with async_session() as db:
        # Load scan
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        if not scan:
            return

        scan.status = "cloning"
        scan.started_at = datetime.now(timezone.utc)
        await db.flush()

        tmpdir = None
        try:
            # Phase 1: Ingest
            if local_path and os.path.isdir(local_path):
                scan_root = local_path
            elif repo_url:
                tmpdir = tempfile.mkdtemp(prefix="ciotx-scan-")
                subprocess.run(
                    ["git", "clone", "--depth=1", repo_url, tmpdir],
                    capture_output=True, timeout=60,
                )
                scan_root = tmpdir
            else:
                scan.status = "failed"
                scan.completed_at = datetime.now(timezone.utc)
                await db.flush()
                return

            scan.status = "scanning"
            await db.flush()

            files = discover_files(scan_root)
            scan.files_scanned = len(files)
            await db.flush()

            if not files:
                scan.status = "completed"
                scan.completed_at = datetime.now(timezone.utc)
                await db.flush()
                return

            # Phase 2: AI-First Review
            project_info = detect_project_info(files)
            findings = await run_ai_review(scan_id, project_id, files, project_info, db)

            # Phase 3: Triage & Store
            scan.status = "triaging"
            await db.flush()

            severity_map = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
            stored = 0

            for f in findings:
                sev = f.get("severity", "medium").lower()
                if sev not in severity_map:
                    sev = "medium"

                vuln = Vulnerability(
                    scan_id=scan_id,
                    project_id=project_id,
                    title=f.get("title", "Untitled finding"),
                    description=f.get("description", ""),
                    severity=sev,
                    cwe_id=f.get("cwe_id"),
                    cvss_score=f.get("cvss_score"),
                    file_path=f.get("file_path", "unknown"),
                    line_start=f.get("line_start"),
                    line_end=f.get("line_end"),
                    vulnerable_code=f.get("vulnerable_code"),
                    fix_suggestion=f.get("fix_suggestion"),
                    source_agent="ai_reviewer",
                    confidence=f.get("confidence", 0.7),
                )
                db.add(vuln)
                severity_map[sev] = severity_map.get(sev, 0) + 1
                stored += 1

            scan.total_findings = stored
            scan.critical_count = severity_map["critical"]
            scan.high_count = severity_map["high"]
            scan.medium_count = severity_map["medium"]
            scan.low_count = severity_map["low"]
            scan.status = "completed"
            scan.completed_at = datetime.now(timezone.utc)
            await db.flush()

        except Exception as e:
            scan.status = "failed"
            scan.completed_at = datetime.now(timezone.utc)
            agent_log = ScanAgentLog(
                scan_id=scan_id,
                agent_name="orchestrator",
                status="failed",
                error_message=str(e)[:500],
                completed_at=datetime.now(timezone.utc),
            )
            db.add(agent_log)
            await db.flush()
        finally:
            if tmpdir:
                import shutil
                shutil.rmtree(tmpdir, ignore_errors=True)


async def run_local_scan(scan_id: str, project_id: str, local_path: str):
    """Run scan on a local directory (via CLI upload)."""
    await run_scan(scan_id, project_id, None, local_path=local_path)
