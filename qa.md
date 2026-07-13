# QA Audit Report

## Summary
- **Total files reviewed:** 68
- **Total lines read:** ~6,800
- **Critical (crash):** 7
- **Production bugs:** 14
- **Cross-file / API inconsistencies:** 8
- **Irrelevant / minor:** 11

## Files Reviewed

- [x] `.env` (11 lines)
- [x] `.env.example` (56 lines)
- [x] `.gitignore` (51 lines)
- [x] `Makefile` (50 lines)
- [x] `docker-compose.yml` (118 lines)
- [x] `.claude/settings.local.json` (11 lines)
- [x] `api/Dockerfile` (22 lines)
- [x] `api/Dockerfile.worker` (21 lines)
- [x] `api/alembic.ini` (37 lines)
- [x] `api/requirements.txt` (39 lines)
- [x] `api/app/__init__.py` (0 lines — empty)
- [x] `api/app/config.py` (67 lines)
- [x] `api/app/database.py` (46 lines)
- [x] `api/app/main.py` (110 lines)
- [x] `api/app/worker.py` (38 lines)
- [x] `api/app/models/__init__.py` (6 lines)
- [x] `api/app/models/billing.py` (48 lines)
- [x] `api/app/models/project.py` (47 lines)
- [x] `api/app/models/scan.py` (77 lines)
- [x] `api/app/models/user.py` (77 lines)
- [x] `api/app/routes/__init__.py` (0 lines — empty)
- [x] `api/app/routes/auth.py` (524 lines)
- [x] `api/app/routes/billing.py` (198 lines)
- [x] `api/app/routes/github.py` (195 lines)
- [x] `api/app/routes/projects.py` (196 lines)
- [x] `api/app/routes/scans.py` (281 lines)
- [x] `api/app/routes/vulns.py` (161 lines)
- [x] `api/app/routes/webhooks.py` (99 lines)
- [x] `api/app/schemas/auth.py` (76 lines)
- [x] `api/app/schemas/project.py` (55 lines)
- [x] `api/app/services/auth.py` (202 lines)
- [x] `api/app/services/deepseek.py` (173 lines)
- [x] `api/app/services/scanner.py` (290 lines)
- [x] `api/migrations/env.py` (52 lines)
- [x] `api/migrations/script.py.mako` (25 lines)
- [x] `cli/main.go` (16 lines)
- [x] `cli/go.mod` (9 lines)
- [x] `cli/cmd/root.go` (314 lines)
- [x] `cli/internal/api/client.go` (228 lines)
- [x] `cli/internal/auth/pkce.go` (117 lines)
- [x] `cli/internal/config/config.go` (91 lines)
- [x] `cli/internal/engine/ingest.go` (160 lines)
- [x] `cli/internal/engine/llm.go` (183 lines)
- [x] `cli/internal/engine/safety.go` (56 lines)
- [x] `cli/internal/engine/sanitizer.go` (77 lines)
- [x] `cli/internal/engine/scanner.go` (184 lines)
- [x] `dashboard/Dockerfile` (13 lines)
- [x] `dashboard/package.json` (31 lines)
- [x] `dashboard/tailwind.config.ts` (69 lines)
- [x] `dashboard/tsconfig.json` (24 lines)
- [x] `dashboard/app/globals.css` (50 lines)
- [x] `dashboard/app/layout.tsx` (18 lines)
- [x] `dashboard/app/page.tsx` (67 lines)
- [x] `dashboard/app/(auth)/login/page.tsx` (100 lines)
- [x] `dashboard/app/(auth)/signup/page.tsx` (118 lines)
- [x] `dashboard/app/(auth)/verify/page.tsx` (90 lines)
- [x] `dashboard/app/(dashboard)/billing/page.tsx` (168 lines)
- [x] `dashboard/app/(dashboard)/dashboard/page.tsx` (186 lines)
- [x] `dashboard/app/(dashboard)/dashboard/[projectId]/page.tsx` (190 lines)
- [x] `dashboard/app/(dashboard)/dashboard/[projectId]/scans/[scanId]/page.tsx` (142 lines)
- [x] `dashboard/app/(dashboard)/dashboard/[projectId]/vulns/page.tsx` (124 lines)
- [x] `dashboard/app/(dashboard)/dashboard/[projectId]/vulns/[vulnId]/page.tsx` (155 lines)
- [x] `dashboard/app/(dashboard)/settings/page.tsx` (99 lines)
- [x] `dashboard/components/Sidebar.tsx` (71 lines)
- [x] `dashboard/lib/api.ts` (152 lines)
- [x] `scripts/qa-test.sh` (237 lines)
- [x] `scripts/qa-test.ps1` (216 lines)
- [x] `dashboard/app/settings/` (empty directory — skipped)

---

## API / Surface Inventory

### API Endpoints (Python/FastAPI — `api/`)

