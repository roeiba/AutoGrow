# Core SeedGPT Workflows

These workflows are **planted into every new project** created by SeedGPT.

## Included Workflows

### AI Agents
- **issue-generator-agent.yml** - Ensures minimum number of open issues
- **issue-resolver-agent.yml** - Automatically resolves issues with AI
- **marketing-agent.yml** - Marketing automation agent
- **product-agent.yml** - Product management agent
- **qa-agent.yml** - Quality assurance agent
- **sales-agent.yml** - Sales automation agent
- **specialized-agents.yml** - Domain-specific specialized agents

### Testing
- **sanity-tests.yml** - Core sanity checks for the project

## Purpose

These workflows provide the core SeedGPT functionality that every planted project needs:
- Automated issue management
- AI-powered development assistance
- Quality assurance automation
- Business process automation

## Setup Required

After planting, each project needs to configure:
1. **GitHub Secrets**: `ANTHROPIC_API_KEY`, `PAT_TOKEN`
2. **Repository Variables**: Optional configuration for agents

See the main `.github/workflows/README.md` for detailed setup instructions.
