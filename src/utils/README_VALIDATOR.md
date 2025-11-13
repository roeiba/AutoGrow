# PROJECT_BRIEF.md Validator

Validates PROJECT_BRIEF.md structure and required fields before AI generation to prevent wasted API calls and provide better error messages.

## Overview

The PROJECT_BRIEF.md validator performs comprehensive pre-flight checks on your project brief to ensure it has the necessary structure and content for AI agents to generate quality code. This validation prevents wasted API calls by catching issues early.

## Features

- **Required Section Validation**: Ensures all mandatory sections are present
- **Content Quality Checks**: Validates that descriptions and requirements meet minimum length thresholds
- **Structure Analysis**: Checks for proper formatting and organization
- **Placeholder Detection**: Identifies incomplete placeholder text
- **Detailed Error Messages**: Provides clear, actionable error messages
- **Warning System**: Highlights potential issues without blocking generation

## Usage

### As a Library

```python
from utils.project_brief_validator import validate_project_brief

# Validate a PROJECT_BRIEF.md file
result = validate_project_brief('PROJECT_BRIEF.md')

if result.is_valid:
    print("✅ Validation passed!")
    print(f"Sections found: {result.metadata['sections_found']}")
else:
    print("❌ Validation failed!")
    for error in result.errors:
        print(f"  - {error}")
```

### Command Line

```python
from utils.project_brief_validator import validate_or_exit

# Validate and exit if invalid (useful in scripts)
validate_or_exit('PROJECT_BRIEF.md')
```

### Integrated Usage

The validator is automatically integrated into:

1. **AgenticWorkflow**: Validates PROJECT_BRIEF.md after cloning repository
2. **Issue Resolver Agent**: Validates before processing GitHub issues

## Validation Rules

### Required Sections

The following sections must be present:

- ✅ **Project Overview** - High-level project information
- ✅ **Core Requirements** - Functional and non-functional requirements
- ✅ **Technical Preferences** - Technology stack choices
- ✅ **User Roles & Permissions** - Who uses the system
- ✅ **Key User Flows** - How users interact with the system

### Recommended Sections

These sections are optional but recommended:

- ⚠️ Data Model - Data structures and relationships
- ⚠️ External Integrations - Third-party services
- ⚠️ Timeline & Priorities - Project schedule
- ⚠️ Budget & Resources - Resource constraints

### Required Fields in Project Overview

- **Project Name**: Unique identifier
- **Brief Description**: Minimum 50 characters
- **Problem Statement**: Minimum 100 characters
- **Target Users**: Who will use this

### Content Quality Rules

- **Minimum file length**: 1000 characters
- **Minimum requirements section**: 100 characters
- **At least 3 requirements** in functional requirements
- **No empty sections**
- **Completion checklist** should be checked

### Common Issues Detected

- 🔍 Placeholder text like `[Your text here]`, `TODO`, `TBD`
- 🔍 Lines longer than 200 characters
- 🔍 Empty sections
- 🔍 Missing functional/non-functional requirements subsections
- 🔍 Unchecked completion checklist items

## Validation Result

The `ValidationResult` object contains:

```python
@dataclass
class ValidationResult:
    is_valid: bool              # Overall validation status
    errors: List[str]           # Blocking errors
    warnings: List[str]         # Non-blocking warnings
    metadata: Dict[str, any]    # Additional information
```

### Metadata Fields

- `file_size`: Size of the file in characters
- `line_count`: Number of lines in the file
- `sections_found`: List of section headers found
- `checklist_progress`: Checklist completion status (if present)
  - `checked`: Number of checked items
  - `unchecked`: Number of unchecked items
  - `total`: Total checklist items

## Examples

### Valid PROJECT_BRIEF.md

```markdown
# Project Brief

## 🎯 Project Overview

**Project Name**: My Awesome Project

**Brief Description**:
A comprehensive web application that solves real-world problems.

**Problem Statement**:
Users currently struggle with X, Y, and Z. This project aims to provide
a solution that addresses these pain points effectively.

**Target Users**:
Software developers, project managers, and business analysts.

## 📋 Core Requirements

### Functional Requirements
1. Feature A - Description
2. Feature B - Description
3. Feature C - Description

### Non-Functional Requirements
- Performance: Fast response times
- Usability: Intuitive interface

## 🏗️ Technical Preferences
- Backend: Python/FastAPI
- Frontend: React

## 👥 User Roles & Permissions
- Admin: Full access
- User: Limited access

## 🔄 Key User Flows
1. User logs in
2. User performs action
3. System responds
```

### Invalid PROJECT_BRIEF.md

```markdown
# Project Brief

## Project Overview

**Project Name**: [Your Project]

**Brief Description**: Short

## Requirements

Some requirements
```

**Validation errors:**
- Missing required section: 'Core Requirements'
- Missing required section: 'Technical Preferences'
- Missing required section: 'User Roles & Permissions'
- Missing required section: 'Key User Flows'
- Missing required field: 'Problem Statement'
- Missing required field: 'Target Users'
- Brief Description is too short (5 chars). Recommended minimum: 50 characters
- Found placeholder text: [Your Project]

## Testing

Run the unit tests:

```bash
pytest tests/unit/test_project_brief_validator.py -v
```

Test coverage:
- ✅ File existence validation
- ✅ Empty file detection
- ✅ Required sections validation
- ✅ Content length validation
- ✅ Placeholder detection
- ✅ Overview fields validation
- ✅ Requirements section validation
- ✅ Empty section detection
- ✅ Checklist analysis
- ✅ Metadata collection

## Integration

### In AgenticWorkflow

```python
def _validate_project_brief(self) -> bool:
    """Validate PROJECT_BRIEF.md before AI generation"""
    project_brief_path = self.repo_path / "PROJECT_BRIEF.md"

    if not project_brief_path.exists():
        return True  # Optional

    result = validate_project_brief(project_brief_path)

    if not result.is_valid:
        self.logger.error("Validation failed")
        for error in result.errors:
            self.logger.error(f"  - {error}")
        return False

    return True
```

### In Issue Resolver

The validator is called before processing any issue to ensure the PROJECT_BRIEF.md is valid. This prevents wasted API calls when the brief is incomplete or malformed.

## Benefits

1. **Saves API Costs**: Catches errors before making expensive AI API calls
2. **Better Error Messages**: Clear, actionable feedback on what's wrong
3. **Consistent Quality**: Ensures all project briefs meet minimum standards
4. **Early Detection**: Finds issues before they cause problems downstream
5. **Documentation Quality**: Encourages thorough project documentation

## Future Enhancements

Potential improvements:

- [ ] Validate technical stack compatibility
- [ ] Check for security requirements
- [ ] Validate timeline feasibility
- [ ] Suggest missing sections based on project type
- [ ] Integration with IDE/editor extensions
- [ ] Auto-fix common issues
- [ ] Custom validation rules per project type
- [ ] Validation severity levels (error/warning/info)

## Contributing

To add new validation rules:

1. Add the rule to `ProjectBriefValidator` class
2. Create tests in `test_project_brief_validator.py`
3. Update this documentation
4. Ensure backward compatibility

## License

Part of the AI-Optimized Project Template - MIT License
