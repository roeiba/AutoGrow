# SeedGPT Template Apps Workflows

These workflows are **specific to the SeedGPT template** and are **NOT planted** into new projects.

## Included Workflows

- **seed-planter-api.yml** - CI/CD for the Seed Planter API backend
- **seed-planter-frontend.yml** - CI/CD for the Seed Planter Frontend

## Purpose

These workflows build, test, and deploy the SeedGPT template applications:
- **Seed Planter API**: The backend service that plants new projects
- **Seed Planter Frontend**: The web UI for creating projects

## Why Not Planted?

When a new project is planted:
1. The `apps/` folder is deleted (contains seed-planter apps)
2. These workflows reference files in `apps/` that no longer exist
3. Planted projects don't need to deploy the seed-planter infrastructure

## Deletion During Planting

The seed planter automatically deletes this folder when creating new projects via:
```python
apps_workflows_path = repo_path / ".github" / "workflows" / "apps"
if apps_workflows_path.exists():
    shutil.rmtree(apps_workflows_path)
```

See: `apps/seed-planter-api/src/seed_planter.py`