| File | Route | Method | Inputs | Outputs | Error Behavior | Side Effects |
|------|-------|--------|--------|---------|----------------|--------------|
| routes/auth.py | `/v1/auth/signup` | POST | `SignupRequest{email,password,name?}` | `{message,user_id}` | 400 disposable email, 409 duplicate | Creates User row, generates verification code |
| routes/auth.py | `/v1/auth/verify` | POST | `VerifyEmailRequest{email,code}` | `{message}` | 400 bad code, 404 no user | Sets `email_verified=True` |
| routes/auth.py | `/v1/auth/login` | POST | `LoginRequest{email,password}` | `TokenResponse{access_token,refresh_token,token_type,expires_in}` | 401 bad creds, 403 unverified | Creates ApiToken (refresh) |
| routes/auth.py | `/v1/auth/refresh` | POST | `RefreshTokenRequest{refresh_token}` | `TokenResponse` | 401 invalid/expired | Rotates refresh token family |
| routes/auth.py | `/v1/auth/me` | GET | Bearer token header | `UserResponse` | 401, 404 | None |
| routes/auth.py | `/v1/auth/github` | GET | None | `{url,state}` | 501 not configured | None |
| routes/auth.py | `/v1/auth/github/callback` | GET | `code,state` query params | `TokenResponse` | 400/501 | Creates/links User, stores tokens |
| routes/auth.py | `/v1/auth/cli/init` | POST | `CliInitRequest{code_challenge}` | `CliInitResponse{device_code,user_code,verification_uri,expires_in}` | — | Creates CliAuthRequest row |
| routes/auth.py | `/v1/auth/cli/verify` | POST | `user_code` query param, Bearer token | `{message}` | 401, 404 | Sets `verified=True`, links user |
| routes/auth.py | `/v1/auth/cli/token` | POST | `CliTokenRequest{device_code,code_verifier}` | `TokenResponse` | 400 various | Deletes CliAuthRequest, creates tokens |
| routes/auth.py | `/v1/auth/forgot-password` | POST | `dict{email}` | `{message}` or `{message,reset_token}` | — | Stores token in in-memory dict |
| routes/auth.py | `/v1/auth/reset-password` | POST | `dict{email,token,new_password}` | `{message}` | 400, 404 | Updates `password_hash` |
| routes/billing.py | `/v1/billing/plans` | GET | None | `{plans}` | — | None |
| routes/billing.py | `/v1/billing/subscription` | GET | Bearer token | `{has_subscription,...}` | 401, 404 | None |
| routes/billing.py | `/v1/billing/subscribe` | POST | Bearer token, `{plan,billing_period}` | `{message,...}` or `{order_id,...}` | 400, 401, 500 | Creates/updates Subscription, Invoice |
| routes/billing.py | `/v1/billing/cancel` | POST | Bearer token | `{message}` | 400, 401 | Sets subscription status=cancelled |
| routes/projects.py | `/v1/projects` | GET | Bearer token | `ProjectListResponse` | 401, 404 | None |
| routes/projects.py | `/v1/projects` | POST | Bearer token, `CreateProjectRequest` | `ProjectResponse` | 401, 404 | Creates Project row |
| routes/projects.py | `/v1/projects/{id}` | GET | Bearer token, path param | `ProjectResponse` | 401, 404 | None |
| routes/projects.py | `/v1/projects/{id}` | DELETE | Bearer token, path param | 204 | 401, 404 | Deletes Project row |
| routes/scans.py | `/v1/projects/{id}/scans` | POST | Bearer token | `{scan_id,status,message}` | 402, 404 | Creates Scan, enqueues ARQ job |
| routes/scans.py | `/v1/projects/{id}/scans` | GET | Bearer token | `{scans[],total}` | 404 | None |
| routes/scans.py | `/v1/scans/{id}` | GET | Bearer token | Scan detail dict | 404 | None |
| routes/scans.py | `/v1/scans/local` | POST | Bearer token, JSON body | `{scan_id,project_id,total_findings,message}` | 401 | Creates Project/Scan/Vulnerability rows |
| routes/vulns.py | `/v1/projects/{id}/vulns` | GET | Bearer token, query params | `{vulns[],total,limit,offset}` | 404 | None |
| routes/vulns.py | `/v1/vulns/{id}` | GET | Bearer token | Vuln detail dict | 404 | None |
| routes/vulns.py | `/v1/vulns/{id}` | PATCH | Bearer token, `{status}` | `{id,status,message}` | 400, 404 | Updates vuln status |
| routes/webhooks.py | `/v1/webhooks/github` | POST | Raw body, GitHub headers | `{message,...}` | 401, 400 | None (TODOs for scan triggering) |
| routes/github.py | `/v1/github/connect` | GET | None (no auth enforced on initiation) | `{url,state}` | 501 | None |
| routes/github.py | `/v1/github/callback` | GET | Bearer token, `code,state` query | `{message,github_username}` | 400, 501 | Upserts GitHubConnection |
| routes/github.py | `/v1/github/repos` | GET | Bearer token | `GitHubRepoListResponse` | 400 | None |
| main.py | `/health` | GET | None | `{status,version,dev_mode}` | — | None |
| main.py | `/v1/health` | GET | None | `{status,version,dev_mode}` | — | None |

### Exported Functions (Python Services)

