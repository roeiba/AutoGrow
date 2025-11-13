#!/bin/bash

# Set GitHub Secrets from .env files
# Usage: ./set_github_secrets.sh [repo]

set -e

REPO="${1:-roeiba/autoGrow}"

echo "🔐 Setting GitHub Secrets for repository: $REPO"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

# Function to set secret from .env file
set_secret_from_env() {
    local env_file="$1"
    local secret_name="$2"
    
    if [ ! -f "$env_file" ]; then
        echo "⚠️  Warning: $env_file not found, skipping $secret_name"
        return
    fi
    
    local value=$(grep "^${secret_name}=" "$env_file" | cut -d'=' -f2-)
    
    if [ -z "$value" ]; then
        echo "⚠️  Warning: $secret_name not found in $env_file"
        return
    fi
    
    echo "$value" | gh secret set "$secret_name" --repo "$REPO"
    echo "✅ Set $secret_name"
}

# Set Gemini secrets
echo "📦 Setting Gemini secrets..."
set_secret_from_env "src/gemini-agent/.env" "GEMINI_API_KEY"
set_secret_from_env "src/gemini-agent/.env" "GOOGLE_CLOUD_PROJECT"

# Set Claude/Anthropic secrets
echo ""
echo "📦 Setting Claude/Anthropic secrets..."
set_secret_from_env "src/claude-agent/.env" "ANTHROPIC_API_KEY"

# Set GitHub token if exists
echo ""
echo "📦 Setting GitHub secrets..."
set_secret_from_env "src/claude-agent/.env" "GITHUB_TOKEN"

echo ""
echo "🎉 Done! Verifying secrets..."
echo ""

# List all secrets
gh secret list --repo "$REPO"

echo ""
echo "✅ All secrets have been set successfully!"
echo ""
echo "Note: Secret values are not displayed for security reasons."
echo "You can verify they work by running the GitHub Actions workflow."
