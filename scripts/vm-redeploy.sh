#!/bin/bash
# Runs on the VM to redeploy the bot after a new image was pushed.
set -euxo pipefail

PROJECT="autoreitbuch-bot"
REGION="us-central1"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/autoreitbuch/bot:latest"

docker pull "$IMAGE"
docker stop autoreitbuch-bot 2>/dev/null || true
docker rm   autoreitbuch-bot 2>/dev/null || true

TELEGRAM_TOKEN=$(gcloud secrets versions access latest --secret=TELEGRAM_TOKEN --project="$PROJECT")
TELEGRAM_CHAT_ID=$(gcloud secrets versions access latest --secret=TELEGRAM_CHAT_ID --project="$PROJECT")
REITBUCH_USER=$(gcloud secrets versions access latest --secret=REITBUCH_USER --project="$PROJECT")
REITBUCH_PASSWORD=$(gcloud secrets versions access latest --secret=REITBUCH_PASSWORD --project="$PROJECT")

docker run -d \
  --name autoreitbuch-bot \
  --restart always \
  -e TELEGRAM_TOKEN="$TELEGRAM_TOKEN" \
  -e TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID" \
  -e REITBUCH_USER="$REITBUCH_USER" \
  -e REITBUCH_PASSWORD="$REITBUCH_PASSWORD" \
  "$IMAGE"

echo "✅ Bot redeployed successfully"