| File | Function | Inputs | Outputs | Notes |
|------|----------|--------|---------|-------|
| services/auth.py | `hash_password(password)` | str | str (argon2 hash) | — |
| services/auth.py | `verify_password(password, hash)` | str, str | bool | — |
| services/auth.py | `create_access_token(user_id, email, plan)` | str, str, str | JWT str | 15min expiry |
| services/auth.py | `decode_access_token(token)` | str | dict or None | Checks `type=access` |
| services/auth.py | `store_refresh_token(db, user_id, family_id?)` | AsyncSession, str, str? | raw token str | Creates ApiToken row |
| services/auth.py | `rotate_refresh_token(db, raw_token)` | AsyncSession, str | tuple or None | Reuse detection |
| services/auth.py | `get_user_by_email(db, email)` | AsyncSession, str | User or None | — |
| services/auth.py | `get_user_by_id(db, user_id)` | AsyncSession, str | User or None | — |
| services/auth.py | `generate_verification_code(email)` | str | 6-digit str | In-memory dict |
| services/auth.py | `verify_email_code(email, code)` | str, str | bool | — |
| services/deepseek.py | `run_ai_review(scan_id, project_id, files, project_info, db)` | various | list[dict] | Calls LLM API |
| services/scanner.py | `run_scan(scan_id, project_id, repo_url, local_path?)` | various | None | Full scan orchestrator |
| worker.py | `run_scan_job(ctx, scan_id, project_id, repo_url?)` | dict, str, str, str? | None | ARQ job entry |
| worker.py | `enqueue_scan(scan_id, project_id, repo_url?)` | str, str, str? | None | Creates Redis pool per call |

### Go CLI Exported Functions

| File | Function | Inputs | Outputs | Notes |
|------|----------|--------|---------|-------|
| cmd/root.go | `Execute()` | — | error | CLI entry point |
| internal/api/client.go | `GetMe(cfg)` | *Config | *UserResponse, error | GET /v1/auth/me |
| internal/api/client.go | `TriggerScan(cfg, repoURL)` | *Config, string | map, error | Creates project if needed |
| internal/api/client.go | `ListScans(cfg)` | *Config | []map, error | Fetches all projects' scans |
| internal/api/client.go | `RefreshToken(cfg)` | *Config | error | POST /v1/auth/refresh |
| internal/auth/pkce.go | `InitPKCE(apiURL)` | string | *CliInitResponse, verifier, error | PKCE flow init |
| internal/auth/pkce.go | `PollForToken(apiURL, deviceCode, verifier, timeout)` | various | *TokenResponse, error | Polls /v1/auth/cli/token |
| internal/engine/scanner.go | `RunLocalScan(path)` | string | *ScanResult, error | Full local scan |
| internal/engine/scanner.go | `PushFindings(apiURL, token, name, result)` | various | scanID string, error | POST /v1/scans/local |

---

## Critical / Crash Bugs

### C1. [api/app/routes/webhooks.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/webhooks.py#L28) : line 28
- **Issue:** `hmac.new()` should be `hmac.HMAC()` (or `hmac.new()`). Actually Python's `hmac` module exposes `hmac.new()` — but it is lower-case `hmac.new`, not `hmac.HMAC`. Let me re-examine… The code uses `hmac.new(...)` on line 28. In Python's `hmac` module the constructor is `hmac.new()`. This is correct. **RETRACTED — not a bug.**

### C1 (revised). [api/app/database.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/database.py#L25-L32) : lines 25-32
- **Issue:** `get_db()` is an async generator (uses `yield`), but it is annotated as returning `-> AsyncSession`. FastAPI handles this correctly as a dependency, but the return type annotation is technically wrong. More critically: **the `commit()` on line 29 runs after every request**, even read-only GET requests. This is not a crash bug per se, but it causes unnecessary DB round-trips.
- **Reasoning/trace:** Every route using `Depends(get_db)` will auto-commit even for pure SELECT queries. If any transient DB error occurs during commit of a read-only request, the user gets a 500 error on what should be a side-effect-free read.
- **Trigger condition:** Any GET endpoint under transient DB instability.
- **Impact:** Spurious 500 errors on read-only endpoints.

### C2. [api/app/routes/scans.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/scans.py#L90-L91) : lines 90-91
- **Issue:** `enqueue_scan()` is called within the `get_db()` context manager, which means it runs **before** `db.commit()` completes. The `enqueue_scan` function creates a **separate** Redis connection and enqueues a job referencing `scan.id`. The worker will then open its **own** DB session and do `select(Scan).where(Scan.id == scan_id)`. But at this point, the original transaction (which created the Scan row) may not yet be committed — `get_db()` commits **after** the route handler returns. This is a race condition: the worker can pick up the job before the Scan row is committed, find no scan, and silently return.
- **Reasoning/trace:** Route handler → `db.add(scan)` + `db.flush()` (writes to DB but within uncommitted transaction) → `enqueue_scan()` (puts job in Redis) → handler returns → `get_db()` calls `await session.commit()`. Meanwhile, worker picks up job → opens new session → `select(Scan).where(Scan.id == scan_id)` → row not yet visible (READ COMMITTED isolation) → `scan` is `None` → `return` on line 173 of scanner.py. Scan stuck in `queued` forever.
- **Trigger condition:** Worker picks up the job faster than the API transaction commits. More likely under load.
- **Impact:** Scans silently fail to execute, stuck permanently in `queued` status. Data loss — user never gets results.

