"""
PROJECT_BRIEF.md Validator

Validates PROJECT_BRIEF.md structure and required fields before AI generation
to prevent wasted API calls and provide better error messages.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of PROJECT_BRIEF.md validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)

    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)

    def get_summary(self) -> str:
        """Get a human-readable summary of validation results"""
        if self.is_valid:
            summary = "✅ PROJECT_BRIEF.md validation passed"
            if self.warnings:
                summary += f" ({len(self.warnings)} warning(s))"
        else:
            summary = f"❌ PROJECT_BRIEF.md validation failed with {len(self.errors)} error(s)"

        if self.errors:
            summary += "\n\nErrors:"
            for error in self.errors:
                summary += f"\n  - {error}"

        if self.warnings:
            summary += "\n\nWarnings:"
            for warning in self.warnings:
                summary += f"\n  - {warning}"

        return summary


class ProjectBriefValidator:
    """Validator for PROJECT_BRIEF.md format and content"""

    # Required sections in PROJECT_BRIEF.md
    # Note: Section names can have variations (e.g., "Core Features" or "Core Requirements")
    REQUIRED_SECTIONS = [
        "Project Overview",
        "Core Requirements",  # Also accepts: "Core Features"
        "Technical Preferences",  # Also accepts: "Technical Requirements"
        "Success Criteria"
    ]

    # Optional but recommended sections
    RECOMMENDED_SECTIONS = [
        "Data Model",
        "External Integrations",
        "Timeline & Priorities",
        "Budget & Resources"
    ]

    # Required fields in Project Overview
    REQUIRED_OVERVIEW_FIELDS = [
        "Project Name",
        "Brief Description",
        "Problem Statement",
        "Target Users"
    ]

    # Minimum content length thresholds (characters)
    MIN_DESCRIPTION_LENGTH = 50
    MIN_PROBLEM_STATEMENT_LENGTH = 100
    MIN_REQUIREMENTS_LENGTH = 100

    def __init__(self, project_brief_path: Optional[Path] = None):
        """
        Initialize validator

        Args:
            project_brief_path: Path to PROJECT_BRIEF.md file
        """
        if project_brief_path is None:
            # Default to PROJECT_BRIEF.md in repo root
            self.project_brief_path = Path.cwd() / "PROJECT_BRIEF.md"
        else:
            self.project_brief_path = Path(project_brief_path)

    def validate(self) -> ValidationResult:
        """
        Perform comprehensive validation of PROJECT_BRIEF.md

        Returns:
            ValidationResult with validation outcome and messages
        """
        result = ValidationResult(is_valid=True)

        # Check file exists
        if not self.project_brief_path.exists():
            result.add_error(f"PROJECT_BRIEF.md not found at: {self.project_brief_path}")
            return result

        # Read file content
        try:
            content = self.project_brief_path.read_text(encoding='utf-8')
        except Exception as e:
            result.add_error(f"Failed to read PROJECT_BRIEF.md: {e}")
            return result

        if not content.strip():
            result.add_error("PROJECT_BRIEF.md is empty")
            return result

        # Store metadata
        result.metadata['file_size'] = len(content)
        result.metadata['line_count'] = content.count('\n') + 1

        # Validate structure
        self._validate_sections(content, result)

        # Validate content
        self._validate_content(content, result)

        # Validate overview section
        self._validate_overview_section(content, result)

        # Validate requirements section
        self._validate_requirements_section(content, result)

        # Validate success criteria section
        self._validate_success_criteria_section(content, result)

        # Check for common issues
        self._check_common_issues(content, result)

        return result

    def _validate_sections(self, content: str, result: ValidationResult):
        """Validate that required sections exist"""
        # Extract all headers (## Section Name)
        headers = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)

        result.metadata['sections_found'] = headers

        # Define section variations that are acceptable
        section_variations = {
            "Project Overview": ["Project Overview", "Overview"],
            "Core Requirements": ["Core Requirements", "Core Features", "Features", "Requirements"],
            "Technical Preferences": ["Technical Preferences", "Technical Requirements", "Tech Stack", "Technology Stack"],
            "Success Criteria": ["Success Criteria", "Acceptance Criteria", "Definition of Done"]
        }

        # Check required sections (accepting variations)
        for required_section in self.REQUIRED_SECTIONS:
            variations = section_variations.get(required_section, [required_section])
            found = False

            for variation in variations:
                # Use emoji-agnostic matching
                pattern = re.compile(r'##\s+[🎯📋🏗️👥🔄✅]?\s*' + re.escape(variation), re.IGNORECASE)
                if pattern.search(content):
                    found = True
                    break

            if not found:
                # Show all acceptable variations in error message
                variations_str = "', '".join(variations)
                result.add_error(f"Missing required section: '{required_section}' (also accepts: '{variations_str}')")

        # Check recommended sections
        for recommended_section in self.RECOMMENDED_SECTIONS:
            pattern = re.compile(r'##\s+[🗄️🔌📅💰]?\s*' + re.escape(recommended_section), re.IGNORECASE)
            if not pattern.search(content):
                result.add_warning(f"Missing recommended section: '{recommended_section}'")

    def _validate_content(self, content: str, result: ValidationResult):
        """Validate overall content quality"""
        # Check minimum length
        if len(content) < 1000:
            result.add_error(
                f"PROJECT_BRIEF.md is too short ({len(content)} chars). "
                "Minimum recommended: 1000 characters"
            )

        # Check for placeholder text
        placeholder_patterns = [
            r'\[.*?\]',  # [Placeholder text]
            r'TODO',
            r'FIXME',
            r'TBD',
            r'Fill.*here',
            r'Your.*here'
        ]

        placeholders_found = []
        for pattern in placeholder_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            placeholders_found.extend(matches)

        if placeholders_found:
            result.add_warning(
                f"Found {len(placeholders_found)} potential placeholders that may need completion: "
                f"{', '.join(set(placeholders_found[:5]))}"
            )

    def _validate_overview_section(self, content: str, result: ValidationResult):
        """Validate Project Overview section"""
        # Try different variations
        overview_match = None
        for section_name in ["Project Overview", "Overview"]:
            overview_match = re.search(
                r'##\s+[🎯]?\s*' + re.escape(section_name) + r'\s*\n(.*?)(?=\n##|\Z)',
                content,
                re.DOTALL | re.IGNORECASE
            )
            if overview_match:
                break

        if not overview_match:
            result.add_error("Could not parse Project Overview/Overview section")
            return

        overview_content = overview_match.group(1)

        # Check required fields
        for field in self.REQUIRED_OVERVIEW_FIELDS:
            pattern = re.compile(r'\*\*' + re.escape(field) + r'\*\*\s*:\s*(.+)', re.IGNORECASE)
            match = pattern.search(overview_content)

            if not match:
                result.add_error(f"Missing required field in Project Overview: '{field}'")
            else:
                # Check field content length
                field_content = match.group(1).strip()

                if field == "Brief Description" and len(field_content) < self.MIN_DESCRIPTION_LENGTH:
                    result.add_warning(
                        f"'{field}' is too short ({len(field_content)} chars). "
                        f"Recommended minimum: {self.MIN_DESCRIPTION_LENGTH} characters"
                    )

                if field == "Problem Statement" and len(field_content) < self.MIN_PROBLEM_STATEMENT_LENGTH:
                    result.add_warning(
                        f"'{field}' is too short ({len(field_content)} chars). "
                        f"Recommended minimum: {self.MIN_PROBLEM_STATEMENT_LENGTH} characters"
                    )

    def _validate_requirements_section(self, content: str, result: ValidationResult):
        """Validate Core Requirements/Features section"""
        # Try different variations
        requirements_match = None
        for section_name in ["Core Requirements", "Core Features", "Features", "Requirements"]:
            requirements_match = re.search(
                r'##\s+[📋]?\s*' + re.escape(section_name) + r'\s*\n(.*?)(?=\n##|\Z)',
                content,
                re.DOTALL | re.IGNORECASE
            )
            if requirements_match:
                break

        if not requirements_match:
            result.add_error("Could not parse Core Requirements/Features section")
            return

        requirements_content = requirements_match.group(1)

        # Check minimum length
        if len(requirements_content.strip()) < self.MIN_REQUIREMENTS_LENGTH:
            result.add_error(
                f"Core Requirements section is too short ({len(requirements_content)} chars). "
                f"Minimum recommended: {self.MIN_REQUIREMENTS_LENGTH} characters"
            )

        # Check for both functional and non-functional requirements
        has_functional = re.search(r'Functional Requirements', requirements_content, re.IGNORECASE)
        has_non_functional = re.search(r'Non-Functional Requirements', requirements_content, re.IGNORECASE)

        if not has_functional:
            result.add_warning("Missing 'Functional Requirements' subsection")

        if not has_non_functional:
            result.add_warning("Missing 'Non-Functional Requirements' subsection")

        # Count requirements (numbered or bulleted lists)
        functional_reqs = len(re.findall(r'^\s*[\d\-\*]\.\s+', requirements_content, re.MULTILINE))

        if functional_reqs < 3:
            result.add_warning(
                f"Only {functional_reqs} requirements found. Consider adding more specific requirements."
            )

    def _validate_success_criteria_section(self, content: str, result: ValidationResult):
        """Validate Success Criteria section"""
        # Try different variations
        success_criteria_match = None
        for section_name in ["Success Criteria", "Acceptance Criteria", "Definition of Done"]:
            success_criteria_match = re.search(
                r'##\s+[✅]?\s*' + re.escape(section_name) + r'\s*\n(.*?)(?=\n##|\Z)',
                content,
                re.DOTALL | re.IGNORECASE
            )
            if success_criteria_match:
                break

        if not success_criteria_match:
            result.add_error("Could not parse Success Criteria section")
            return

        success_criteria_content = success_criteria_match.group(1)

        # Check minimum length
        MIN_SUCCESS_CRITERIA_LENGTH = 50
        if len(success_criteria_content.strip()) < MIN_SUCCESS_CRITERIA_LENGTH:
            result.add_error(
                f"Success Criteria section is too short ({len(success_criteria_content.strip())} chars). "
                f"Minimum recommended: {MIN_SUCCESS_CRITERIA_LENGTH} characters"
            )

        # Count criteria items (numbered or bulleted lists)
        criteria_items = len(re.findall(r'^\s*[\d\-\*]+\.?\s+', success_criteria_content, re.MULTILINE))

        if criteria_items == 0:
            result.add_warning(
                "Success Criteria section has no measurable criteria items. "
                "Consider adding specific, measurable success metrics."
            )
        elif criteria_items < 3:
            result.add_warning(
                f"Only {criteria_items} success criteria found. "
                "Consider adding more specific and measurable criteria."
            )

    def _check_common_issues(self, content: str, result: ValidationResult):
        """Check for common issues and anti-patterns"""
        # Check for excessively long lines
        lines = content.split('\n')
        long_lines = [i + 1 for i, line in enumerate(lines) if len(line) > 200 and not line.startswith('http')]

        if long_lines:
            result.add_warning(
                f"Found {len(long_lines)} lines longer than 200 characters. "
                "Consider breaking them up for readability."
            )

        # Check for empty sections (sections with no content before the next section)
        # Look for ## headers followed by only whitespace and then another ## header
        # Exclude cases where there's a ### subsection
        empty_sections = []
        section_pattern = re.compile(r'##\s+(.+?)\s*\n(.*?)(?=\n##|\Z)', re.DOTALL)
        for match in section_pattern.finditer(content):
            section_name = match.group(1)
            section_content = match.group(2).strip()
            # Check if section is truly empty (no content, not even subsections)
            if not section_content or (section_content and not re.search(r'\S', section_content)):
                empty_sections.append(section_name)

        if empty_sections:
            result.add_error(
                f"Found empty sections: {', '.join(empty_sections[:3])}"
            )

        # Check completion checklist if exists
        if '## ✅ Completion Checklist' in content or '## Completion Checklist' in content:
            # Check if checklist items are marked complete
            checklist_match = re.search(
                r'##\s+[✅]?\s*Completion Checklist\s*\n(.*?)(?=\n##|\Z)',
                content,
                re.DOTALL | re.IGNORECASE
            )

            if checklist_match:
                checklist_content = checklist_match.group(1)
                unchecked = len(re.findall(r'-\s+\[\s\]', checklist_content))
                checked = len(re.findall(r'-\s+\[x\]', checklist_content, re.IGNORECASE))

                result.metadata['checklist_progress'] = {
                    'checked': checked,
                    'unchecked': unchecked,
                    'total': checked + unchecked
                }

                if unchecked > 0:
                    result.add_warning(
                        f"Completion checklist has {unchecked} unchecked items. "
                        "Ensure all sections are complete before AI generation."
                    )


def validate_project_brief(project_brief_path: Optional[Path] = None) -> ValidationResult:
    """
    Convenience function to validate PROJECT_BRIEF.md

    Args:
        project_brief_path: Path to PROJECT_BRIEF.md file

    Returns:
        ValidationResult with validation outcome
    """
    validator = ProjectBriefValidator(project_brief_path)
    return validator.validate()


def validate_or_exit(project_brief_path: Optional[Path] = None) -> None:
    """
    Validate PROJECT_BRIEF.md and exit if validation fails

    Args:
        project_brief_path: Path to PROJECT_BRIEF.md file

    Raises:
        SystemExit: If validation fails
    """
    result = validate_project_brief(project_brief_path)

    print(result.get_summary())

    if not result.is_valid:
        print("\n⚠️  Please fix the errors before running AI generation.")
        raise SystemExit(1)

    if result.warnings:
        print("\n⚠️  Consider addressing the warnings for better AI generation results.")
