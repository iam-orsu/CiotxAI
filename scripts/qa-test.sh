#!/bin/bash
# CIOTX QA Test Suite
# Uses docker exec to avoid WSL↔Windows networking issues.
# Run: bash /mnt/c/Users/adversary/Desktop/CiotxAI/scripts/qa-test.sh

set -e
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS=0
FAIL=0
API="docker exec ciotx-api"
CURL="$API curl -s"

pass() { echo -e "${GREEN}✅ PASS${NC} — $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}❌ FAIL${NC} — $1 (got: $2)"; FAIL=$((FAIL+1)); }

echo "══════════════════════════════════════════"
echo "  CIOTX QA Test Suite"
echo "══════════════════════════════════════════"

# ── Step 1: Ensure containers are running ───
echo ""
echo "── Step 1: Checking containers..."
cd /mnt/c/Users/adversary/Desktop/CiotxAI
API_RUNNING=$(docker ps --filter "name=ciotx-api" --filter "status=running" -q)
if [ -z "$API_RUNNING" ]; then
  echo "Containers not running. Starting..."
  docker compose up -d --build 2>&1 | tail -5
else
  echo "Containers already running. Skipping rebuild."
fi
echo "Waiting for API to be ready..."
for i in $(seq 1 20); do
  if $CURL http://localhost:8000/health 2>/dev/null | grep -q 'ok'; then
    echo "API ready after $((i*2))s"
    break
  fi
  sleep 2
done

