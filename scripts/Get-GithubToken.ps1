<#
.SYNOPSIS
    Generates a short-lived GitHub App installation token.

.DESCRIPTION
    Reads App ID, Client ID and key-file path from environment variables:
      GITHUB_APP_ID
      GITHUB_CLIENT_ID
      GITHUB_APP_KEY_PATH
    1️⃣  Builds a JWT (10-minute lifetime)
    2️⃣  Lists installations
    3️⃣  Exchanges the JWT for an installation access token
#>

# --- prerequisites -----------------------------------------------------------
# Requires PowerShell 7+ and module 'JWT'
if (-not (Get-Module -ListAvailable -Name JWT)) {
    Write-Host "Installing JWT module..." -ForegroundColor Yellow
    Install-Module JWT -Scope CurrentUser -Force
}

# --- configuration -----------------------------------------------------------
$AppId  = $env:GITHUB_APP_ID
$KeyPath = $env:GITHUB_APP_KEY_PATH

if (-not (Test-Path $KeyPath)) { throw "Key file not found at $KeyPath" }

# --- create JWT --------------------------------------------------------------
$PrivateKey = Get-Content $KeyPath -Raw
$EpochNow = [int][double]::Parse((Get-Date -UFormat %s))
$Payload = @{
    iat = $EpochNow
    exp = $EpochNow + 600   # valid for 10 minutes
    iss = $AppId
}

$JWT = New-JWT -Algorithm RS256 -Payload $Payload -PrivateKey $PrivateKey

# --- get installation id -----------------------------------------------------
$Headers = @{
    "Authorization" = "Bearer $JWT"
    "Accept"        = "application/vnd.github+json"
}
$installations = Invoke-RestMethod -Uri "https://api.github.com/app/installations" -Headers $Headers
if (-not $installations) { throw "No installations found; install the app on at least one repo." }

$InstallationId = $installations[0].id
Write-Host "Installation ID: $InstallationId" -ForegroundColor Cyan

# --- exchange JWT → installation token --------------------------------------
$TokenResponse = Invoke-RestMethod -Method POST `
    -Uri "https://api.github.com/app/installations/$InstallationId/access_tokens" `
    -Headers $Headers

$AccessToken = $TokenResponse.token
$ExpiresAt   = $TokenResponse.expires_at

Write-Host "`n✅ GitHub Installation Token:" -ForegroundColor Green
Write-Host $AccessToken
Write-Host "`nExpires At: $ExpiresAt"

# --- optional: save to a secure temp file -----------------------------------
$tokenFile = "$env:TEMP\github_token.txt"
$AccessToken | Out-File -FilePath $tokenFile -Encoding ASCII -Force
icacls $tokenFile /inheritance:r /grant:r "$env:USERNAME:R" | Out-Null
Write-Host "`nToken saved to $tokenFile (read-only)."
