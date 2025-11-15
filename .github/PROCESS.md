# SeedGPT Development Process

## Issue Types and Handling

### Technical Issues
Technical issues have clear implementation paths with specific code changes, file modifications, or infrastructure updates.

**Characteristics:**
- Clear acceptance criteria
- Specific technical requirements
- Can be implemented by development agents
- Direct impact on codebase

**Labels:** `bug`, `feature`, `enhancement`, `ci/cd`, `infrastructure`

**Workflow:**
1. Issue created with technical specification
2. Assigned to appropriate agent or developer
3. Implementation in PR with tests
4. Review and merge
5. Close issue with reference to PR

### Strategic Issues
Strategic issues involve business decisions, product direction, marketing initiatives, or sales strategies that require planning before technical implementation.

**Characteristics:**
- High-level business/product goals
- Require feasibility analysis
- Need breakdown into technical tasks
- May require stakeholder input

**Labels:** `product`, `marketing`, `sales`, `strategy`, `planning`

**Required Breakdown Process:**
1. **Feasibility Review:** Assess technical feasibility, resource requirements, and dependencies
2. **Break Down:** Create specific sub-tasks with:
   - Clear deliverables
   - Acceptance criteria
   - Technical specifications
   - Estimated effort
3. **Prioritization:** Assign priority based on business value and technical capacity
4. **Assignment:** Assign sub-tasks to appropriate agents/developers
5. **Tracking:** Link sub-tasks to parent strategic issue

## QA Report Response Process

When a QA report is generated:

1. **Review Within 24 Hours:** Designated reviewer checks all findings
2. **Categorize Issues:**
   - Critical (HIGH): Create immediate action items
   - Important (MEDIUM): Schedule for next sprint
   - Minor (LOW): Add to backlog
3. **Create Action Items:** Convert QA findings into trackable issues with owners
4. **Track Resolution:** Link resolution PRs back to QA report issue
5. **Close QA Report:** Only close after all HIGH/MEDIUM items addressed

## Workflow Permissions Standard

All GitHub Actions workflows must include explicit permissions:

```yaml
permissions:
  contents: read        # Read repository contents
  issues: write         # Create/update issues (for agent workflows)
  pull-requests: write  # Create/update PRs (for agent workflows)
  # Add others as needed
```

### Common Permission Sets

**Agent Workflows (Issue/PR creation):**
```yaml
permissions:
  contents: read
  issues: write
  pull-requests: write
```

**Validation Workflows (Read-only):**
```yaml
permissions:
  contents: read
  issues: read
  pull-requests: read
```

**Deployment Workflows:**
```yaml
permissions:
  contents: read
  deployments: write
  id-token: write  # For OIDC auth
```

## PR Review Standards

### Size Guidelines
- **Small (<200 lines):** 1 reviewer, can merge same day
- **Medium (200-500 lines):** 1 reviewer, thorough review required
- **Large (500-1000 lines):** 1-2 reviewers, break into smaller PRs if possible
- **Very Large (>1000 lines):** Must break down unless:
  - Mass refactoring/rename (document thoroughly)
  - Generated code (mark as such)
  - Initial feature scaffold (mark as MVP)

### Review Requirements
1. All PRs require at least one approval
2. PRs changing workflow files require workflow validation
3. PRs from agents should be reviewed for:
   - Code quality
   - Security implications
   - Alignment with project goals
   - No unintended side effects

### Rejection Protocol
When closing a PR without merge:
1. **Comment Required:** Explain specific reasons for rejection
2. **Actionable Feedback:** Provide clear guidance for fixes
3. **Link Alternatives:** If suggesting different approach, explain why
4. **Update Issue:** Update linked issue status and next steps

## Strategic Issue Examples

### Good Strategic Issue (Requires Breakdown)
**Title:** Implement freemium pricing tiers with usage-based metering

**Problem:** Needs technical breakdown into:
- Database schema for usage tracking
- API endpoints for metering
- Frontend UI for tier display
- Payment integration
- Usage limit enforcement
- Upgrade flow implementation

**Action:** Create sub-issues for each component

### Bad Strategic Issue (Too Vague)
**Title:** Make the product better

**Problem:** No clear goal, no measurable outcome, no direction

**Action:** Close and request specific requirements

## Agent-Generated Issues

Issues created by AI agents (Marketing, Sales, Product, QA) should:

1. **Include Context:** Agent type and generation timestamp
2. **Be Reviewed:** Human validates feasibility within 48 hours
3. **Get Labeled:** Apply appropriate type labels
4. **Be Broken Down:** Strategic issues need technical breakdown
5. **Have Priority:** Assign realistic priority based on capacity

## Commit Message Standards

Follow Conventional Commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes
- `ci`: CI/CD changes

**Examples:**
- `feat(api): add usage tracking endpoint`
- `fix(workflow): add missing permissions to QA agent`
- `refactor(core): rename AutoGrow to SeedGPT`

## Workflow Validation Checklist

Before merging workflow changes:

- [ ] Permissions explicitly defined
- [ ] Secrets properly referenced
- [ ] Concurrency groups set (for agents)
- [ ] Error handling included
- [ ] Dry-run/validation job for PR changes
- [ ] Documentation updated if adding new workflow

## Handling Previous QA Concerns

When a new QA report references unresolved items from previous reports:

1. **Acknowledge Pattern:** If same issues recur, it indicates process gap
2. **Root Cause Analysis:** Determine why concerns weren't addressed
3. **Create Meta-Issue:** Track process improvement needed
4. **Implement Prevention:** Update this process document with learnings
5. **Regular Review:** Schedule monthly process review meetings
