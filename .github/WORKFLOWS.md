# GitHub Actions Workflow Documentation

## Workflow Validation Summary

**Last Validated:** 2025-11-15
**Status:** ✅ All workflows have proper permissions configured

## Core Agent Workflows

### QA Agent (`core-qa-agent.yml`)
**Schedule:** Every 4 hours
**Purpose:** Automated code quality and repository health checks

**Permissions:**
- `issues: write` - Create QA report issues
- `contents: read` - Read repository code
- `pull-requests: read` - Review PR status

**Key Features:**
- Validation mode for PR changes (dry run)
- Concurrency control to prevent duplicate runs
- Semantic deduplication to prevent spam
- Reviews last 10 issues, 5 PRs, 10 commits

**Secrets Required:**
- `PAT_TOKEN` - Personal Access Token for issue creation
- `ANTHROPIC_API_KEY` - AI model access

### Issue Generator Agent (`core-issue-generator-agent.yml`)
**Schedule:** Every 10 minutes
**Purpose:** Maintains minimum issue backlog

**Permissions:**
- `issues: write` - Create new issues
- `contents: read` - Read repository state

**Configuration:**
- `MIN_OPEN_ISSUES`: Minimum issue threshold (default: 3)

**Secrets Required:**
- `GITHUB_TOKEN` - Standard GitHub token
- `ANTHROPIC_API_KEY` - AI model access

### Issue Resolver Agent (`core-issue-resolver-agent.yml`)
**Schedule:** Every 30 minutes
**Purpose:** Automatically resolves open issues

**Permissions:**
- `contents: write` - Commit code changes
- `pull-requests: write` - Create PRs
- `issues: write` - Update issue status

**Secrets Required:**
- `PAT_TOKEN` - For PR creation
- `ANTHROPIC_API_KEY` - AI model access

### Marketing Agent (`core-marketing-agent.yml`)
**Schedule:** Daily at 09:00 UTC
**Purpose:** Generate marketing-related issues

**Permissions:**
- `issues: write` - Create marketing issues
- `contents: read` - Read repository

**Note:** Generates strategic issues requiring breakdown per PROCESS.md

### Product Agent (`core-product-agent.yml`)
**Schedule:** Every 2 days at 10:00 UTC
**Purpose:** Generate product feature issues

**Permissions:**
- `issues: write` - Create product issues
- `contents: read` - Read repository

**Note:** Generates strategic issues requiring breakdown per PROCESS.md

### Sales Agent (`core-sales-agent.yml`)
**Schedule:** Weekly on Mondays at 11:00 UTC
**Purpose:** Generate sales and revenue-related issues

**Permissions:**
- `issues: write` - Create sales issues
- `contents: read` - Read repository

**Note:** Generates strategic issues requiring breakdown per PROCESS.md

### Specialized Agents (`core-specialized-agents.yml`)
**Schedule:** Configurable per agent type
**Purpose:** Run specialized task agents

**Permissions:**
- `contents: write` - Make code changes
- `pull-requests: write` - Create PRs
- `issues: write` - Update issues

## Application Workflows

### Seed Planter Frontend (`apps-seed-planter-frontend.yml`)
**Triggers:** Push to main, PR to main, manual dispatch
**Purpose:** Deploy frontend application

**Permissions:**
- `contents: read` - Read code
- `deployments: write` - Deploy to Cloudflare Pages
- `id-token: write` - OIDC authentication

**Secrets Required:**
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

### Seed Planter API (`apps-seed-planter-api.yml`)
**Triggers:** Push to main, PR to main, manual dispatch
**Purpose:** Deploy backend API

**Permissions:**
- `contents: read` - Read code
- `id-token: write` - OIDC authentication

## Testing Workflows

### Validate Agents (`testing-validate-agents.yml`)
**Triggers:** PR to main, push to main
**Purpose:** Dry-run validation of agent code

**Permissions:**
- `contents: read` - Read code only

### Test Agents (`testing-test-agents.yml`)
**Triggers:** PR to main
**Purpose:** Run unit/integration tests

