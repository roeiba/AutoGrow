# PR Failure Resolver Agent

## Overview

The PR Failure Resolver Agent automatically detects and fixes failing CI/CD checks in open pull requests. It analyzes test failures, build errors, linting issues, and other CI/CD failures, then implements fixes and pushes them to the PR branch.

## How It Works

### Workflow

1. **PR Selection**
   - Scans all open PRs for failing checks
   - Skips draft PRs
   - Skips PRs already claimed by the agent
   - Selects the oldest failing PR

2. **Claiming**
   - Posts a comment on the PR indicating work has started
   - Marks the PR as being worked on by the agent

3. **Failure Analysis**
   - Retrieves check run details from GitHub
   - Extracts failure messages, logs, and context
   - Analyzes test output, build logs, and error messages

4. **Branch Checkout**
   - Fetches the PR branch from remote
   - Checks out the branch locally

5. **Fix Generation**
   - Uses Claude AI (CLI or SDK) to analyze failures
   - Provides context from README, PROJECT_BRIEF.md, and PR files
   - Generates fixes for the identified issues

6. **Commit & Push**
   - Commits the fixes with descriptive message
   - Pushes changes to the PR branch
   - CI/CD checks re-run automatically

7. **PR Update**
   - Posts a comment with fix details
   - Lists files changed
   - Outcome tracking for feedback loop

## Features

### Supported Failure Types

- **Test Failures**: Unit tests, integration tests, E2E tests
- **Build Errors**: Compilation errors, dependency issues
- **Linting Issues**: Code style, formatting, static analysis
- **Type Errors**: TypeScript, Python type checking
- **CI/CD Failures**: Workflow errors, deployment issues
- **Security Scans**: Vulnerability detection failures

### Intelligence

- **Context-Aware**: Uses README and PROJECT_BRIEF.md for project understanding
- **PR-Specific**: Analyzes only files changed in the PR
- **Root Cause Analysis**: Identifies underlying issues, not just symptoms
- **Minimal Changes**: Makes focused fixes without over-engineering

### Safety

- **No Draft PRs**: Skips draft PRs to avoid interfering with WIP
- **Claim System**: Prevents multiple agents from working on same PR
- **Dry Mode**: Validation mode for testing without making changes
- **Outcome Tracking**: Records success/failure for continuous improvement

## Configuration

### Environment Variables

```bash
# Required
GITHUB_TOKEN=<your-github-token>
ANTHROPIC_API_KEY=<your-anthropic-api-key>
REPO_NAME=owner/repo

# Optional
SPECIFIC_PR=42                    # Fix specific PR number
MAX_EXECUTION_TIME=8              # Max minutes per run (default: 8)
DRY_MODE=false                    # Validation mode (default: false)
```

### GitHub Actions

The agent runs automatically via GitHub Actions workflow:

```yaml
# .github/workflows/core-pr-failure-resolver-agent.yml
schedule:
  - cron: '*/15 * * * *'  # Every 15 minutes
```

### Permissions Required

```yaml
permissions:
  issues: write          # Post comments
  contents: write        # Push fixes
  pull-requests: write   # Update PRs
  checks: read          # Read check runs
```

## Usage

### Automatic Mode

The agent runs automatically every 15 minutes via GitHub Actions:

1. Scans for failing PRs
2. Selects one to fix
3. Analyzes failures
4. Implements fixes
5. Pushes changes

### Manual Trigger

Fix a specific PR:

```bash
gh workflow run core-pr-failure-resolver-agent.yml -f pr_number=42
```

Auto-select a failing PR:

```bash
gh workflow run core-pr-failure-resolver-agent.yml
```

### Local Testing

```bash
cd seedgpt-core/src

# Set environment variables
export GITHUB_TOKEN=<token>
export ANTHROPIC_API_KEY=<key>
export REPO_NAME=owner/repo
export SPECIFIC_PR=42

# Run the agent
python cli/pr_failure_resolver_cli.py
```

### Dry Mode (Validation)

Test without making changes:

```bash
export DRY_MODE=true
python cli/pr_failure_resolver_cli.py
```

## Architecture

### Components

```
pr_failure_resolver.py          # Core agent logic
├── _select_failing_pr()        # Find PR with failures
├── _claim_pr()                 # Mark PR as being worked on
├── _get_failure_details()      # Extract failure information
├── _checkout_pr_branch()       # Checkout PR branch
├── _generate_fix()             # Use Claude AI to fix
└── _push_changes_if_modified() # Commit and push fixes

pr_failure_resolver_cli.py      # CLI entry point
├── Environment configuration
├── GitHub client setup
├── Error handling
└── Agent execution

github_helpers.py               # PR helper functions
├── get_pull_request()          # Get PR by number
├── get_open_pull_requests()    # List open PRs
├── get_pr_checks()             # Get check runs
├── get_pr_files()              # Get changed files
└── get_pr_comments()           # Get PR comments

git_helpers.py                  # Git operations
├── checkout_branch()           # Checkout existing branch
├── commit_changes()            # Stage and commit
└── push_branch()               # Push to remote
```

