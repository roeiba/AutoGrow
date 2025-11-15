# GitHub Workflow Agents

Automated agents that maintain and resolve issues using Claude AI.

## Workflow Organization

The workflows are organized into three categories:

### 📁 `core/` - Core SeedGPT Workflows
**✅ Planted into every new project**

These workflows provide the core SeedGPT functionality:
- AI-powered issue management
- Automated development assistance
- Quality assurance automation
- Business process automation

See [`core/README.md`](core/README.md) for details.

### 📁 `apps/` - Template Apps Workflows
**❌ NOT planted (deleted during planting)**

CI/CD workflows for the SeedGPT template applications:
- Seed Planter API backend
- Seed Planter Frontend

These are specific to the SeedGPT template and reference the `apps/` folder which is removed when planting new projects.

See [`apps/README.md`](apps/README.md) for details.

### 📁 `testing/` - Development & Testing Workflows
**❌ NOT planted (deleted during planting)**

Workflows for SeedGPT framework development:
- Agent framework testing
- Configuration validation
- Template quality checks

These are only needed for developing the SeedGPT template itself.

See [`testing/README.md`](testing/README.md) for details.

## Core Workflows

### 1. Issue Generator Agent (`issue-generator-agent.yml`)

**Purpose**: Ensures the repository always has at least a minimum number of open issues.

**Schedule**: Every 10 minutes

**What it does**:
1. Counts current open issues
2. If below minimum (default: 3), generates new issues using Claude AI
3. Creates realistic, actionable issues based on repository analysis

**Configuration**:
```yaml
# Repository variables (Settings → Secrets and variables → Actions → Variables)
MIN_OPEN_ISSUES: 3  # Minimum issues to maintain
```

**Manual trigger**:
```bash
# Via GitHub UI: Actions → Issue Generator Agent → Run workflow
# Or via gh CLI:
gh workflow run issue-generator-agent.yml -f min_issues=5
```

### 2. Issue Resolver Agent (`issue-resolver-agent.yml`)

**Purpose**: Automatically resolves open issues by analyzing them with Claude AI and creating PRs.

**Schedule**: Every 10 minutes (singleton - no overlapping executions)

**What it does**:
1. Finds an open issue to work on
2. Claims the issue (adds comment + `in-progress` label)
3. Analyzes the issue with Claude AI
4. Implements the fix
5. Creates a branch and commits changes
6. Pushes and creates a pull request
7. Updates the issue with PR link

**Configuration**:
```yaml
# Repository variables
ISSUE_LABELS_TO_HANDLE: bug,enhancement  # Only handle these labels
ISSUE_LABELS_TO_SKIP: wontfix,duplicate,in-progress  # Skip these labels
MAX_EXECUTION_TIME: 8  # Max minutes per run
```

**Manual trigger**:
```bash
# Resolve specific issue:
gh workflow run issue-resolver.yml -f issue_number=42

# Auto-select issue:
gh workflow run issue-resolver.yml
```

## Setup

### 1. Add Secrets

Go to **Settings → Secrets and variables → Actions → Secrets**:

```
ANTHROPIC_API_KEY: Your Claude API key from console.anthropic.com
```

Note: `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### 2. Configure Variables (Optional)

Go to **Settings → Secrets and variables → Actions → Variables**:

```
MIN_OPEN_ISSUES: 3
ISSUE_LABELS_TO_HANDLE: bug,enhancement
ISSUE_LABELS_TO_SKIP: wontfix,duplicate,in-progress
MAX_EXECUTION_TIME: 8
```

### 3. Enable Workflows

The workflows will run automatically every 10 minutes once enabled.

## How They Work Together

```
┌─────────────────────────┐
│  Issue Generator Agent  │
│  (Every 10 min)         │
└───────────┬─────────────┘
            │
            ▼
    ┌───────────────┐
    │ Check count   │
    │ < 3 issues?   │
    └───────┬───────┘
            │ Yes
            ▼
    ┌───────────────┐
    │ Generate new  │
    │ issues with   │
    │ Claude AI     │
    └───────────────┘

┌─────────────────────────┐
│  Issue Resolver Agent   │
│  (Every 10 min)         │
└───────────┬─────────────┘
            │
            ▼
    ┌───────────────┐
    │ Find open     │
    │ issue         │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ Claim issue   │
    │ (comment +    │
    │  label)       │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ Analyze with  │
    │ Claude AI     │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ Implement fix │
    │ Create PR     │
    └───────────────┘
```

## Customization

### Change Schedule

Edit the cron expression in the workflow files:

```yaml
on:
  schedule:
    - cron: '*/10 * * * *'  # Every 10 minutes
    # - cron: '0 * * * *'   # Every hour
    # - cron: '0 0 * * *'   # Daily at midnight
```

### Customize Issue Selection

Edit `.github/scripts/issue_resolver.py`:

```python
# Add custom logic for issue selection
# Example: Prioritize by label
if 'critical' in issue_labels:
    selected_issue = issue
    break
```

### Customize Prompts

Edit the prompt in `.github/scripts/issue_generator.py` or `issue_resolver.py`:

```python
prompt = f"""Your custom prompt here...

Repository: {REPO_NAME}
...
"""
```

## Monitoring

### View Workflow Runs

Go to **Actions** tab to see all workflow runs.

### Check Logs

Click on any workflow run to see detailed logs.

### Workflow Status Badge

Add to your README:

```markdown
![Issue Generator](https://github.com/{owner}/{repo}/actions/workflows/issue-generator-agent.yml/badge.svg)
![Issue Resolver](https://github.com/{owner}/{repo}/actions/workflows/issue-resolver-agent.yml/badge.svg)
```

## Troubleshooting

### Workflow not running

- Check if workflows are enabled: **Actions → Enable workflows**
- Verify cron schedule is correct
- Check repository permissions

### Authentication errors

- Verify `ANTHROPIC_API_KEY` secret is set correctly
- Check `GITHUB_TOKEN` has required permissions

### No issues being generated

- Check Claude API quota/limits
- Review workflow logs for errors
- Verify repository has README and content

### No issues being resolved

- Check if issues have required labels
- Verify issues aren't already claimed (`in-progress` label)
- Review workflow logs for errors

## Best Practices

1. **Monitor the agents**: Check workflow runs regularly
2. **Review PRs**: Always review agent-generated PRs before merging
3. **Adjust configuration**: Tune variables based on your needs
4. **Set rate limits**: Don't run too frequently to avoid API limits
5. **Use labels**: Properly label issues for better agent selection

## Security

- Secrets are encrypted and not exposed in logs
- Workflows run in isolated environments
- PRs require review before merging
- Agent actions are clearly marked and traceable

## Cost Considerations

- **GitHub Actions**: Free for public repos, limited minutes for private
- **Claude API**: Charged per token usage
- **Recommendation**: Monitor usage and adjust frequency as needed

## Examples

### Generate 5 issues manually

```bash
gh workflow run issue-generator-agent.yml -f min_issues=5
```

### Resolve specific issue

```bash
gh workflow run issue-resolver-agent.yml -f issue_number=123
```

### Disable temporarily

Comment out the schedule in the workflow file:

```yaml
on:
  # schedule:
  #   - cron: '*/10 * * * *'
  workflow_dispatch:  # Keep manual trigger
```

## Contributing

To improve the agents:

1. Edit Python scripts in `.github/scripts/`
2. Test locally before committing
3. Update documentation
4. Submit PR with changes

## License

Part of the AI Project Template.
