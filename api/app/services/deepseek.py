"""
CIOTX — DeepSeek API Client
AI-First code review: sends code to LLM, parses structured findings.
"""

import json
import os
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.scan import ScanAgentLog, Vulnerability


SYSTEM_PROMPT = """You are a world-class security researcher performing a code audit.
Your task: read the provided code files, understand the application, and find security vulnerabilities.

RULES:
1. Read EVERY line of code carefully.
2. Understand how data flows from input to dangerous operations.
3. Only report a vulnerability if you can PROVE it is exploitable with code evidence.
4. If you cannot prove exploitability, do NOT report it.
5. Consider: SQL injection, XSS, command injection, path traversal, SSRF, IDOR, auth bypass, crypto misuse, race conditions, business logic flaws.
6. For each finding, provide: title, severity (critical/high/medium/low), CWE ID, file path, line numbers, vulnerable code snippet, explanation of why it's vulnerable, and a fix suggestion.

Output ONLY valid JSON. No markdown. No commentary outside the JSON.

{
  "findings": [
    {
      "title": "SQL Injection in search endpoint",
      "severity": "critical",
      "cwe_id": "CWE-89",
      "file_path": "src/api/search.py",
      "line_start": 42,
      "line_end": 45,
      "vulnerable_code": "cursor.execute(f\"SELECT * FROM products WHERE name LIKE '%{query}%'\")",
      "description": "User input 'query' is directly interpolated into SQL string via f-string. No parameterization or sanitization.",
      "fix_suggestion": "Use parameterized queries with SQLAlchemy ORM or cursor.execute with bind parameters.",
      "confidence": 0.95
    }
  ]
}

If no vulnerabilities are found, return: {"findings": []}
"""


def build_context(files: dict[str, str], project_info: str) -> str:
    """Build the prompt context with files and project information."""
    context_parts = [f"PROJECT CONTEXT:\n{project_info}\n\nFILES TO ANALYZE:\n"]
    for path, content in files.items():
        # Truncate very large files to 500 lines
        lines = content.split("\n")
        if len(lines) > 500:
            display = "\n".join(lines[:500])
            context_parts.append(f"--- {path} (truncated to 500 lines) ---\n{display}\n")
        else:
            context_parts.append(f"--- {path} ---\n{content}\n")
    return "\n".join(context_parts)


def parse_findings(response_text: str) -> list[dict]:
    """Parse LLM response into structured findings. Handles JSON in various formats."""
    # Strip markdown code blocks
    text = response_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
        return data.get("findings", [])
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        match = re.search(r'\{[\s\S]*"findings"[\s\S]*\}', text)
        if match:
            try:
                data = json.loads(match.group(0))
                return data.get("findings", [])
            except json.JSONDecodeError:
                pass
        return []


async def run_ai_review(
    scan_id: str,
    project_id: str,
    files: dict[str, str],
    project_info: str,
    db: AsyncSession,
) -> list[dict]:
    """Run the AI-first code review. Returns list of findings."""
    if not settings.DEEPSEEK_API_KEY and not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY:
        return []

    api_key = settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY
    base_url = "https://api.deepseek.com/v1"
    model = "deepseek-v4-flash"

    if settings.OPENAI_API_KEY and not settings.DEEPSEEK_API_KEY:
        base_url = "https://api.openai.com/v1"
        model = "gpt-4o"
    elif settings.ANTHROPIC_API_KEY and not settings.DEEPSEEK_API_KEY and not settings.OPENAI_API_KEY:
        # Anthropic uses a different API format — require CIOTX relay in production
        # For dev: use Anthropic directly via their Messages API
        base_url = "https://api.anthropic.com/v1"
        model = "claude-sonnet-5-20251001"
        # Return early with warning — Anthropic's API is not OpenAI-compatible
        # In production, always use the CIOTX relay which normalizes provider formats
        if not settings.DEV_MODE:
            raise ValueError("Anthropic requires the CIOTX relay in production. Set DEEPSEEK_API_KEY or OPENAI_API_KEY for direct access.")

    context = build_context(files, project_info)

    agent_log = ScanAgentLog(
        scan_id=scan_id,
        agent_name="ai_reviewer",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(agent_log)
    await db.flush()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": context},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096,
                    "response_format": {"type": "json_object"},
                },
            )

            if resp.status_code != 200:
                agent_log.status = "failed"
                agent_log.error_message = f"API error {resp.status_code}: {resp.text[:500]}"
                agent_log.completed_at = datetime.now(timezone.utc)
                await db.flush()
                return []

            data = resp.json()
            usage = data.get("usage", {})
            agent_log.input_tokens = usage.get("prompt_tokens", 0)
            agent_log.output_tokens = usage.get("completion_tokens", 0)
            # Cost: DeepSeek V4 Flash = $0.14/M input, $0.28/M output
            cost = (agent_log.input_tokens / 1_000_000 * 0.14) + (agent_log.output_tokens / 1_000_000 * 0.28)
            agent_log.llm_cost_cents = int(cost * 100)

            content = data["choices"][0]["message"]["content"]
            findings = parse_findings(content)

            agent_log.findings_count = len(findings)
            agent_log.status = "completed"
            agent_log.completed_at = datetime.now(timezone.utc)
            await db.flush()

            return findings

    except Exception as e:
        agent_log.status = "failed"
        agent_log.error_message = str(e)[:500]
        agent_log.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return []