### C3. [api/app/services/scanner.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/scanner.py#L165-L284) : lines 165-284
- **Issue:** `run_scan()` opens its own `async_session()` context and does `await db.flush()` repeatedly but **never calls `await db.commit()`**. The `async with async_session() as db:` block will auto-close the session when exiting, but SQLAlchemy `async_session` does NOT auto-commit. All scan results, vulnerability records, and status updates are flushed to the database within the transaction but **never committed**.
- **Reasoning/trace:** The `async_session` factory is created with `expire_on_commit=False` in database.py:18. The `run_scan` function does not use the `get_db()` dependency (which has auto-commit in its `try/yield/commit` pattern). It directly uses `async with async_session() as db:`. SQLAlchemy's `AsyncSession` context manager closes the session on exit but does NOT commit. All `flush()` calls write to the DB within the transaction, but without `commit()`, the transaction is rolled back on session close.
- **Trigger condition:** Every cloud scan execution via the worker.
- **Impact:** **All scan results are lost.** Vulnerabilities are written then rolled back. The scan status is never updated from the perspective of other sessions. This is the most critical bug in the codebase.

### C4. [cli/internal/api/client.go](file:///c:/Users/adversary/Desktop/CiotxAI/cli/internal/api/client.go#L166-L182) : lines 166-182
- **Issue:** After a 401 response triggers token refresh, the code attempts to retry the original request by re-sending `req`. However, the original request's `Body` (an `io.Reader`) has **already been consumed** by the first `http.DefaultClient.Do(req)` call. On retry, `req.Body` is at EOF. For POST requests with a body, the retry sends an empty body, which will fail.
- **Reasoning/trace:** Go's `http.Request.Body` is an `io.ReadCloser`. After the first `Do(req)`, the body is fully read and the stream is at EOF. The retry on line 173 re-uses the same `req` object with the depleted body. Additionally, `resp.Body` from the first call was already read on line 161, and `defer resp.Body.Close()` on line 159 will close it — but `resp2.Body.Close()` on line 177 creates a second defer that will also fire, which is fine but the real issue is the empty body on retry.
- **Trigger condition:** Any authenticated POST/PUT request that gets a 401 and triggers token refresh (e.g., creating a project with an expired access token).
- **Impact:** The retried request fails with a malformed/empty body. The user sees a cryptic API error.

### C5. [cli/internal/engine/llm.go](file:///c:/Users/adversary/Desktop/CiotxAI/cli/internal/engine/llm.go#L109-L124) : lines 109-124
- **Issue:** The LLM request does **not include the Authorization header**. The code builds the request body and POSTs to `c.BaseURL + "/chat/completions"`, but never sets `Authorization: Bearer <key>`. The `http.Client.Post()` method doesn't support custom headers. The API key (`c.APIKey`) is stored in the `LLMClient` struct but never used in the HTTP request.
- **Reasoning/trace:** Line 112: `client.Post(c.BaseURL+"/chat/completions", "application/json", bytes.NewReader(bodyBytes))`. The `http.Client.Post` signature is `Post(url, contentType, body)` — there is no way to pass headers. The API key is never sent. Every LLM API call from the CLI will fail with a 401 Unauthorized.
- **Trigger condition:** Every local scan that attempts AI code review via the CLI.
- **Impact:** CLI AI review always fails. The error is caught and printed as a warning (`⚠️ AI review failed`), so it doesn't crash, but the core feature (AI code review) is completely broken in the CLI.

### C6. [cli/cmd/root.go](file:///c:/Users/adversary/Desktop/CiotxAI/cli/cmd/root.go#L263-L270) : lines 263-270
- **Issue:** `s["id"].(string)[:8]` and `s["total_findings"]` are type-asserted from `map[string]interface{}` without nil checks. If the API response doesn't contain these keys (e.g., API version mismatch, or a field is null), this will panic with a nil pointer dereference or interface conversion error.
- **Reasoning/trace:** `s["id"].(string)` will panic if `s["id"]` is nil. `s["total_findings"]` when formatted with `%v` won't panic, but `s["status"].(string)` on line 264 will panic if status is missing.
- **Trigger condition:** API returns a scan without `id` or `status` field, or returns them as non-string types (e.g., `null`).
- **Impact:** CLI panic (crash) with stack trace.

