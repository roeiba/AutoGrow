#!/bin/bash
# Setup GCP for SeedGPT using existing project

set -e

echo "🌱 Setting up GCP for SeedGPT Seed Planter"
echo "=========================================="

# Use existing project
PROJECT_ID="magic-mirror-427812"  # Your current active project
SERVICE_ACCOUNT_NAME="seedgpt-planter"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="./apps/seed-planter-api/gcp-credentials.json"

echo "Using existing project: ${PROJECT_ID}"

# Set active project
gcloud config set project ${PROJECT_ID}

# Step 1: Enable required APIs
echo ""
echo "🔌 Step 1: Enabling required APIs..."
gcloud services enable \
    cloudresourcemanager.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    iam.googleapis.com \
    --project=${PROJECT_ID}
echo "✅ APIs enabled"

# Step 2: Create service account
echo ""
echo "👤 Step 2: Creating service account..."
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} --project=${PROJECT_ID} &>/dev/null; then
    echo "✅ Service account already exists"
else
    gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
        --display-name="SeedGPT Planter Service Account" \
        --project=${PROJECT_ID}
    echo "✅ Service account created"
fi

# Step 3: Grant permissions
echo ""
echo "🔐 Step 3: Granting permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/editor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.admin"

echo "✅ Permissions granted"

# Step 4: Create and download key
echo ""
echo "🔑 Step 4: Creating service account key..."
if [ -f "${KEY_FILE}" ]; then
    echo "⚠️  Key file already exists"
    rm "${KEY_FILE}"
fi

gcloud iam service-accounts keys create ${KEY_FILE} \
    --iam-account=${SERVICE_ACCOUNT_EMAIL} \
    --project=${PROJECT_ID}
echo "✅ Key created at ${KEY_FILE}"

# Step 5: Update .env file
echo ""
echo "📝 Step 5: Updating .env file..."
ENV_FILE="./apps/seed-planter-api/.env"

if [ ! -f "${ENV_FILE}" ]; then
    cp ./apps/seed-planter-api/.env.example ${ENV_FILE}
fi

# Update GCP settings
sed -i.bak "s|^GCP_PROJECT_ID=.*|GCP_PROJECT_ID=${PROJECT_ID}|" ${ENV_FILE} || echo "GCP_PROJECT_ID=${PROJECT_ID}" >> ${ENV_FILE}
sed -i.bak "s|^GCP_CREDENTIALS_PATH=.*|GCP_CREDENTIALS_PATH=gcp-credentials.json|" ${ENV_FILE} || echo "GCP_CREDENTIALS_PATH=gcp-credentials.json" >> ${ENV_FILE}
rm -f ${ENV_FILE}.bak

echo "✅ .env file updated"

# Step 6: Add to .gitignore
echo ""
echo "🔒 Step 6: Securing credentials..."
if ! grep -q "gcp-credentials.json" ./apps/seed-planter-api/.gitignore; then
    echo "" >> ./apps/seed-planter-api/.gitignore
    echo "# GCP Credentials" >> ./apps/seed-planter-api/.gitignore
    echo "gcp-credentials.json" >> ./apps/seed-planter-api/.gitignore
fi
echo "✅ Secured"

# Summary
echo ""
echo "=========================================="
echo "✅ GCP Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Configuration:"
echo "  Project: ${PROJECT_ID}"
echo "  Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo "  Credentials: ${KEY_FILE}"
echo ""
echo "🔐 GitHub Secret (run this):"
echo "  cat ${KEY_FILE} | pbcopy"
echo "  Then create secret 'GCP_CREDENTIALS' at:"
echo "  https://github.com/roeiba/SeedGPT/settings/secrets/actions"
echo ""
