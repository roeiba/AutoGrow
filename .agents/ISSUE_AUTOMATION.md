# Issue Automation System

Complete guide for the automated issue generation and resolution system.

## 🎯 Overview

The project includes two automated workflows that work together:
1. **Issue Generator** - Creates diverse issues when needed
2. **Issue Resolver** - Automatically resolves issues using Claude AI

## 📋 Supported Issue Types

### All Types Supported

The system now handles **all** types of issues:

| Label | Type | Description | Example |
|-------|------|-------------|---------|
| `feature` | New Feature | New functionality or enhancements | "Add dark mode support" |
| `bug` | Bug Fix | Bugs or issues to fix | "Fix login error on mobile" |
| `documentation` | Documentation | Docs improvements | "Update API documentation" |
| `refactor` | Code Quality | Refactoring and cleanup | "Refactor authentication module" |
| `test` | Testing | Test improvements | "Add integration tests for API" |
| `performance` | Performance | Performance optimizations | "Optimize database queries" |
| `security` | Security | Security improvements | "Add rate limiting to API" |
| `ci/cd` | CI/CD | Pipeline improvements | "Add deployment workflow" |
| `enhancement` | Enhancement | General improvements | "Improve error messages" |

## 🤖 Issue Generator

### Configuration

**File**: `.github/workflows/issue-generator.yml`

**Environment Variables**:
```yaml
MIN_OPEN_ISSUES: 3  # Minimum number of open issues to maintain
```

### How It Works

1. **Checks issue count** - Counts open issues (excluding PRs)
2. **Generates if needed** - If below minimum, generates new issues
3. **Uses Claude AI** - Analyzes repo and creates diverse, actionable issues
4. **Creates issues** - Posts to GitHub with appropriate labels

### Issue Generation Strategy

The generator creates **diverse** issues across all categories:

```python
Generate realistic, actionable issues. Include diverse types:
1. feature: New functionality or enhancements
2. bug: Potential bugs or issues to fix
3. documentation: Documentation improvements
4. refactor: Code quality and refactoring
5. test: Testing improvements
6. performance: Performance optimizations
7. security: Security improvements
8. ci/cd: CI/CD pipeline improvements
```

### Example Generated Issues

```json
{
  "issues": [
    {
      "title": "Add logging system for better debugging",
      "body": "Implement centralized logging with multiple levels and file rotation",
      "labels": ["feature"]
    },
    {
      "title": "Fix integration test timeout issue",
      "body": "Integration tests hang indefinitely, need timeout configuration",
      "labels": ["bug", "test"]
    },
    {
      "title": "Document Makefile usage",
      "body": "Add comprehensive guide for using Makefiles in CI/CD",
      "labels": ["documentation"]
    }
  ]
}
```

## 🔧 Issue Resolver

### Configuration

**File**: `.github/workflows/issue-resolver.yml`

**Environment Variables**:
```yaml
ISSUE_LABELS_TO_HANDLE: feature,bug,documentation,refactor,test,performance,security,ci/cd,enhancement
ISSUE_LABELS_TO_SKIP: wontfix,duplicate,invalid,in-progress
MAX_EXECUTION_TIME: 8  # minutes
```

### How It Works

1. **Selects issue** - Finds oldest open issue with handled labels
2. **Claims issue** - Adds comment and "in-progress" label
3. **Analyzes context** - Reads README, issue description, labels
4. **Implements solution** - Uses Claude AI to write code/docs
5. **Creates PR** - Commits changes and creates pull request
6. **Updates issue** - Comments with PR link

### Issue Selection Logic

```python
# Prioritizes:
1. Specific issue (if provided via workflow_dispatch)
2. Oldest open issue with matching labels
3. Not already claimed by agent
4. Not in skip labels (wontfix, duplicate, invalid, in-progress)
```

### Supported Operations

#### Feature Implementation
- Adds new functionality
- Creates new files if needed
- Updates existing code
- Adds tests

#### Bug Fixes
- Identifies root cause
- Implements fix
- Adds regression tests
- Updates documentation

#### Documentation
- Updates README files
- Creates new documentation
- Adds code comments
- Generates API docs

#### Refactoring
- Improves code structure
- Removes duplication
- Applies best practices
- Maintains functionality

#### Testing
- Adds unit tests
- Adds integration tests
- Improves test coverage
- Fixes failing tests

#### Performance
- Optimizes algorithms
- Improves queries
- Reduces memory usage
- Adds benchmarks

#### Security
- Fixes vulnerabilities
- Adds input validation
- Implements rate limiting
- Updates dependencies

#### CI/CD
- Updates workflows
- Adds automation
- Improves pipelines
- Fixes CI issues

## 🚀 Usage

### Trigger Issue Generator

**Manually**:
```bash
# Via GitHub UI
Actions → Issue Generator Agent → Run workflow

# Via gh CLI
gh workflow run issue-generator.yml
```

**Automatically**:
- Runs when issue count drops below minimum

### Trigger Issue Resolver

