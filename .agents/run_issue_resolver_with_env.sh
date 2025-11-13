#!/bin/bash
# Run issue resolver with environment variables from .env file

set -e  # Exit on error

echo "🚀 Running Issue Resolver with .env configuration"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f ".github/scripts/issue_resolver.py" ]; then
    echo "❌ Error: Must run from project root"
    exit 1
fi

# Load environment from .env file
ENV_FILE="src/claude-agent/.env"
if [ -f "$ENV_FILE" ]; then
    echo "📂 Loading environment from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
    echo "✅ Environment loaded"
else
    echo "❌ Error: $ENV_FILE not found"
    exit 1
fi

# Validate required variables
if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "ghp_your_github_personal_access_token_here" ]; then
    echo "❌ Error: GITHUB_TOKEN not set or still using placeholder"
    echo "Please update GITHUB_TOKEN in $ENV_FILE"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-your_anthropic_api_key_here" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY not set or still using placeholder"
    echo "Please update ANTHROPIC_API_KEY in $ENV_FILE"
    exit 1
fi

# Set REPO_NAME from REPO_URL if not set
if [ -z "$REPO_NAME" ]; then
    # Extract owner/repo from REPO_URL and remove .git suffix
    export REPO_NAME=$(echo "$REPO_URL" | sed -E 's|https?://github.com/([^/]+/[^/]+)(\.git)?$|\1|' | sed 's/\.git$//')
    echo "ℹ️  Extracted REPO_NAME from REPO_URL: $REPO_NAME"
fi

# Set SPECIFIC_ISSUE from ISSUE_NUMBER if provided
if [ -n "$ISSUE_NUMBER" ]; then
    export SPECIFIC_ISSUE="$ISSUE_NUMBER"
    echo "🎯 Using specific issue #$SPECIFIC_ISSUE"
fi

# Set labels to handle
export ISSUE_LABELS_TO_HANDLE="feature,bug,documentation,refactor,test,performance,security,ci/cd,enhancement"
export ISSUE_LABELS_TO_SKIP="wontfix,duplicate,invalid,in-progress"

echo ""
echo "Configuration:"
echo "  REPO_NAME: $REPO_NAME"
echo "  SPECIFIC_ISSUE: ${SPECIFIC_ISSUE:-auto-select}"
echo "  AGENT_MODE: ${AGENT_MODE:-auto}"
echo "  GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."
echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:15}..."
echo ""

# Check if GitPython is installed
echo "🔍 Checking dependencies..."
python3 -c "import git" 2>/dev/null || {
    echo "❌ GitPython not installed"
    echo "Installing GitPython..."
    pip3 install GitPython
}

# Check if claude CLI is installed
if ! command -v claude &> /dev/null; then
    echo "⚠️  Warning: claude CLI not found"
    echo "The script will try to run but may fail if Claude CLI is required"
    echo "Install from: https://code.claude.com/"
    echo ""
fi

# Run the issue resolver
echo "🚀 Running issue resolver..."
echo ""

python3 .github/scripts/issue_resolver.py

echo ""
echo "✅ Issue resolver completed!"
