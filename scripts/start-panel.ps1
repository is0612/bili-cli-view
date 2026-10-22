# Start the panel backend at logon. Idempotent: if it is already up, do nothing.
# Called by the scheduled task "bili-desk" (hidden window).
$root = Split-Path $PSScriptRoot -Parent
# Personal data lives outside the repo: %APPDATA%\bili-desk (or BILI_DESK_HOME).
$dataHome = if ($env:BILI_DESK_HOME) { $env:BILI_DESK_HOME } else { Join-Path $env:APPDATA 'bili-desk' }
$logDir = Join-Path $dataHome 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'panel.log'

function Write-Log($msg) {
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Out-File -FilePath $log -Append -Encoding utf8
}

# 1) already alive? then do nothing
try {
  $r = Invoke-WebRequest 'http://127.0.0.1:8811/api/ping' -UseBasicParsing -TimeoutSec 3
  if ($r.StatusCode -eq 200) { Write-Log 'already running, skip'; exit 0 }
} catch {
  # not running - fall through
}

# 2) start backend (pythonw: no console window; output goes to log files)
$py = Join-Path $root '.venv\Scripts\pythonw.exe'
if (-not (Test-Path $py)) { $py = Join-Path $root '.venv\Scripts\python.exe' }
if (-not (Test-Path $py)) { Write-Log "python not found: $py"; exit 1 }

Write-Log "starting panel: $py"
Start-Process -FilePath $py -WorkingDirectory $root `
  -ArgumentList '-m', 'uvicorn', 'app.main:app', '--port', '8811', '--app-dir', 'backend' `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $logDir 'panel.out.log') `
  -RedirectStandardError (Join-Path $logDir 'panel.err.log')

# 3) wait until it answers
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Milliseconds 500
  try {
    $r = Invoke-WebRequest 'http://127.0.0.1:8811/api/ping' -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { Write-Log 'panel up'; exit 0 }
  } catch {
    # keep waiting
  }
}
Write-Log 'panel did not come up in 15s'
exit 1
