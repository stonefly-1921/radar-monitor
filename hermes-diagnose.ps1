# hermes-diagnose.ps1 - Hermes 0.14 + Windows + Feishu quick diagnostic
# Usage: powershell -ExecutionPolicy Bypass -File hermes-diagnose.ps1

$ErrorActionPreference = "Continue"
$LOC = "$env:LOCALAPPDATA\hermes\logs"
$ENV_FILE = "$env:LOCALAPPDATA\hermes\.env"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Hermes Diagnostic $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 1/5: Log check
Write-Host "[1/5] Checking logs..." -ForegroundColor Yellow
if (Test-Path "$LOC\gateway.log") {
    $gatewayLog = Get-Content "$LOC\gateway.log" -Tail 50 -ErrorAction SilentlyContinue
    $lines = $gatewayLog | Select-Object -Last 50

    $sslErr = $lines | Where-Object { $_ -match "SSL|certificate|verify failed" }
    $notAllowed = $lines | Where-Object { $_ -match "user not allowed|not allowed" }
    $noEvent = $lines | Where-Object { $_ -match "no event subscription|event" }
    $connected = $lines | Where-Object { $_ -match "Lark.*connected|websocket.*open" }
    $received = $lines | Where-Object { $_ -match "im\.message\.receive|receive.*message" }
    $send = $lines | Where-Object { $_ -match "send.*message|reply" }
    $timeout = $lines | Where-Object { $_ -match "timeout|Timed out" }
    $apiKeyErr = $lines | Where-Object { $_ -match "API.*key|invalid.*key|401|403" }

    if ($sslErr) {
        Write-Host "  [SSL] Certificate verify failed - set HERMES_SSL_VERIFY=false" -ForegroundColor Red
        foreach ($line in $sslErr) { Write-Host "    $line" -ForegroundColor DarkGray }
    }
    if ($notAllowed) {
        Write-Host "  [WHITELIST] User blocked - set GATEWAY_ALLOW_ALL_USERS=true" -ForegroundColor Red
    }
    if ($noEvent) {
        Write-Host "  [EVENTS] No subscription - add im.message.receive_v1 in Feishu console" -ForegroundColor Red
    }
    if ($connected) {
        Write-Host "  [CONNECTION] WebSocket: ESTABLISHED" -ForegroundColor Green
    } else {
        Write-Host "  [CONNECTION] WebSocket: NOT connected" -ForegroundColor Red
    }
    if ($received) {
        Write-Host "  [MESSAGE] Received: YES" -ForegroundColor Green
    } else {
        Write-Host "  [MESSAGE] Received: NO (check Feishu event subscription)" -ForegroundColor Yellow
    }
    if ($send) {
        Write-Host "  [REPLY] Sent reply: YES" -ForegroundColor Green
    }
    if ($timeout) {
        Write-Host "  [TIMEOUT] Timeout detected" -ForegroundColor Yellow
    }
    if ($apiKeyErr) {
        Write-Host "  [API KEY] Auth error - check model key" -ForegroundColor Red
    }
    if (-not $sslErr -and -not $notAllowed -and -not $noEvent -and -not $timeout -and -not $apiKeyErr -and $connected) {
        Write-Host "  No obvious errors detected in recent logs" -ForegroundColor Green
    }
} else {
    Write-Host "  Log file not found - is hermes running?" -ForegroundColor Red
}

Write-Host ""

# 2/5: .env check
Write-Host "[2/5] Checking .env config..." -ForegroundColor Yellow
$envIssues = @()
if (Test-Path $ENV_FILE) {
    $envContent = Get-Content $ENV_FILE -ErrorAction SilentlyContinue
    $envDict = @{}
    foreach ($line in $envContent) {
        if ($line -match "^(.+?)=(.*)$") {
            $envDict[$matches[1].Trim()] = $matches[2].Trim()
        }
    }

    $checkList = @{
        "HERMES_SSL_VERIFY"       = "SSL verify (recommend false on Windows)";
        "GATEWAY_ALLOW_ALL_USERS" = "User whitelist (set true to test)";
        "HERMES_API_KEY"         = "Model API Key";
    }

    foreach ($key in $checkList.Keys) {
        if ($envDict.ContainsKey($key)) {
            $val = $envDict[$key]
            Write-Host "  $key = $val" -ForegroundColor Green
        } else {
            Write-Host "  $key = (not set) - $($checkList[$key])" -ForegroundColor DarkYellow
            $envIssues += $key
        }
    }
} else {
    Write-Host "  .env file not found: $ENV_FILE" -ForegroundColor Red
}

Write-Host ""

# 3/5: Process & port check
Write-Host "[3/5] Checking process & ports..." -ForegroundColor Yellow
$hermesProc = Get-Process -Name "hermes" -ErrorAction SilentlyContinue
if ($hermesProc) {
    Write-Host "  hermes process running (PID: $($hermesProc.Id))" -ForegroundColor Green
} else {
    Write-Host "  No hermes process found" -ForegroundColor Red
}

$listeningPorts = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in @(9000, 8080, 8000) } |
    Select-Object LocalPort, OwningProcess
if ($listeningPorts) {
    Write-Host "  Listening ports:"
    foreach ($p in $listeningPorts) {
        $proc = Get-Process -Id $p.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "    $($p.LocalPort) <- PID $($p.OwningProcess) $($proc.ProcessName)" -ForegroundColor Cyan
    }
} else {
    Write-Host "  No hermes listening ports found (9000/8080/8000)" -ForegroundColor Yellow
}

Write-Host ""

# 4/5: Feishu console checklist
Write-Host "[4/5] Feishu console checklist" -ForegroundColor Yellow
Write-Host "  [ ] Events > Add im.message.receive_v1 > Publish version" -ForegroundColor White
Write-Host "  [ ] Permissions > im:message or higher" -ForegroundColor White
Write-Host "  [ ] App settings > Verify App ID and App Secret" -ForegroundColor White

Write-Host ""

# 5/5: Version info
Write-Host "[5/5] Version info..." -ForegroundColor Yellow
try {
    $version = hermes --version 2>&1
    Write-Host "  Hermes version: $version" -ForegroundColor Cyan
} catch {
    Write-Host "  Cannot get version (hermes not in PATH)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Diagnostic complete" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick fixes:" -ForegroundColor White
Write-Host "  Disable SSL:    [Environment]::SetEnvironmentVariable('HERMES_SSL_VERIFY','false','User')" -ForegroundColor DarkGray
Write-Host "  Allow users:     Add GATEWAY_ALLOW_ALL_USERS=true to .env" -ForegroundColor DarkGray
Write-Host "  Restart gateway: hermes gateway restart" -ForegroundColor DarkGray
Write-Host "  Upgrade 0.15+:  npm i -g hermes-ai@latest" -ForegroundColor DarkGray