### Integration Points

1. **GitHub API**: PR data, check runs, comments
2. **Claude AI**: Failure analysis and fix generation
3. **Git**: Branch operations, commits, pushes
4. **Outcome Tracker**: Success/failure metrics
5. **GitHub Actions**: Automated scheduling

## Examples

### Example 1: Test Failure

**PR**: #42 - "Add user authentication"

**Failure**:
```
FAILED tests/test_auth.py::test_login - AssertionError: Expected 200, got 401
```

**Agent Action**:
1. Analyzes test failure
2. Identifies missing authentication header
3. Fixes the test to include proper auth
4. Pushes fix
5. Tests pass ✅

### Example 2: Linting Error

**PR**: #43 - "Refactor database queries"

**Failure**:
```
src/db.py:42:1: E501 line too long (120 > 88 characters)
```

**Agent Action**:
1. Identifies linting rule violation
2. Reformats the line
3. Pushes fix
4. Linting passes ✅

### Example 3: Build Error

**PR**: #44 - "Update dependencies"

**Failure**:
```
ERROR: Cannot install package-a and package-b because these package versions have conflicting dependencies.
```

**Agent Action**:
1. Analyzes dependency conflict
2. Identifies compatible versions
3. Updates requirements.txt
4. Pushes fix
5. Build succeeds ✅

## Best Practices

### For Repository Owners

1. **Review Agent Fixes**: Always review commits made by the agent
2. **Monitor Patterns**: Check if same failures repeat
3. **Adjust Frequency**: Tune schedule based on PR volume
4. **Set Up Alerts**: Get notified when agent fails

### For Contributors

1. **Check PR Comments**: Agent will comment when working on your PR
2. **Don't Force Push**: Avoid force pushing while agent is working
3. **Review Fixes**: Verify agent's fixes are correct
4. **Provide Context**: Good PR descriptions help the agent

### For Maintainers

1. **Keep Tests Clear**: Clear test names and error messages help
2. **Document Standards**: PROJECT_BRIEF.md guides the agent
3. **Use Labels**: Consider adding labels for PR status
4. **Monitor Costs**: Track Claude API usage

## Troubleshooting

### Agent Not Finding Failures

**Symptoms**: Agent says "No failing PRs found"

**Solutions**:
- Verify PRs actually have failing checks
- Check if checks are still running (not completed)
- Ensure agent has `checks: read` permission

### Agent Can't Checkout Branch

**Symptoms**: "Failed to checkout branch" error

**Solutions**:
- Verify branch exists on remote
- Check git credentials are configured
- Ensure no local conflicts

### No Changes Made

**Symptoms**: Agent says "No files were modified"

**Solutions**:
- Check Claude API key is valid
- Review failure details for clarity
- May need manual intervention for complex issues

### Fixes Don't Work

**Symptoms**: Agent pushes fixes but checks still fail

**Solutions**:
- Review agent's fix for correctness
- Check if failure requires different approach
- May need to disable agent for this PR and fix manually

## Metrics & Monitoring

### Outcome Tracking

The agent tracks:
- PR numbers worked on
- Success/failure rates
- Time to fix
- Types of failures resolved

### View Metrics

```python
from utils.outcome_tracker import OutcomeTracker

tracker = OutcomeTracker()
stats = tracker.get_overall_stats()
print(f"Success rate: {stats['success_rate']:.1%}")
```

### Logs

All actions are logged:
- PR selection decisions
- Failure analysis
- Fix generation
- Commit and push operations

Check GitHub Actions logs for details.

## Security

### Secrets Management

- `ANTHROPIC_API_KEY`: Stored as GitHub secret
- `GITHUB_TOKEN`: Auto-provided by GitHub Actions
- Never logged or exposed in output

### Code Review

- All agent commits are clearly marked
- PRs require review before merging
- Agent actions are auditable

### Permissions

- Minimal required permissions
- No access to secrets or sensitive data
- Isolated execution environment

## Future Enhancements

### Planned Features

- [ ] Multi-PR support (fix multiple PRs in one run)
- [ ] Priority system (critical failures first)
- [ ] Learning from successful fixes
- [ ] Integration with issue tracker
- [ ] Slack/Discord notifications

### Experimental

- [ ] Rollback on repeated failures
- [ ] Suggest PR improvements
- [ ] Auto-merge on success (with approval)

## Contributing

To improve the PR Failure Resolver:

1. Edit `pr_failure_resolver.py` for core logic
2. Update `pr_failure_resolver_cli.py` for CLI changes
3. Add tests in `tests/` directory
4. Update this documentation
5. Submit PR with changes

## Related Agents

- **Issue Resolver**: Resolves issues and creates PRs
- **QA Agent**: Monitors repository health
- **Issue Generator**: Creates new issues

## License

Part of the SeedGPT framework.