**Manually**:
```bash
# Resolve any issue
gh workflow run issue-resolver.yml

# Resolve specific issue
gh workflow run issue-resolver.yml -f issue_number=42
```

**Automatically**:
- Runs every 10 minutes (cron: '*/10 * * * *')

### Disable Automation

**Temporarily**:
```bash
# Disable workflow
gh workflow disable issue-resolver.yml
gh workflow disable issue-generator.yml
```

**Permanently**:
- Delete or rename workflow files
- Or add condition: `if: false`

## 📊 Workflow Status

### Check Status

```bash
# List workflow runs
gh run list --workflow=issue-resolver.yml
gh run list --workflow=issue-generator.yml

# View specific run
gh run view <run-id>

# Watch live
gh run watch
```

### View Logs

```bash
# View logs for latest run
gh run view --log

# View logs for specific run
gh run view <run-id> --log
```

## 🎯 Configuration Examples

### Handle Only Bugs and Features

```yaml
env:
  ISSUE_LABELS_TO_HANDLE: bug,feature
  ISSUE_LABELS_TO_SKIP: wontfix,duplicate,invalid,in-progress
```

### Handle Everything Except Documentation

```yaml
env:
  ISSUE_LABELS_TO_HANDLE: feature,bug,refactor,test,performance,security,ci/cd
  ISSUE_LABELS_TO_SKIP: wontfix,duplicate,invalid,in-progress,documentation
```

### Aggressive Resolution (Handle All)

```yaml
env:
  ISSUE_LABELS_TO_HANDLE: feature,bug,documentation,refactor,test,performance,security,ci/cd,enhancement
  ISSUE_LABELS_TO_SKIP: wontfix,duplicate,invalid,in-progress
  MAX_EXECUTION_TIME: 15  # Allow more time
```

## 🔍 Monitoring

### Issue Metrics

```bash
# Count open issues by label
gh issue list --label feature --state open | wc -l
gh issue list --label bug --state open | wc -l

# List in-progress issues
gh issue list --label in-progress --state open

# List recently resolved
gh issue list --state closed --limit 10
```

### PR Metrics

```bash
# List PRs created by agent
gh pr list --author "github-actions[bot]"

# List open PRs from agent
gh pr list --author "github-actions[bot]" --state open
```

## 🛡️ Safety Features

### Prevents Issues

1. **Concurrency control** - Only one resolver runs at a time
2. **Time limits** - Max execution time prevents infinite loops
3. **Label checking** - Won't touch wontfix/duplicate issues
4. **Claim system** - Won't work on already-claimed issues
5. **PR review** - All changes go through PR review

### Manual Override

```yaml
# Add label to prevent automation
gh issue edit <number> --add-label "wontfix"

# Remove in-progress to allow retry
gh issue edit <number> --remove-label "in-progress"
```

## 📝 Best Practices

### For Issue Generator

1. **Keep minimum low** - 3-5 issues is reasonable
2. **Review generated issues** - Close irrelevant ones
3. **Add context** - Comment on issues with more details
4. **Use labels** - Properly label issues for resolver

### For Issue Resolver

1. **Review PRs** - Always review agent-created PRs
2. **Test changes** - Run tests before merging
3. **Monitor failures** - Check logs if resolution fails
4. **Adjust labels** - Use skip labels for complex issues

### General

1. **Start conservative** - Begin with fewer issue types
2. **Monitor closely** - Watch first few runs
3. **Iterate** - Adjust configuration based on results
4. **Document** - Add context to issues for better resolution

## 🐛 Troubleshooting

### Generator Not Creating Issues

**Check**:
1. Issue count is below minimum
2. ANTHROPIC_API_KEY is set
3. Workflow has permissions
4. Check workflow logs

### Resolver Not Working

**Check**:
1. Issues have correct labels
2. Issues not in skip labels
3. ANTHROPIC_API_KEY is set
4. Check for "in-progress" label conflicts

### Poor Quality Issues/Solutions

**Fix**:
1. Add more context to issues
2. Improve README documentation
3. Add examples in issues
4. Adjust prompts in scripts

## 📚 Files Reference

### Workflows
- `.github/workflows/issue-generator.yml` - Generator workflow
- `.github/workflows/issue-resolver.yml` - Resolver workflow

### Scripts
- `.github/scripts/issue_generator.py` - Generator logic
- `.github/scripts/issue_resolver.py` - Resolver logic

### Documentation
- `.agents/ISSUE_AUTOMATION.md` - This file
- `.agents/ISSUE_RESOLVER_FIX.md` - Resolver fixes
- `.github/workflows/README.md` - Workflow overview

## 🎉 Summary

**The system now supports ALL issue types**:
- ✅ Features
- ✅ Bugs
- ✅ Documentation
- ✅ Refactoring
- ✅ Testing
- ✅ Performance
- ✅ Security
- ✅ CI/CD
- ✅ Enhancements

**Configuration updated**:
- ✅ Issue generator creates diverse issues
- ✅ Issue resolver handles all types
- ✅ Labels expanded to cover all categories
- ✅ Documentation complete

---

**Status**: ✅ **Full automation for all issue types enabled!**
