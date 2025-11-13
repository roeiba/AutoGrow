# GitHub Secrets Management

Guide for managing GitHub repository secrets for CI/CD workflows.

## 🔐 Current Secrets

The following secrets are configured in the repository:

| Secret Name | Purpose | Required For |
|------------|---------|--------------|
| `GEMINI_API_KEY` | Gemini API authentication | Integration tests (Gemini) |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID | Gemini API calls |
| `ANTHROPIC_API_KEY` | Anthropic API authentication | Integration tests (Claude) |
| `GITHUB_TOKEN` | GitHub API authentication | Issue resolver workflow |

## ✅ Secrets Set

Current status (as of last update):

```
✓ GEMINI_API_KEY        - Set
✓ GOOGLE_CLOUD_PROJECT  - Set  
✓ ANTHROPIC_API_KEY     - Set
```

## 🚀 Quick Setup

### Using the Script (Recommended)

```bash
# Set all secrets from .env files
./.agents/scripts/set_github_secrets.sh

# Or specify a different repository
./.agents/scripts/set_github_secrets.sh owner/repo-name
```

### Manual Setup

```bash
# Set Gemini API Key
echo "your-gemini-api-key" | gh secret set GEMINI_API_KEY

# Set Google Cloud Project
echo "your-project-id" | gh secret set GOOGLE_CLOUD_PROJECT

# Set Anthropic API Key
echo "your-anthropic-api-key" | gh secret set ANTHROPIC_API_KEY
```

## 📋 Prerequisites

### 1. Install GitHub CLI

```bash
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

### 2. Authenticate

```bash
gh auth login
```

Follow the prompts to authenticate with GitHub.

### 3. Verify Authentication

```bash
gh auth status
```

## 🔑 Getting API Keys

### Gemini API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with `AIza...`)
5. Add to `src/gemini-agent/.env`:
   ```bash
   GEMINI_API_KEY=AIza...your-key-here
   ```

### Google Cloud Project

1. Visit: https://console.cloud.google.com/
2. Select or create a project
3. Note the Project ID
4. Add to `src/gemini-agent/.env`:
   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   ```

### Anthropic API Key

1. Visit: https://console.anthropic.com/
2. Sign in or create an account
3. Go to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)
6. Add to `src/claude-agent/.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-...your-key-here
   ```

## 📝 Setting Secrets

### Method 1: Using the Script

```bash
# Make sure .env files are configured
cd /path/to/autoGrow

# Run the script
./.agents/scripts/set_github_secrets.sh

# Output:
# 🔐 Setting GitHub Secrets for repository: roeiba/autoGrow
# 
# 📦 Setting Gemini secrets...
# ✅ Set GEMINI_API_KEY
# ✅ Set GOOGLE_CLOUD_PROJECT
# 
# 📦 Setting Claude/Anthropic secrets...
# ✅ Set ANTHROPIC_API_KEY
# 
# 🎉 Done! Verifying secrets...
```

### Method 2: Manual via GitHub CLI

```bash
# Set individual secrets
echo "your-api-key" | gh secret set GEMINI_API_KEY --repo roeiba/autoGrow
echo "your-project-id" | gh secret set GOOGLE_CLOUD_PROJECT --repo roeiba/autoGrow
echo "your-api-key" | gh secret set ANTHROPIC_API_KEY --repo roeiba/autoGrow
```

### Method 3: Via GitHub Web UI

1. Go to repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter name and value
5. Click **Add secret**

## 🔍 Verifying Secrets

### List All Secrets

```bash
gh secret list --repo roeiba/autoGrow
```

Output:
```
NAME                  UPDATED               
ANTHROPIC_API_KEY     about 1 hour ago
GEMINI_API_KEY        less than a minute ago
GOOGLE_CLOUD_PROJECT  less than a minute ago
```

### Test in Workflow

1. Go to **Actions** tab on GitHub
2. Select **Test AI Agents** workflow
3. Click **Run workflow**
4. Enable **Run integration tests**
5. Click **Run workflow**
6. Check if tests pass

## 🔄 Updating Secrets

### Update via Script

```bash
# Update .env files with new values
vim src/gemini-agent/.env
vim src/claude-agent/.env

# Run script to update all secrets
./.agents/scripts/set_github_secrets.sh
```

### Update via CLI

```bash
# Update individual secret
echo "new-api-key" | gh secret set GEMINI_API_KEY --repo roeiba/autoGrow
```

## 🗑️ Removing Secrets

```bash
# Remove a secret
gh secret remove GEMINI_API_KEY --repo roeiba/autoGrow
```

## 🔒 Security Best Practices

### 1. Never Commit Secrets

```bash
# Make sure .env files are in .gitignore
cat .gitignore | grep ".env"

# Output should include:
# .env
# *.env
# !.env.example
```

### 2. Use .env.example

```bash
# Create example files without real values
cp src/gemini-agent/.env src/gemini-agent/.env.example

# Remove actual values
sed -i '' 's/=.*/=your-key-here/' src/gemini-agent/.env.example
```

### 3. Rotate Keys Regularly

- Rotate API keys every 90 days
- Update secrets after rotation
- Test workflows after updating

### 4. Limit Secret Access

- Only set secrets needed for CI/CD
- Use environment-specific secrets when possible
- Review secret usage in workflows

## 📊 Secret Usage in Workflows

### test-agents.yml

```yaml
test-integration:
  steps:
    - name: Run CI integration flow
      env:
        GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: make ci-integration-flow
```

### issue-resolver.yml

```yaml
steps:
  - name: Run Issue Resolver
    env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    run: python src/agentic_workflow.py
```

## 🐛 Troubleshooting

### Secret Not Found

**Issue**: Workflow fails with "secret not found"

**Solution**:
```bash
# Verify secret exists
gh secret list --repo roeiba/autoGrow

# If missing, set it
echo "your-key" | gh secret set SECRET_NAME --repo roeiba/autoGrow
```

### Authentication Failed

**Issue**: `gh` command fails with authentication error

**Solution**:
```bash
# Re-authenticate
gh auth login

# Verify
gh auth status
```

### Permission Denied

**Issue**: Cannot set secrets

**Solution**:
- Ensure you have admin access to the repository
- Check token scopes include `repo` and `workflow`
- Re-authenticate with correct scopes

### Secret Not Working in Workflow

**Issue**: Tests fail even with secrets set

**Solution**:
1. Verify secret name matches exactly (case-sensitive)
2. Check workflow syntax for secret reference
3. Ensure secret value is correct (no extra spaces/newlines)
4. Re-run workflow after updating secret

## 📚 Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Anthropic API Documentation](https://docs.anthropic.com/)

## ✅ Checklist

Before running CI/CD workflows:

- [ ] GitHub CLI installed and authenticated
- [ ] `.env` files configured with API keys
- [ ] Secrets set in GitHub repository
- [ ] Secrets verified with `gh secret list`
- [ ] Test workflow runs successfully
- [ ] `.env` files added to `.gitignore`
- [ ] `.env.example` files created (without real values)

---

**Last Updated**: November 13, 2025  
**Repository**: roeiba/autoGrow  
**Status**: ✅ All secrets configured
