#!/usr/bin/env bash
# ==============================================================================
# deploy_cloud_run.sh - One-Command Automated Google Cloud Run Deployment
# ==============================================================================
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-hr-policy-assistant}"
REGION="${REGION:-us-central1}"
SECRET_NAME="${SECRET_NAME:-streamlit-auth}"
PROJECT_ID="$(gcloud config get-value project 2>/dev/null || echo "")"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Error: No active GCP project configured. Run 'gcloud config set project <PROJECT_ID>' first."
  exit 1
fi

echo "=============================================================================="
echo "Deploying HR Policy RAG Assistant to Google Cloud Run"
echo "Project:  ${PROJECT_ID}"
echo "Service:  ${SERVICE_NAME}"
echo "Region:   ${REGION}"
echo "=============================================================================="

# 1. Enable required GCP service APIs
echo "[1/4] Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com

# 2. Manage Secret in Secret Manager
echo "[2/4] Uploading Streamlit OAuth secrets to Secret Manager..."
if ! gcloud secrets describe "${SECRET_NAME}" >/dev/null 2>&1; then
  gcloud secrets create "${SECRET_NAME}" --replication-policy="automatic"
fi

if [[ -f ".streamlit/secrets.toml" ]]; then
  gcloud secrets versions add "${SECRET_NAME}" --data-file=".streamlit/secrets.toml"
  echo "Mounted .streamlit/secrets.toml to Secret Manager '${SECRET_NAME}'."
else
  echo "Warning: .streamlit/secrets.toml not found! Deploying without OAuth secrets."
fi

# 3. Build and Deploy Container to Cloud Run
echo "[3/4] Building image and deploying to Cloud Run via Cloud Build..."
DEPLOY_ARGS=(
  "run" "deploy" "${SERVICE_NAME}"
  "--source" "."
  "--region" "${REGION}"
  "--allow-unauthenticated"
  "--env-vars-file" "deploy.env.yaml"
)

if [[ -f ".streamlit/secrets.toml" ]]; then
  DEPLOY_ARGS+=("--set-secrets=/app/.streamlit/secrets.toml=${SECRET_NAME}:latest")
fi

gcloud "${DEPLOY_ARGS[@]}"

# 4. Display service URL and OAuth configuration instructions
echo "[4/4] Deployment successful!"
SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format='value(status.url)')"

echo "=============================================================================="
echo "Live Service URL: ${SERVICE_URL}"
echo ""
echo "CRITICAL STEP FOR GOOGLE OAUTH:"
echo "1. Go to Google Cloud Console -> APIs & Services -> Credentials"
echo "2. Edit your OAuth 2.0 Web Client ID"
echo "3. Add this EXACT URL to 'Authorized redirect URIs':"
echo "   ${SERVICE_URL}/oauth2callback"
echo "4. Update .streamlit/secrets.toml with this redirect_uri and re-run:"
echo "   gcloud secrets versions add ${SECRET_NAME} --data-file=.streamlit/secrets.toml"
echo "=============================================================================="