### C7. [api/app/services/deepseek.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/deepseek.py#L100-L109) : lines 100-109
- **Issue:** When using the Anthropic API, the code sets `base_url = "https://api.anthropic.com/v1"` and then calls `f"{base_url}/chat/completions"` which resolves to `https://api.anthropic.com/v1/chat/completions`. Anthropic's API uses `/v1/messages`, not `/v1/chat/completions`. The request will fail with a 404.
- **Reasoning/trace:** Lines 107-109: if Anthropic key is set and DeepSeek is not, `base_url` becomes `https://api.anthropic.com/v1` and `model` becomes `claude-sonnet-5-20251001`. Then line 125: `f"{base_url}/chat/completions"` → `https://api.anthropic.com/v1/chat/completions` which is not a valid Anthropic endpoint. Additionally, Anthropic uses `x-api-key` header instead of `Authorization: Bearer`, and a completely different request format.
- **Trigger condition:** User configures `ANTHROPIC_API_KEY` without `DEEPSEEK_API_KEY`.
- **Impact:** AI review silently fails (returns empty findings). The error is caught and logged in agent_log but the scan completes with zero findings — user is misled into thinking their code has no vulnerabilities.

---

## Production Bugs

### P1. [api/app/routes/auth.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/auth.py#L469) : lines 469-523
- **Issue:** Password reset tokens are stored in an **in-memory dictionary** (`RESET_TOKENS`). In the Docker deployment, the API runs behind uvicorn with `--reload`, and multiple workers could be spawned. The token generated by one worker process won't exist in another. Even with a single worker, container restarts wipe all pending reset tokens.
- **Trigger condition:** User requests password reset, then API container restarts (or different worker handles the reset request).
- **Impact:** Password reset always fails in production. Users are locked out if they forget their password.

### P2. [api/app/services/auth.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/auth.py#L176) : line 176
- **Issue:** Verification codes are stored in an **in-memory dictionary** (`VERIFICATION_CODES`), same problem as P1. In dev mode this is masked because signup auto-verifies (line 103-105 in auth.py routes). In production, the code generated by `generate_verification_code()` would be lost on restart.
- **Trigger condition:** Production mode, user signs up, server restarts before verification.
- **Impact:** Users can never verify their email in production. Permanently locked out of login.

### P3. [api/app/routes/auth.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/auth.py#L220-L239) : lines 220-239
- **Issue:** The GitHub OAuth `/v1/auth/github` endpoint generates a CSRF `state` token but **never stores or validates it**. The state is returned to the client and included in the redirect URL, but when `/v1/auth/github/callback` receives the callback, the `state` parameter is accepted as a query parameter but never verified against any stored value.
- **Trigger condition:** An attacker crafts a malicious callback URL with an arbitrary state value.
- **Impact:** CSRF vulnerability in the OAuth flow. An attacker could potentially trick a user into linking the attacker's GitHub account.

### P4. [api/app/routes/github.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/github.py#L39-L59) : lines 39-59
- **Issue:** Same OAuth state issue as P3 — `github/connect` generates a state token on line 48 but never stores it, and `github/callback` on line 62 accepts any state value without validation.
- **Impact:** Same CSRF risk as P3.

### P5. [api/app/routes/github.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/github.py#L110-L111) : lines 110-111
- **Issue:** GitHub access tokens are "encrypted" using **base64 encoding** (`base64.b64encode`). Base64 is not encryption — it's trivially reversible encoding. The comment on line 109 says "AES-256-GCM in production, base64 for dev" but there is no conditional — base64 is always used.
- **Trigger condition:** Database breach or SQL injection.
- **Impact:** All stored GitHub access tokens are recoverable in plaintext from the database. These tokens grant full `repo` scope access to users' private repositories.

### P6. [api/app/routes/vulns.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/vulns.py#L32-L33) : lines 32-33
- **Issue:** The `status` query parameter name **shadows** the imported `status` from `fastapi` (line 3: `from fastapi import ... status`). Inside the function body, `status` refers to the query parameter string, not `fastapi.status`. This doesn't cause a crash because `fastapi.status` isn't used inside this function, but it masks a potential bug and is a naming collision.
- **Trigger condition:** If someone later adds `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)` inside this function, it would crash because `status` is now a string.
- **Impact:** Latent bug. Currently no functional impact but creates a trap.

### P7. [api/app/routes/vulns.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/vulns.py#L51-L53) : lines 51-53
- **Issue:** Vulnerability sorting uses `Vulnerability.severity.asc()` which sorts alphabetically: `critical < high < info < low < medium`. This means "info" findings appear between "high" and "low", and "critical" appears first only by luck. The intended sort order is by actual severity level.
- **Trigger condition:** Any listing of vulnerabilities with mixed severity levels.
- **Impact:** Vulnerabilities are displayed in wrong priority order. Users may miss critical issues buried among medium/low ones (e.g., on pages with many findings).

### P8. [api/app/services/scanner.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/scanner.py#L224) : line 224
- **Issue:** The dedup logic uses `if f in semgrep_findings` to determine source_agent. This is an **identity check** (`in` on a list of dicts checks by value equality in Python), but the real issue is that `f` is iterating over `semgrep_findings + gitleaks_findings`. When `f` is from `gitleaks_findings`, `f in semgrep_findings` is `False`, so `source_agent` is set to `"gitleaks"` — that's correct. But when `f` is from `semgrep_findings`, `f in semgrep_findings` is `True`, so `source_agent` is `"semgrep"` — also correct. However, line 253 **overrides** `source_agent` to `"ai_reviewer"` for ALL findings, including semgrep and gitleaks findings. So the source_agent attribution is always wrong for safety-net findings.
- **Trigger condition:** Any scan that produces semgrep or gitleaks findings.
- **Impact:** All vulnerability source attribution is lost — everything is labeled "ai_reviewer" regardless of actual source.

