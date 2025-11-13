# PROJECT_BRIEF.md Validation

## Overview

AutoGrow includes automated validation for `PROJECT_BRIEF.md` to ensure all required sections are present and properly formatted before AI agents start generating code. This prevents wasted API calls and improves generation quality by catching issues early.

## Required Sections

The validator checks for the following **required sections** in PROJECT_BRIEF.md:

1. **Project Overview** (or "Overview")
   - Must include: Project Name, Brief Description, Problem Statement, Target Users
   - Minimum description length: 50 characters
   - Minimum problem statement length: 100 characters

2. **Core Requirements** (or "Core Features", "Features", "Requirements")
   - Must include functional requirements
   - Minimum section length: 100 characters
   - Should include at least 3 requirements

3. **Technical Preferences** (or "Technical Requirements", "Tech Stack", "Technology Stack")
   - Specifies the technology choices for the project

4. **Success Criteria** (or "Acceptance Criteria", "Definition of Done") ⭐ **NEW**
   - Defines measurable outcomes for project success
   - Minimum section length: 50 characters
   - Should include at least 3 specific, measurable criteria

## Recommended Sections

The following sections are optional but recommended:

- Data Model
- External Integrations
- Timeline & Priorities
- Budget & Resources
- User Roles & Permissions
- Key User Flows

## When Validation Runs

Validation runs automatically:

1. **Issue Resolver Agent** - Before attempting to fix any issue
2. **Agentic Workflow** - Before cloning repository and starting AI generation
3. **Manual Validation** - Can be run standalone using the validator module

## Validation Skip Logic

Validation is automatically skipped for issues related to:
- Documentation setup
- Template creation
- PROJECT_BRIEF.md itself
- Initial bootstrap/setup tasks

This prevents circular validation errors when working on the brief itself.

## Example: Valid PROJECT_BRIEF.md Structure

```markdown
# Project Brief

## Project Overview

**Project Name**: MyApp

**Brief Description**: A comprehensive description of at least 50 characters...

**Problem Statement**: A detailed problem statement of at least 100 characters explaining what problem this project solves...

**Target Users**: Developers, end users, administrators

---

## Core Requirements

### Functional Requirements
1. User authentication with OAuth2
2. RESTful API for data management
3. Real-time notifications

### Non-Functional Requirements
- Performance: <200ms response time
- Security: End-to-end encryption
- Scalability: Support 10k+ users

---

## Technical Preferences

### Backend
- Python 3.11+
- FastAPI
- PostgreSQL

### Frontend
- React 18+
- TypeScript

---

## Success Criteria

1. 90% code coverage with automated tests
2. Deploy to production in under 1 hour
3. Zero critical security vulnerabilities
4. API response time <200ms for 95% of requests
5. Handle 10,000 concurrent users successfully

---
```

## Using the Validator

### Standalone Usage

```python
from pathlib import Path
from utils.project_brief_validator import validate_project_brief

# Validate PROJECT_BRIEF.md
result = validate_project_brief(Path('PROJECT_BRIEF.md'))

# Print summary
print(result.get_summary())

# Check if valid
if result.is_valid:
    print("✅ Validation passed!")
else:
    print("❌ Validation failed")
    for error in result.errors:
        print(f"  - {error}")
```

### Exit on Failure

```python
from utils.project_brief_validator import validate_or_exit

# Validate and exit if invalid
validate_or_exit(Path('PROJECT_BRIEF.md'))
```

### Command Line

```bash
# Run tests
python test_validator.py

# Validate manually in Python
python -c "
import sys
sys.path.insert(0, 'src')
from utils.project_brief_validator import validate_or_exit
validate_or_exit()
"
```

## Validation Output

### Success Example

```
✅ PROJECT_BRIEF.md validation passed (2 warning(s))

Warnings:
  - Missing recommended section: 'Data Model'
  - Found 5 potential placeholders that may need completion: TODO, TBD
```

### Failure Example

```
❌ PROJECT_BRIEF.md validation failed with 2 error(s)

Errors:
  - Missing required section: 'Success Criteria' (also accepts: 'Acceptance Criteria', 'Definition of Done')
  - Core Requirements section is too short (45 chars). Minimum recommended: 100 characters

Warnings:
  - Missing recommended section: 'External Integrations'
```

## Benefits

1. **Prevents Wasted API Calls** - Catches issues before expensive AI generation starts
2. **Better Generation Quality** - Ensures AI has complete context and requirements
3. **Clear Error Messages** - Tells users exactly what's missing or needs improvement
4. **Flexible Section Names** - Accepts common variations (e.g., "Core Features" vs "Core Requirements")
5. **Quality Metrics** - Enforces minimum content length to ensure sufficient detail

## Troubleshooting

### "Missing required section" Error

Make sure your section headers match one of the accepted variations:
- Use `##` for section headers (not `#` or `###`)
- Check spelling and capitalization (validation is case-insensitive)
- Include any optional emoji prefix if your template uses them

### "Section too short" Error

Add more detail to the section:
- PROJECT_BRIEF.md: minimum 1000 characters total
- Description: minimum 50 characters
- Problem Statement: minimum 100 characters
- Core Requirements: minimum 100 characters
- Success Criteria: minimum 50 characters

### "Empty sections" Error

Ensure each section has content between the header and the next section. Sections with only whitespace are flagged as empty.

### Validation Skipped

If you see "Skipping PROJECT_BRIEF.md validation", it means:
- The issue is about documentation/templates (intentional skip)
- Or PROJECT_BRIEF.md doesn't exist (optional file)

## Implementation Details

**Location**: `src/utils/project_brief_validator.py`

**Integration Points**:
- `src/agentic_workflow.py:369` - Main workflow validation
- `.github/scripts/issue_resolver.py:212` - Issue resolver validation

**Test Suite**: `test_validator.py`

## Future Enhancements

Potential improvements for the validator:

- [ ] Validate YAML frontmatter if present
- [ ] Check for broken internal links
- [ ] Validate code blocks for syntax
- [ ] Suggest improvements based on AI analysis
- [ ] Export validation results to JSON/HTML
- [ ] Pre-commit hook integration
