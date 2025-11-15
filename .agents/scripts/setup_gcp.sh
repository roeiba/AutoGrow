#!/bin/bash
# Setup GCP for SeedGPT Seed Planter

set -e

echo "🌱 Setting up GCP for SeedGPT Seed Planter"
echo "=========================================="

# Configuration
PROJECT_ID="seedgpt-planter"
SERVICE_ACCOUNT_NAME="seedgpt-planter"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="./apps/seed-planter-api/gcp-credentials.json"

# Step 1: Create project
echo ""
echo "📦 Step 1: Creating GCP project '${PROJECT_ID}'..."
if gcloud projects describe ${PROJECT_ID} &>/dev/null; then
    echo "✅ Project already exists"
else
    gcloud projects create ${PROJECT_ID} \
        --name="SeedGPT Planter" \
        --set-as-default
    echo "✅ Project created"
fi

# Set active project
gcloud config set project ${PROJECT_ID}

# Step 2: Enable required APIs
echo ""
echo "🔌 Step 2: Enabling required APIs..."
gcloud services enable \
    cloudresourcemanager.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    iam.googleapis.com \
    --project=${PROJECT_ID}
echo "✅ APIs enabled"

# Step 3: Create service account
echo ""
echo "👤 Step 3: Creating service account..."
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} --project=${PROJECT_ID} &>/dev/null; then
    echo "✅ Service account already exists"
else
    gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
        --display-name="SeedGPT Planter Service Account" \
        --project=${PROJECT_ID}
    echo "✅ Service account created"
fi

# Step 4: Grant permissions
echo ""
echo "🔐 Step 4: Granting permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/editor" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.admin" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.admin" \
    --condition=None

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/cloudbuild.builds.editor" \
    --condition=None

echo "✅ Permissions granted"

# Step 5: Create and download key
echo ""
echo "🔑 Step 5: Creating service account key..."
if [ -f "${KEY_FILE}" ]; then
    echo "⚠️  Key file already exists at ${KEY_FILE}"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping key creation"
    else
        rm "${KEY_FILE}"
        gcloud iam service-accounts keys create ${KEY_FILE} \
            --iam-account=${SERVICE_ACCOUNT_EMAIL} \
            --project=${PROJECT_ID}
        echo "✅ New key created"
    fi
else
    gcloud iam service-accounts keys create ${KEY_FILE} \
        --iam-account=${SERVICE_ACCOUNT_EMAIL} \
        --project=${PROJECT_ID}
    echo "✅ Key created at ${KEY_FILE}"
fi

# Step 6: Update .env file
echo ""
echo "📝 Step 6: Updating .env file..."
ENV_FILE="./apps/seed-planter-api/.env"

if [ ! -f "${ENV_FILE}" ]; then
    cp ./apps/seed-planter-api/.env.example ${ENV_FILE}
    echo "✅ Created .env from .env.example"
fi

# Update GCP settings in .env
if grep -q "^GCP_PROJECT_ID=" ${ENV_FILE}; then
    sed -i.bak "s|^GCP_PROJECT_ID=.*|GCP_PROJECT_ID=${PROJECT_ID}|" ${ENV_FILE}
else
    echo "GCP_PROJECT_ID=${PROJECT_ID}" >> ${ENV_FILE}
fi

if grep -q "^GCP_CREDENTIALS_PATH=" ${ENV_FILE}; then
    sed -i.bak "s|^GCP_CREDENTIALS_PATH=.*|GCP_CREDENTIALS_PATH=gcp-credentials.json|" ${ENV_FILE}
else
    echo "GCP_CREDENTIALS_PATH=gcp-credentials.json" >> ${ENV_FILE}
fi

rm -f ${ENV_FILE}.bak

echo "✅ .env file updated"

# Step 7: Add to .gitignore
echo ""
echo "🔒 Step 7: Securing credentials..."
if ! grep -q "gcp-credentials.json" ./apps/seed-planter-api/.gitignore; then
    echo "" >> ./apps/seed-planter-api/.gitignore
    echo "# GCP Credentials" >> ./apps/seed-planter-api/.gitignore
    echo "gcp-credentials.json" >> ./apps/seed-planter-api/.gitignore
    echo "✅ Added to .gitignore"
else
    echo "✅ Already in .gitignore"
fi

# Summary
echo ""
echo "=========================================="
echo "✅ GCP Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Summary:"
echo "  Project ID: ${PROJECT_ID}"
echo "  Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo "  Credentials: ${KEY_FILE}"
echo "  .env updated: ${ENV_FILE}"
echo ""
echo "🔐 GitHub Secret Setup:"
echo "  1. Copy the credentials file content:"
echo "     cat ${KEY_FILE} | pbcopy"
echo "  2. Go to: https://github.com/roeiba/SeedGPT/settings/secrets/actions"
echo "  3. Create new secret: GCP_CREDENTIALS"
echo "  4. Paste the content"
echo ""
echo "🚀 Next steps:"
echo "  1. Test locally: cd apps/seed-planter-api/src && python main.py"
echo "  2. Upload GCP_CREDENTIALS to GitHub secrets"
echo "  3. Deploy!"
echo ""