### P9. [api/app/routes/billing.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/billing.py#L92-L93) : lines 92-93
- **Issue:** `create_subscription` reads the raw request body via `await request.json()` instead of using a Pydantic schema. The `plan` and `billing_period` fields are extracted with `.get()` with defaults, but there's no validation that the body is valid JSON or has the expected structure. If the request body is not JSON, this will raise an unhandled exception that gets caught by the global handler and returns a generic 500.
- **Trigger condition:** POST to `/v1/billing/subscribe` with non-JSON body or missing Content-Type.
- **Impact:** 500 error instead of 400/422.

### P10. [api/app/routes/auth.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/auth.py#L473) : line 473
- **Issue:** `forgot-password` and `reset-password` endpoints accept a raw `dict` as the body parameter (`body: dict`). FastAPI will try to parse the request body as JSON into a Python dict, but there's no Pydantic validation. Missing fields like `email` will silently become empty strings via `.get("email", "")`. A request with `{}` will proceed to query the DB with an empty email string.
- **Trigger condition:** POST to `/v1/auth/forgot-password` with `{}`.
- **Impact:** Unnecessary DB query with empty string. No crash, but wrong behavior — should return 422 for missing fields.

### P11. [api/app/routes/scans.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/scans.py#L47-L79) : lines 47-79
- **Issue:** Scan limit enforcement has a logic gap. If `user.plan == "pro"`, the entire limit check is skipped (line 47). But `user.plan` is set by the billing flow. During the 7-day trial, `user.plan` is set to `settings.DEV_AUTO_PLAN` which defaults to `"pro"` (config.py:16, .env:7). This means in dev mode, ALL trial users have `plan="pro"` and can run unlimited scans, bypassing the trial limit of 10.
- **Trigger condition:** Dev mode (which is the default). All trial users get unlimited scans.
- **Impact:** In dev mode this is intentional. But if `DEV_AUTO_PLAN` is not changed for production, trial users get unlimited pro-tier scanning.

### P12. [api/app/Dockerfile](file:///c:/Users/adversary/Desktop/CiotxAI/api/Dockerfile#L21) : line 21
- **Issue:** The production Dockerfile runs uvicorn with `--reload` flag. This enables file-watching and auto-restart in production, which is a performance and reliability concern. It also means uvicorn runs in single-worker mode.
- **Trigger condition:** Production deployment using Docker.
- **Impact:** Degraded performance, unnecessary file-system watching, single worker process.

### P13. [dashboard/Dockerfile](file:///c:/Users/adversary/Desktop/CiotxAI/dashboard/Dockerfile#L12) : line 12
- **Issue:** The dashboard Dockerfile runs `npm run dev` which starts Next.js in development mode. In production, this means no static optimization, no code splitting, slower page loads, and development-only error messages exposed to users.
- **Trigger condition:** Production deployment using Docker.
- **Impact:** Poor performance, development error pages visible to end users, potential information disclosure.

### P14. [api/app/routes/scans.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/scans.py#L112-L114) : lines 112-114
- **Issue:** `submit_local_scan` finds or creates a project by matching `Project.name == project_name AND Project.created_by == user.id`. But project names are not unique per user. If two different local scans use the same directory name (e.g., `src`), findings from both scans are merged into the same project. There's no way to distinguish them.
- **Trigger condition:** User runs `ciotx scan --path ./src` on two different projects both named "src".
- **Impact:** Findings from different codebases are mixed together in one project.

---

## Cross-File / API Contract Inconsistencies

### X1. [api/app/schemas/auth.py : line 48](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/schemas/auth.py#L48) vs [api/app/config.py : line 28](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/config.py#L28)
- **Contradiction:** `TokenResponse.expires_in` is hardcoded to `900` (15 minutes) in the schema. `settings.ACCESS_TOKEN_EXPIRE_MINUTES` is `15` (also 15 minutes). These match now, but the schema value is hardcoded and won't update if the config changes. More importantly, the dashboard and CLI use this `expires_in` value to know when to refresh, so a config change would silently break refresh timing.
- **Impact:** Fragile coupling. If `ACCESS_TOKEN_EXPIRE_MINUTES` is changed in config, `expires_in` in responses remains 900, misleading clients.