**Permissions:**
- `contents: read` - Read code only

### Sanity Tests (`core-sanity-tests.yml`)
**Triggers:** PR to main, push to main
**Purpose:** Quick smoke tests

**Permissions:**
- `contents: read` - Read code only

## Permission Issues - Resolution History

### Issue: Trial-and-error permission fixes (PR #71, commits f3357a6, 68d23e5)

**Root Cause:** Workflows initially used `GITHUB_TOKEN` which has limited permissions in forked repos and for creating issues in workflows.

**Resolution:**
1. Created `PAT_TOKEN` secret with broader permissions
2. Updated all agent workflows to use `PAT_TOKEN` for issue/PR creation
3. Kept `GITHUB_TOKEN` for read-only operations
4. Added explicit `permissions:` blocks to all workflows

**Validation:** All workflows now functioning correctly with proper permissions.

**Prevention:**
- All new workflows must define explicit permissions
- Use workflow validation job for PR changes
- Document required permissions in workflow comments

## Required Secrets

### Repository Secrets
| Secret | Purpose | Used By |
|--------|---------|---------|
| `GITHUB_TOKEN` | Standard GitHub operations | All workflows (auto-provided) |
| `PAT_TOKEN` | Issue/PR creation | Agent workflows |
| `ANTHROPIC_API_KEY` | AI model access | All agent workflows |
| `CLOUDFLARE_API_TOKEN` | Cloudflare deployments | Deployment workflows |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account | Deployment workflows |
| `GCP_PROJECT_ID` | Google Cloud project | Future deployment workflows |
| `GCP_SERVICE_ACCOUNT` | GCP authentication | Future deployment workflows |

## Adding New Workflows

When adding a new workflow:

1. **Define Permissions Explicitly**
   ```yaml
   permissions:
     contents: read
     issues: write  # if creating issues
     pull-requests: write  # if creating PRs
   ```

2. **Add Validation Job** for PR changes:
   ```yaml
   validate-on-change:
     if: github.event_name == 'pull_request'
     runs-on: ubuntu-latest
     permissions:
       contents: read
     steps:
       - name: Dry run validation
         run: echo "Validation logic here"
   ```

3. **Use Concurrency Groups** for agent workflows:
   ```yaml
   concurrency:
     group: agent-name
     cancel-in-progress: false
   ```

4. **Handle Secrets Properly**
   - Use `PAT_TOKEN` for issue/PR creation
   - Use `GITHUB_TOKEN` for read operations
   - Never commit secrets in code

5. **Add Error Handling**
   ```yaml
   - name: Step that might fail
     run: command
     continue-on-error: true
   ```

6. **Document in This File**
   - Add workflow description
   - List required permissions
   - Document required secrets
   - Explain trigger conditions

## Workflow Best Practices

1. **Concurrency Control:** Use concurrency groups to prevent duplicate agent runs
2. **Rate Limiting:** Space out agent schedules to avoid API rate limits
3. **Semantic Deduplication:** Check for duplicate issues before creating
4. **Quality Gates:** Validate inputs and outputs
5. **Fail Fast:** Return early on validation failures
6. **Logging:** Use descriptive echo statements for debugging
7. **Secrets:** Never log secret values, use masked variables
8. **Idempotency:** Ensure workflows can safely re-run

## Monitoring Workflow Health

Check workflow runs regularly:
```bash
gh run list --limit 20
gh run view <run-id> --log
```

Look for:
- Permission errors (indicates missing permissions)
- Rate limiting (space out schedules)
- Duplicate issue creation (check deduplication logic)
- Failed deployments (check secrets and permissions)

## Common Issues and Solutions

### Issue: "Resource not accessible by integration"
**Solution:** Add required permission to workflow permissions block

### Issue: Duplicate issues created
**Solution:** Implement semantic deduplication in agent code

### Issue: Workflow not triggering
**Solution:** Check cron schedule syntax and branch filters

### Issue: Secrets not found
**Solution:** Verify secret name and check repository settings

### Issue: Workflow runs too frequently
**Solution:** Adjust cron schedule or add concurrency controls
