#!/bin/bash
# Debug script for issue resolver

echo "🔍 Debugging Issue Resolver"
echo "================================"

# Check Python version
echo ""
echo "Python version:"
python3 --version

# Check installed packages
echo ""
echo "Checking required packages:"
python3 -c "import github; print('✅ PyGithub installed')" 2>/dev/null || echo "❌ PyGithub not installed"
python3 -c "import git; print('✅ GitPython installed')" 2>/dev/null || echo "❌ GitPython not installed"
python3 -c "import anyio; print('✅ anyio installed')" 2>/dev/null || echo "❌ anyio not installed"
python3 -c "import anthropic; print('✅ anthropic installed')" 2>/dev/null || echo "❌ anthropic not installed"

# Check environment variables
echo ""
echo "Environment variables:"
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:+set}"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+set}"
echo "REPO_NAME: ${REPO_NAME:-not set}"

# Check git status
echo ""
echo "Git status:"
git status --short

# Check current branch
echo ""
echo "Current branch:"
git branch --show-current

echo ""
echo "================================"
echo "Ready to run issue resolver"
