# CIOTX QA Test Suite
# Run: powershell -ExecutionPolicy Bypass -File scripts/qa-test.ps1

$API = "http://localhost:8000"
$PASS = 0
$FAIL = 0

function pass($msg) { Write-Host "  [PASS] $msg" -ForegroundColor Green; $global:PASS++ }
function fail($msg, $got) { Write-Host "  [FAIL] $msg (got: $got)" -ForegroundColor Red; $global:FAIL++ }

Write-Host ""
Write-Host "  CIOTX QA Test Suite" -ForegroundColor White
Write-Host "========================================" -ForegroundColor White
Write-Host ""

# 1. Health Check
Write-Host "-- 1. Health Check" -ForegroundColor Yellow
try {
  $r = Invoke-RestMethod -Uri "$API/health" -TimeoutSec 5
  pass "API health: $($r.status)"
} catch {
  fail "API health" $_.Exception.Message
}

# 2. Signup
Write-Host "-- 2. Signup"
$ts = Get-Date -Format "HHmmss"
$body = @{email="qa-$ts@ciotx.io";password="securepass123";name="QA Tester"} | ConvertTo-Json
try {
  $r = Invoke-RestMethod -Uri "$API/v1/auth/signup" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
  pass "Signup: user created"
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 409) {
    pass "Signup: user already exists (409, OK for re-runs)"
  } else {
    fail "Signup" $_.Exception.Message
  }
}

# 3. Temp Email Block
Write-Host "-- 3. Temp Email Detection"
$body = @{email="spam@mailinator.com";password="testpass123"} | ConvertTo-Json
try {
  Invoke-RestMethod -Uri "$API/v1/auth/signup" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
  fail "Disposable email" "should have been rejected"
} catch {
  if ($_.Exception.Message -match "permanent|400") {
    pass "Disposable email blocked"
  } else {
    fail "Disposable email" $_.Exception.Message
  }
}

# 4. Login
Write-Host "-- 4. Login"
$body = @{email="qa-$ts@ciotx.io";password="securepass123"} | ConvertTo-Json
try {
  $r = Invoke-RestMethod -Uri "$API/v1/auth/login" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
  $global:TOKEN = $r.access_token
  $global:REFRESH = $r.refresh_token
  pass "Login: JWT tokens received"
} catch {
  fail "Login" $_.Exception.Message
  Write-Host "  Cannot continue without token. Aborting." -ForegroundColor Red
  exit 1
}

# 5. User Info
Write-Host "-- 5. User Info"
try {
  $r = Invoke-RestMethod -Uri "$API/v1/auth/me" -Headers @{Authorization="Bearer $global:TOKEN"} -TimeoutSec 10
  pass "User info: $($r.email) plan=$($r.plan) status=$($r.plan_status)"
} catch {
  fail "User info" $_.Exception.Message
}

# 6. Invalid Login
Write-Host "-- 6. Invalid Login"
$body = @{email="qa-$ts@ciotx.io";password="wrongpass"} | ConvertTo-Json
try {
  Invoke-RestMethod -Uri "$API/v1/auth/login" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
  fail "Bad password" "should return 401"
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 401) {
    pass "Bad credentials return 401"
  } else {
    fail "Bad password" $_.Exception.Message
  }
}

# 7. Token Refresh
Write-Host "-- 7. Token Refresh"
$body = @{refresh_token=$global:REFRESH} | ConvertTo-Json
try {
  $r = Invoke-RestMethod -Uri "$API/v1/auth/refresh" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
  $global:TOKEN = $r.access_token
  $global:REFRESH = $r.refresh_token
  pass "Token rotation: new pair issued"
} catch {
  fail "Token refresh" $_.Exception.Message
}

# 8. Create Project
Write-Host "-- 8. Create Project"
$body = @{name="qa-test-project";repo_url="https://github.com/ciotx/test"} | ConvertTo-Json
try {
  $r = Invoke-RestMethod -Uri "$API/v1/projects" -Method Post -Body $body -ContentType "application/json" -Headers @{Authorization="Bearer $global:TOKEN"} -TimeoutSec 10
  $global:PROJ_ID = $r.id
  pass "Project created: $($r.id)"
} catch {
  fail "Create project" $_.Exception.Message
}

