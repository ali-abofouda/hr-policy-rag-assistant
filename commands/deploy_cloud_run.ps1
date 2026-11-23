# ==============================================================================
# deploy_cloud_run.ps1 - Automated Google Cloud Run Deployment (PowerShell)
# ==============================================================================
[CmdletBinding()]
param (
    [string]$ServiceName = "hr-policy-assistant",
    [string]$Region = "us-central1",
    [string]$SecretName = "streamlit-auth"
)

$ErrorActionPreference = "Stop"

$ProjectId = (gcloud config get-value project 2>$null)
if (-not $ProjectId) {
    Write-Error "No active GCP project configured. Run 'gcloud config set project <PROJECT_ID>' first."
}

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Deploying HR Policy RAG Assistant to Google Cloud Run" -ForegroundColor Cyan
Write-Host "Project:  $ProjectId"
Write-Host "Service:  $ServiceName"
Write-Host "Region:   $Region"
Write-Host "==============================================================================" -ForegroundColor Cyan

# 1. Enable APIs
Write-Host "[1/4] Enabling required Google Cloud APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com

# 2. Upload Secrets
Write-Host "[2/4] Uploading Streamlit OAuth secrets to Secret Manager..." -ForegroundColor Yellow
$secretExists = (gcloud secrets describe $SecretName 2>$null)
if (-not $secretExists) {
    gcloud secrets create $SecretName --replication-policy="automatic"
}

if (Test-Path ".streamlit/secrets.toml") {
    gcloud secrets versions add $SecretName --data-file=".streamlit/secrets.toml"
    Write-Host "Mounted .streamlit/secrets.toml to Secret Manager '$SecretName'." -ForegroundColor Green
} else {
    Write-Warning ".streamlit/secrets.toml not found! Deploying without OAuth secrets."
}

# 3. Deploy
Write-Host "[3/4] Building image and deploying to Cloud Run via Cloud Build..." -ForegroundColor Yellow
$deployCmd = @(
    "run", "deploy", $ServiceName,
    "--source", ".",
    "--region", $Region,
    "--allow-unauthenticated",
    "--env-vars-file", "deploy.env.yaml"
)

if (Test-Path ".streamlit/secrets.toml") {
    $deployCmd += "--set-secrets=/app/.streamlit/secrets.toml=${SecretName}:latest"
}

& gcloud @deployCmd

# 4. Service URL and Instructions
Write-Host "[4/4] Deployment completed successfully!" -ForegroundColor Green
$ServiceUrl = (gcloud run services describe $ServiceName --region $Region --format='value(status.url)')

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Live Service URL: $ServiceUrl" -ForegroundColor Green
Write-Host ""
Write-Host "CRITICAL STEP FOR GOOGLE OAUTH:" -ForegroundColor Red
Write-Host "1. Go to Google Cloud Console -> APIs & Services -> Credentials"
Write-Host "2. Edit your OAuth 2.0 Web Client ID"
Write-Host "3. Add this EXACT URL to 'Authorized redirect URIs':"
Write-Host "   $ServiceUrl/oauth2callback" -ForegroundColor Yellow
Write-Host "4. Update .streamlit/secrets.toml with this redirect_uri and re-run:"
Write-Host "   gcloud secrets versions add $SecretName --data-file=.streamlit/secrets.toml"
Write-Host "==============================================================================" -ForegroundColor Cyan