### X2. [cli/internal/engine/scanner.go : lines 152-158](file:///c:/Users/adversary/Desktop/CiotxAI/cli/internal/engine/scanner.go#L152-L158) vs [api/app/routes/scans.py : lines 143-164](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/scans.py#L143-L164)
- **Contradiction:** The CLI `PushFindings` sends a JSON body with field `"cwe_id"` in each finding (line 126 of scanner.go, `CWEID` json tag is `"cwe_id"`). The API `submit_local_scan` reads `f.get("cwe_id")` on line 154 — this matches. However, the CLI's `FindingPayload` struct has a field `CWEID string json:"cwe_id"` but the source `LLMFinding` struct has `CWEID string json:"cwe_id"` — these match. **No contradiction found here.** But there IS one: the CLI sends `"languages"` and `"duration_ms"` fields that the API endpoint completely ignores — these are silently dropped.
- **Impact:** Minor data loss — scan metadata (languages, duration) from CLI is not stored.

### X3. [api/app/routes/auth.py : line 384](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/auth.py#L384) vs API convention
- **Contradiction:** `cli_verify` takes `user_code` as a **query parameter** (`async def cli_verify(user_code: str, ...)`), not as a JSON body field. All other auth endpoints use JSON request bodies. The CLI and dashboard must know to send `user_code` as a query param (e.g., `POST /v1/auth/cli/verify?user_code=123456`), not in the body.
- **Impact:** Inconsistent API design. If a frontend developer assumes JSON body (like all other POST endpoints), the verify call will fail with a 422.

### X4. [api/app/routes/billing.py : lines 19-37](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/billing.py#L19-L37) vs [dashboard/app/(dashboard)/billing/page.tsx : lines 11-13](file:///c:/Users/adversary/Desktop/CiotxAI/dashboard/app/%28dashboard%29/billing/page.tsx#L11-L13)
- **Contradiction:** The API defines plan features as arrays in `PLANS` dict (e.g., `"features": ["ai_review", "github_connect", ...]`). The dashboard has its own hardcoded `PLAN_FEATURES` dict with human-readable feature strings (e.g., `"20 scans/month"`, `"AI code review"`). These are completely independent — changes to the API plan definition won't propagate to the dashboard.
- **Impact:** If plans change on the API side, the dashboard shows stale feature lists to users.

### X5. [api/app/routes/scans.py : line 53](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/scans.py#L53) vs [api/app/routes/billing.py : line 79](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/billing.py#L79)
- **Contradiction:** Scan limit for "starter" plan is hardcoded in two places with the same value (20) but no shared constant. `scans.py:53` has `scans_limit = 20 if sub.plan == "starter" else -1`. `billing.py:79` has `PLANS.get(sub.plan, {}).get("scans_per_month", 20)`. If someone updates `PLANS["starter"]["scans_per_month"]`, the limit in `scans.py` won't change.
- **Impact:** Potential for inconsistent scan limits between what billing shows and what scan enforcement allows.

### X6. [dashboard/components/Sidebar.tsx : line 17](file:///c:/Users/adversary/Desktop/CiotxAI/dashboard/components/Sidebar.tsx#L17) vs actual Next.js routes
- **Contradiction:** Sidebar links point to `/billing` and `/settings`, but the actual Next.js route files are at `app/(dashboard)/billing/page.tsx` and `app/(dashboard)/settings/page.tsx`. In Next.js 15, the `(dashboard)` route group is a layout grouping that doesn't affect the URL, so `/billing` and `/settings` should resolve correctly. **No bug here** — route groups with parentheses are URL-transparent in Next.js.

### X7. [api/app/services/deepseek.py : line 97](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/deepseek.py#L97) vs [api/app/config.py : line 40](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/config.py#L40)
- **Contradiction:** `deepseek.py:97` checks `if not settings.DEEPSEEK_API_KEY and not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY: return []` — this means if `LLM_PROVIDER` is set to a specific provider but that provider's key is empty, the function silently returns no findings. The `LLM_PROVIDER` config setting is never consulted. The `CUSTOM_API_KEY` and `CUSTOM_BASE_URL` config values are also never used by `deepseek.py`.
- **Impact:** Users who configure `CUSTOM_API_KEY`/`CUSTOM_BASE_URL` (e.g., for Ollama or Groq) as documented in `.env.example` will get zero scan results. The feature doesn't work.

### X8. [cli/internal/engine/llm.go : lines 49-53](file:///c:/Users/adversary/Desktop/CiotxAI/cli/internal/engine/llm.go#L49-L53) vs [api/app/services/deepseek.py : lines 97-100](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/deepseek.py#L97-L100)
- **Contradiction:** The CLI's `NewLLMClient()` checks env vars in order: `CIOTX_API_KEY`, `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. The server's `run_ai_review()` checks `settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY` — a different priority order (DeepSeek > OpenAI > Anthropic). And the CLI has `CIOTX_API_KEY` which the server doesn't support at all. Users configuring only `OPENAI_API_KEY` will get different model selection behavior between CLI and cloud scans.
- **Impact:** Inconsistent scan results between CLI local scans and cloud scans when multiple API keys are configured.

---

## Irrelevant / Minor Issues