# 9. List Projects
Write-Host "-- 9. List Projects"
try {
  $r = Invoke-RestMethod -Uri "$API/v1/projects" -Headers @{Authorization="Bearer $global:TOKEN"} -TimeoutSec 10
  pass "Project list: $($r.total) project(s)"
} catch {
  fail "List projects" $_.Exception.Message
}

# 10. Project Detail
Write-Host "-- 10. Project Detail"
try {
  $r = Invoke-RestMethod -Uri "$API/v1/projects/$global:PROJ_ID" -Headers @{Authorization="Bearer $global:TOKEN"} -TimeoutSec 10
  if ($r.name -eq "qa-test-project") {
    pass "Project detail: name matches"
  } else {
    fail "Project detail" "name mismatch: $($r.name)"
  }
} catch {
  fail "Project detail" $_.Exception.Message
}

# 11. Webhook Ping
Write-Host "-- 11. Webhook Ping"
$body = @{zen="test"} | ConvertTo-Json
try {
  $r = Invoke-RestMethod -Uri "$API/v1/webhooks/github" -Method Post -Body $body -ContentType "application/json" -Headers @{"X-GitHub-Event"="ping"} -TimeoutSec 10
  if ($r.message -eq "pong") {
    pass "Webhook: pong received"
  } else {
    fail "Webhook ping" $r.message
  }
} catch {
  fail "Webhook ping" $_.Exception.Message
}

# 12. Auth Required
Write-Host "-- 12. Auth Required"
try {
  Invoke-RestMethod -Uri "$API/v1/projects" -TimeoutSec 10
  fail "Unauthenticated" "should return 401"
} catch {
  $code = $_.Exception.Response.StatusCode.value__
  if ($code -eq 401 -or $code -eq 403) {
    pass "Unauthenticated blocked ($code)"
  } else {
    fail "Auth required" "got $code"
  }
}

# 13. Dashboard
Write-Host "-- 13. Dashboard"
try {
  $r = Invoke-WebRequest -Uri "http://localhost:3000/login" -TimeoutSec 10 -MaximumRedirection 0 -ErrorAction SilentlyContinue
  pass "Dashboard accessible ($($r.StatusCode))"
} catch {
  $code = $_.Exception.Response.StatusCode.value__
  if ($code -eq 200 -or $code -eq 304) {
    pass "Dashboard accessible ($code)"
  } elseif ($null -ne $code) {
    pass "Dashboard accessible ($code)"
  } else {
    fail "Dashboard" "connection failed"
  }
}

# 14. Delete Project
Write-Host "-- 14. Delete Project"
try {
  $r = Invoke-WebRequest -Uri "$API/v1/projects/$global:PROJ_ID" -Method Delete -Headers @{Authorization="Bearer $global:TOKEN"} -TimeoutSec 10
  if ($r.StatusCode -eq 204) {
    pass "Project deleted (204)"
  } else {
    fail "Delete project" $r.StatusCode
  }
} catch {
  fail "Delete project" $_.Exception.Message
}

# 15. All Containers
Write-Host "-- 15. Containers"
$names = @("ciotx-db","ciotx-redis","ciotx-api","ciotx-worker","ciotx-dashboard")
$up = 0
foreach ($n in $names) {
  $status = docker ps --filter "name=$n" --filter "status=running" -q 2>$null
  if ($status) { $up++ }
}
if ($up -eq 5) {
  pass "All 5 containers running"
} else {
  fail "Containers" "$up/5 running"
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor White
$color = if ($FAIL -eq 0) { "Green" } else { "Red" }
Write-Host "  Passed: $PASS  |  Failed: $FAIL" -ForegroundColor $color
Write-Host "========================================" -ForegroundColor White
Write-Host ""

exit $FAIL
