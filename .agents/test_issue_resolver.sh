#!/bin/bash
# Test script for issue resolver - runs locally with test issue

set -e  # Exit on error

echo "🧪 Testing Issue Resolver Locally"
echo "=================================="

# Check if we're in the right directory
if [ ! -f ".github/scripts/issue_resolver.py" ]; then
    echo "❌ Error: Must run from project root"
    exit 1
fi

# Check required environment variables
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Error: GITHUB_TOKEN not set"
    echo "Set it with: export GITHUB_TOKEN=your_token"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY not set"
    echo "Set it with: export ANTHROPIC_API_KEY=your_key"
    exit 1
fi

# Set default REPO_NAME if not set
if [ -z "$REPO_NAME" ]; then
    export REPO_NAME="roeiba/autoGrow"
    echo "ℹ️  Using default REPO_NAME: $REPO_NAME"
fi

# Set test issue if provided
if [ -n "$1" ]; then
    export SPECIFIC_ISSUE="$1"
    echo "🎯 Testing with specific issue #$SPECIFIC_ISSUE"
fi

# Set labels to handle
export ISSUE_LABELS_TO_HANDLE="feature,bug,documentation,refactor,test,performance,security,ci/cd,enhancement"
export ISSUE_LABELS_TO_SKIP="wontfix,duplicate,invalid,in-progress"

echo ""
echo "Configuration:"
echo "  REPO_NAME: $REPO_NAME"
echo "  SPECIFIC_ISSUE: ${SPECIFIC_ISSUE:-auto-select}"
echo "  LABELS_TO_HANDLE: $ISSUE_LABELS_TO_HANDLE"
echo ""

# Run the issue resolver
echo "🚀 Running issue resolver..."
echo ""

python3 .github/scripts/issue_resolver.py

echo ""
echo "✅ Test complete!"
