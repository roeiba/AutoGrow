# SeedGPT Testing Workflows

These workflows are **for SeedGPT development only** and are **NOT planted** into new projects.

## Included Workflows

- **test-agents.yml** - Tests the agent framework
- **test-agents-with-env.yml.example** - Example configuration for testing with environment
- **validate-agents.yml** - Validates agent configuration and setup

## Purpose

These workflows help develop and test the SeedGPT framework itself:
- Validate agent implementations
- Test CI/CD pipeline changes
- Ensure template quality before planting

## Why Not Planted?

Planted projects don't need to test the SeedGPT framework - they use it. These workflows are only relevant for:
- SeedGPT template development
- Testing changes to the agent system
- Validating the planting process

## Deletion During Planting

The seed planter automatically deletes this folder when creating new projects via:
```python
testing_workflows_path = repo_path / ".github" / "workflows" / "testing"
if testing_workflows_path.exists():
    shutil.rmtree(testing_workflows_path)
```

See: `apps/seed-planter-api/src/seed_planter.py`
