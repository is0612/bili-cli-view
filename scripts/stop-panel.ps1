# Stop the panel backend (and its scheduler). Autostart will bring it back on next logon.
$conn = Get-NetTCPConnection -LocalPort 8811 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $conn) { Write-Host 'panel is not running.'; exit 0 }
$procId = $conn.OwningProcess
Write-Host "stopping panel (pid $procId) ..."
Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
if (Get-NetTCPConnection -LocalPort 8811 -State Listen -ErrorAction SilentlyContinue) {
  Write-Host 'port 8811 is still listening (held by another process?)'
} else {
  Write-Host 'stopped.'
}
