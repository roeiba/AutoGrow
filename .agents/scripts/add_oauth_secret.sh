#!/bin/bash

# Script to add GitHub OAuth Client Secret to GCP Secret Manager
# This secret is needed for the OAuth token exchange endpoint

set -e

echo "🔐 Adding GitHub OAuth Client Secret to GCP Secret Manager"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "   Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get the project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project configured"
    echo "   Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Current GCP Project: $PROJECT_ID"
echo ""

# Prompt for the OAuth client secret
echo "Please enter your GitHub OAuth App Client Secret:"
echo "(You can find this at: https://github.com/settings/apps)"
echo ""
read -s -p "Client Secret: " CLIENT_SECRET
echo ""

if [ -z "$CLIENT_SECRET" ]; then
    echo "❌ Error: Client secret cannot be empty"
    exit 1
fi

# Create or update the secret
SECRET_NAME="GITHUB_OAUTH_CLIENT_SECRET"

echo ""
echo "Creating/updating secret: $SECRET_NAME"

# Check if secret exists
if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
    echo "Secret already exists, adding new version..."
    echo -n "$CLIENT_SECRET" | gcloud secrets versions add $SECRET_NAME \
        --project=$PROJECT_ID \
        --data-file=-
else
    echo "Creating new secret..."
    echo -n "$CLIENT_SECRET" | gcloud secrets create $SECRET_NAME \
        --project=$PROJECT_ID \
        --data-file=- \
        --replication-policy="automatic"
fi

echo ""
echo "✅ Secret added successfully!"
echo ""
echo "Next steps:"
echo "1. Update the Cloud Run service to use this secret:"
echo "   gcloud run services update seed-planter-api \\"
echo "     --region us-central1 \\"
echo "     --update-secrets GITHUB_OAUTH_CLIENT_SECRET=$SECRET_NAME:latest"
echo ""
echo "2. Or add to the deployment workflow in .github/workflows/apps-seed-planter-api.yml"
echo ""