# ── Step 2: Health Check ───────────────────
echo ""
echo "── Step 2: Health Check"
HEALTH=$($CURL http://localhost:8000/health)
if echo "$HEALTH" | grep -q '"ok"'; then
  pass "API health check"
else
  fail "API health check" "$HEALTH"
fi

# ── Step 3: Signup ─────────────────────────
echo "── Step 3: User Signup"
TIMESTAMP=$(date +%s)
SIGNUP=$($CURL -X POST http://localhost:8000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"qa-${TIMESTAMP}@ciotx.io\",\"password\":\"securepass123\",\"name\":\"QA Tester\"}")
if echo "$SIGNUP" | grep -q '"user_id"'; then
  USER_ID=$(echo "$SIGNUP" | grep -o '"user_id":"[^"]*"' | cut -d'"' -f4)
  pass "Signup — user created"
else
  fail "Signup" "$SIGNUP"
fi

# ── Step 4: Temp Email Block ───────────────
echo "── Step 4: Temp Email Detection"
TEMPM=$($CURL -X POST http://localhost:8000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"spam@mailinator.com","password":"testpass123"}')
if echo "$TEMPM" | grep -q 'permanent email'; then
  pass "Disposable email blocked"
else
  fail "Disposable email block" "$TEMPM"
fi

# ── Step 5: Duplicate Signup ───────────────
echo "── Step 5: Duplicate Detection"
DUP_CODE=$(docker exec ciotx-api curl -s -o /dev/null -w "%{http_code}" -X POST \
  http://localhost:8000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"qa-${TIMESTAMP}@ciotx.io\",\"password\":\"testpass123\"}")
if [ "$DUP_CODE" = "409" ]; then
  pass "Duplicate signup blocked (409)"
else
  fail "Duplicate signup (expected 409)" "$DUP_CODE"
fi

# ── Step 6: Login ──────────────────────────
echo "── Step 6: Login"
LOGIN=$($CURL -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"qa-${TIMESTAMP}@ciotx.io\",\"password\":\"securepass123\"}")
if echo "$LOGIN" | grep -q 'access_token'; then
  TOKEN=$(echo "$LOGIN" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
  REFRESH=$(echo "$LOGIN" | grep -o '"refresh_token":"[^"]*"' | cut -d'"' -f4)
  pass "Login — JWT tokens received"
else
  fail "Login" "$LOGIN"
  echo "Cannot continue without token."
  exit 1
fi

# ── Step 7: Get Current User ───────────────
echo "── Step 7: Authenticated User Info"
ME=$($CURL http://localhost:8000/v1/auth/me -H "Authorization: Bearer $TOKEN")
if echo "$ME" | grep -q '"email"'; then
  PLAN=$(echo "$ME" | grep -o '"plan":"[^"]*"' | cut -d'"' -f4)
  STATUS=$(echo "$ME" | grep -o '"plan_status":"[^"]*"' | cut -d'"' -f4)
  pass "User info — plan=$PLAN, status=$STATUS"
else
  fail "User info" "$ME"
fi

# ── Step 8: Token Refresh ──────────────────
echo "── Step 8: Token Refresh"
REFRESHED=$($CURL -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}")
if echo "$REFRESHED" | grep -q 'access_token'; then
  TOKEN=$(echo "$REFRESHED" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
  REFRESH=$(echo "$REFRESHED" | grep -o '"refresh_token":"[^"]*"' | cut -d'"' -f4)
  pass "Token rotation works"
else
  fail "Token refresh" "$REFRESHED"
fi

# ── Step 9: Invalid Login ──────────────────
echo "── Step 9: Invalid Credentials Blocked"
INVALID_CODE=$(docker exec ciotx-api curl -s -o /dev/null -w "%{http_code}" -X POST \
  http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"qa@ciotx.io","password":"wrongpassword"}')
if [ "$INVALID_CODE" = "401" ]; then
  pass "Bad credentials return 401"
else
  fail "Bad credentials (expected 401)" "$INVALID_CODE"
fi

# ── Step 10: Create Project ────────────────
echo "── Step 10: Create Project"
PROJ=$($CURL -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"qa-test-project","repo_url":"https://github.com/ciotx/test"}')
if echo "$PROJ" | grep -q '"id"'; then
  PROJ_ID=$(echo "$PROJ" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
  pass "Project created"
else
  fail "Create project" "$PROJ"
fi

# ── Step 11: List Projects ─────────────────
echo "── Step 11: List Projects"
LIST=$($CURL http://localhost:8000/v1/projects -H "Authorization: Bearer $TOKEN")
if echo "$LIST" | grep -q '"total"'; then
  TOTAL=$(echo "$LIST" | grep -o '"total":[0-9]*' | cut -d':' -f2)
  pass "Project list — $TOTAL project(s)"
else
  fail "List projects" "$LIST"
fi

# ── Step 12: Get Project Detail ────────────
echo "── Step 12: Project Detail"
DETAIL=$($CURL http://localhost:8000/v1/projects/$PROJ_ID -H "Authorization: Bearer $TOKEN")
if echo "$DETAIL" | grep -q '"name":"qa-test-project"'; then
  pass "Project detail — name matches"
else
  fail "Project detail" "$DETAIL"
fi

# ── Step 13: Webhook Ping ──────────────────
echo "── Step 13: Webhook Receiver"
PING=$($CURL -X POST http://localhost:8000/v1/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: ping" \
  -d '{"zen":"test"}')
if echo "$PING" | grep -q 'pong'; then
  pass "Webhook ping — pong received"
else
  fail "Webhook ping" "$PING"
fi

# ── Step 14: Unauthorized Access ───────────
echo "── Step 14: Auth Required"
NOAUTH=$(docker exec ciotx-api curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/v1/projects)
if [ "$NOAUTH" = "401" ]; then
  pass "Unauthenticated request blocked (401)"
else
  fail "Auth required (expected 401)" "$NOAUTH"
fi

# ── Step 15: Dashboard Running ──────────────
echo "── Step 15: Dashboard"
DASH_CODE=$(docker exec ciotx-dashboard curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/login 2>/dev/null || echo "000")
if [ "$DASH_CODE" = "200" ] || [ "$DASH_CODE" = "307" ]; then
  pass "Dashboard accessible (HTTP $DASH_CODE)"
else
  fail "Dashboard (expected 200)" "$DASH_CODE"
fi

# ── Step 16: Delete Project ────────────────
echo "── Step 16: Delete Project"
DEL_CODE=$($CURL -o /dev/null -w "%{http_code}" -X DELETE \
  http://localhost:8000/v1/projects/$PROJ_ID \
  -H "Authorization: Bearer $TOKEN")
if [ "$DEL_CODE" = "204" ]; then
  pass "Project deleted (204)"
else
  fail "Delete project (expected 204)" "$DEL_CODE"
fi

# ── Step 17: Health Check (all services) ────
echo "── Step 17: All Services Running"
AP=$(docker ps --filter "name=ciotx-api" --filter "status=running" -q)
DB=$(docker ps --filter "name=ciotx-db" --filter "status=running" -q)
RD=$(docker ps --filter "name=ciotx-redis" --filter "status=running" -q)
WK=$(docker ps --filter "name=ciotx-worker" --filter "status=running" -q)
DH=$(docker ps --filter "name=ciotx-dashboard" --filter "status=running" -q)
RUNNING=0; [ -n "$AP" ] && RUNNING=$((RUNNING+1))
[ -n "$DB" ] && RUNNING=$((RUNNING+1))
[ -n "$RD" ] && RUNNING=$((RUNNING+1))
[ -n "$WK" ] && RUNNING=$((RUNNING+1))
[ -n "$DH" ] && RUNNING=$((RUNNING+1))
if [ $RUNNING -eq 5 ]; then
  pass "All 5 containers running"
else
  fail "Container count (expected 5)" "$RUNNING/5 running"
fi

# ── Summary ─────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo -e "  ${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}"
echo "══════════════════════════════════════════"
[ $FAIL -gt 0 ] && exit 1 || exit 0