| File | Line | Issue |
|------|------|-------|
| [api/app/models/billing.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/models/billing.py#L13) | 13 | `new_uuid()` function duplicated across billing.py, project.py, scan.py, user.py — should be shared |
| [cli/cmd/root.go](file:///c:/Users/adversary/Desktop/CiotxAI/cli/cmd/root.go#L276) | 276 | `min()` function defined locally; Go 1.22 has built-in `min()` |
| [cli/internal/engine/llm.go](file:///c:/Users/adversary/Desktop/CiotxAI/cli/internal/engine/llm.go#L177) | 177 | `min()` function also defined here — duplicate of the one in root.go, and shadows Go 1.22 builtin |
| [cli/cmd/root.go](file:///c:/Users/adversary/Desktop/CiotxAI/cli/cmd/root.go#L191) | 191 | `enginePath` variable assigned on line 191 but never used |
| [api/app/models/project.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/models/project.py#L8) | 8 | `Boolean, Integer, Text` imported but unused |
| [api/app/models/project.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/models/project.py#L10) | 10 | `relationship` imported but unused |
| [api/app/services/deepseek.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/deepseek.py#L8-L9) | 8-9 | `os` and `re` imported; `os` is unused |
| [api/app/services/deepseek.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/deepseek.py#L15) | 15 | `Vulnerability` imported but unused in this file |
| [api/app/routes/github.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/github.py#L7-L8) | 7-8 | `hashlib`, `hmac` imported but unused |
| [api/app/routes/billing.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/routes/billing.py#L3-L5) | 3-5 | `hashlib`, `hmac`, `json` imported but unused |
| [dashboard/app/(dashboard)/dashboard/{[projectId]](file:///c:/Users/adversary/Desktop/CiotxAI/dashboard/app/(dashboard)/dashboard/%7B%5BprojectId%5D) | — | Directory named `{[projectId]` (with curly brace) exists alongside `[projectId]`. This appears to be an accidental duplicate with a typo. It contains subdirectories but no page files — it's dead/orphaned route structure |

---

## Suspected — Needs Verification

### S1. Redis healthcheck in docker-compose.yml : line 29
- **Suspected issue:** The Redis healthcheck uses `redis-cli --raw incr ping`. This runs `INCR ping` which creates a key named "ping" and increments it on every health check. This is a side effect that creates and continuously modifies a key in the production Redis database. Should use `redis-cli ping` instead.
- **What would confirm:** Check Redis for a key named "ping" that keeps incrementing. Also, the `--requirepass` flag is set but the healthcheck doesn't pass the password, so the healthcheck may actually fail every time (Redis 7 with `requirepass` requires authentication for all commands). If so, the container would never reach "healthy" status.
- **Potential impact:** If healthcheck always fails: API and worker containers never start (they depend on `service_healthy`). If it succeeds: unnecessary data pollution.

### S2. Alembic with asyncpg — [api/alembic.ini](file:///c:/Users/adversary/Desktop/CiotxAI/api/alembic.ini#L3) line 3
- **Suspected issue:** `alembic.ini` hardcodes `sqlalchemy.url = postgresql+asyncpg://ciotx:ciotx@localhost:5432/ciotx`. This uses `asyncpg` driver. When running `alembic upgrade head` in `init_db()`, Alembic's `command.upgrade()` runs synchronously. The `migrations/env.py` handles this by using `asyncio.run()` in `run_migrations_online()`. But `init_db()` in database.py is an async function called during FastAPI startup — calling Alembic's synchronous `command.upgrade()` from within an async context may cause event loop conflicts (`asyncio.run()` inside an already-running event loop).
- **What would confirm:** Run the application and check if `init_db()` raises `RuntimeError: This event loop is already running` when Alembic tries `asyncio.run()`.
- **Potential impact:** Database migrations fail on startup, falling back to `create_all` (which doesn't handle schema migrations).

### S3. [api/app/services/scanner.py](file:///c:/Users/adversary/Desktop/CiotxAI/api/app/services/scanner.py#L186-L189) : lines 186-189
- **Suspected issue:** `subprocess.run(["git", "clone", "--depth=1", repo_url, tmpdir])` clones a user-provided repo URL via subprocess. If `repo_url` contains shell metacharacters or is a malicious URL (e.g., `file:///etc/passwd` or an SSH URL with command injection via git), this could be exploitable. `subprocess.run` with a list avoids shell injection, but git itself can be exploited via crafted URLs.
- **What would confirm:** Test with `repo_url = "ext::sh -c 'echo pwned'"` or similar git URL schemes.
- **Potential impact:** Remote code execution on the worker container via crafted repository URL.

---

## Not Reviewed / Skipped

| Path | Reason |
|------|--------|
| `architecture.md` (232KB) | Listed in `.gitignore` as "not part of the codebase" — planning doc |
| `updates.md` (19KB) | Listed in `.gitignore` as "not part of the codebase" — changelog doc |
| `api/app/agents/` | Empty directory |
| `api/app/utils/` | Empty directory |
| `api/app/services/llm/` | Empty directory |
| `api/tests/` | Empty directory |
| `cli/internal/tui/` | Empty directory |
| `dashboard/app/settings/` | Empty directory |
| `sandbox/` | Empty directory |
| `docs/` | Empty directory |
| `node_modules/`, `.git/`, lockfiles | Excluded per instructions |
