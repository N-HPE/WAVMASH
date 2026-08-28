# Wait until production frontend + backend respond (after git push).
# Usage: powershell -File scripts/wait-for-deploy.ps1

$Frontend = "https://wavmash.vercel.app"
$Backend = "https://wavmash-backend.onrender.com/health"
$MaxTries = 40
$DelaySec = 15

Write-Host "Waiting for Render: $Backend"
for ($i = 1; $i -le $MaxTries; $i++) {
  try {
    $r = Invoke-WebRequest -Uri $Backend -UseBasicParsing -TimeoutSec 20
    if ($r.StatusCode -eq 200 -and $r.Content -match "ok") {
      Write-Host "[OK] Backend live ($i)"
      break
    }
  } catch {}
  Write-Host "[$i/$MaxTries] backend not ready..."
  if ($i -eq $MaxTries) { throw "Backend timeout" }
  Start-Sleep -Seconds $DelaySec
}

Write-Host "Waiting for Vercel: $Frontend"
for ($i = 1; $i -le $MaxTries; $i++) {
  try {
    $r = Invoke-WebRequest -Uri $Frontend -UseBasicParsing -TimeoutSec 20
    if ($r.StatusCode -eq 200) {
      Write-Host "[OK] Frontend live ($i)"
      Write-Host "Refresh $Frontend to monitor."
      exit 0
    }
  } catch {}
  Write-Host "[$i/$MaxTries] frontend not ready..."
  if ($i -eq $MaxTries) { throw "Frontend timeout" }
  Start-Sleep -Seconds $DelaySec
}
