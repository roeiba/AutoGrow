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
    """
    Validator for PROJECT_BRIEF.md format and content

    Ensures PROJECT_BRIEF.md has all required sections before AI generation starts.
    This prevents incomplete briefs and improves generation quality by validating:
    - Overview (Project Overview)
    - Core Features (Core Requirements)
    - Technical Requirements (Technical Preferences)
    - Success Criteria (Timeline & Priorities/Completion Checklist)
    """

    # Required sections in PROJECT_BRIEF.md
    # These are the essential sections needed for quality AI generation
    REQUIRED_SECTIONS = [
        "Project Overview",        # Overview: What is the project about?
        "Core Requirements",       # Core Features: What should it do?
        "Technical Preferences",   # Technical Requirements: How should it be built?
        "User Roles & Permissions", # Who will use it?
        "Key User Flows"           # How will it be used?
    ]

    # Optional but recommended sections for complete project planning
    RECOMMENDED_SECTIONS = [
        "Data Model",              # What data structures are needed?
        "External Integrations",   # What external services to integrate?
        "Timeline & Priorities",   # Success Criteria: When and what to deliver?
        "Budget & Resources"       # What resources are available?
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

        This validation ensures the brief has all required sections before AI generation,
        preventing incomplete briefs and wasted API calls.

        Returns:
            ValidationResult with validation outcome and messages
        """
        result = ValidationResult(is_valid=True)

        # Check file exists
        if not self.project_brief_path.exists():
            result.add_error(f"PROJECT_BRIEF.md not found at: {self.project_brief_path}")
            result.add_error("A complete PROJECT_BRIEF.md is required before AI generation can start.")
            return result

        # Read file content
        try:
            content = self.project_brief_path.read_text(encoding='utf-8')
        except Exception as e:
            result.add_error(f"Failed to read PROJECT_BRIEF.md: {e}")
            return result

        if not content.strip():
            result.add_error("PROJECT_BRIEF.md is empty")
            result.add_error("Please fill in all required sections before starting AI generation.")
            return result

        # Store metadata
        result.metadata['file_size'] = len(content)
        result.metadata['line_count'] = content.count('\n') + 1

        # Validate structure - CRITICAL: Must have all required sections
        self._validate_sections(content, result)

        # Validate content quality
        self._validate_content(content, result)

        # Validate overview section details
        self._validate_overview_section(content, result)

        # Validate requirements section details
        self._validate_requirements_section(content, result)

        # Check for common issues and completion status
        self._check_common_issues(content, result)

        return result

    def _validate_sections(self, content: str, result: ValidationResult):
        """
        Validate that required sections exist in PROJECT_BRIEF.md

        This is a critical validation to ensure all essential information is present
        before AI generation starts, preventing incomplete briefs and improving output quality.
        """
        # Extract all headers (## Section Name)
        headers = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)

        result.metadata['sections_found'] = headers

        missing_required = []

        # Check required sections
        for required_section in self.REQUIRED_SECTIONS:
            # Use emoji-agnostic matching - match any Unicode character (including emojis) before section name
            # Pattern: ## (any chars including emoji) SectionName
            pattern = re.compile(r'##\s+.*?' + re.escape(required_section), re.IGNORECASE)
            if not pattern.search(content):
                missing_required.append(required_section)
                result.add_error(f"Missing required section: '{required_section}'")

        # Add summary error if multiple sections missing
        if len(missing_required) > 1:
            result.add_error(
                f"PROJECT_BRIEF.md is incomplete. Missing {len(missing_required)} required sections. "
                "All sections must be present before AI generation can start."
            )

        # Check recommended sections
        missing_recommended = []
        for recommended_section in self.RECOMMENDED_SECTIONS:
            # Use emoji-agnostic matching - match any Unicode character (including emojis) before section name
            pattern = re.compile(r'##\s+.*?' + re.escape(recommended_section), re.IGNORECASE)
            if not pattern.search(content):
                missing_recommended.append(recommended_section)
                result.add_warning(f"Missing recommended section: '{recommended_section}'")

        # Add informative warning about recommended sections
        if len(missing_recommended) > 1:
            result.add_warning(
                f"Consider adding {len(missing_recommended)} recommended sections for better AI generation results."
            )

    def _validate_content(self, content: str, result: ValidationResult):
        """Validate overall content quality"""
        # Check minimum length (as warning, not error - sections are more important)
        if len(content) < 1000:
            result.add_warning(
                f"PROJECT_BRIEF.md is short ({len(content)} chars). "
                "Recommended minimum: 1000 characters for best AI generation results"
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
        # Extract overview section (with optional emoji or other characters before it)
        overview_match = re.search(
            r'##\s+.*?Project Overview\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if not overview_match:
            result.add_error("Could not parse Project Overview section")
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
        """Validate Core Requirements section"""
        requirements_match = re.search(
            r'##\s+.*?Core Requirements\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if not requirements_match:
            result.add_error("Could not parse Core Requirements section")
            return

        requirements_content = requirements_match.group(1)

        # Check minimum length (as warning, not error - having the section is more important)
        if len(requirements_content.strip()) < self.MIN_REQUIREMENTS_LENGTH:
            result.add_warning(
                f"Core Requirements section is short ({len(requirements_content)} chars). "
                f"Recommended minimum: {self.MIN_REQUIREMENTS_LENGTH} characters for better AI generation"
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

        # Check for truly empty sections (no content at all, not even subsections)
        # A section is empty if it has ONLY whitespace and/or horizontal rules
        empty_sections = []
        # Match section headers and their content up to the next section or end of file
        section_pattern = re.finditer(r'^##\s+(.+?)\s*$(.*?)(?=^##\s|\Z)', content, re.MULTILINE | re.DOTALL)
        for match in section_pattern:
            section_name = match.group(1).strip()
            section_content = match.group(2).strip()
            # Remove horizontal rules to see if there's any actual content
            content_without_rules = re.sub(r'^---+\s*$|^\*\*\*+\s*$|^___+\s*$', '', section_content, flags=re.MULTILINE).strip()
            # Check if section has no content after removing rules
            if not content_without_rules:
                empty_sections.append(section_name)

        if empty_sections:
            result.add_error(
                f"Found empty sections: {', '.join(empty_sections[:3])}"
            )

        # Check completion checklist if exists
        if '## ✅ Completion Checklist' in content or '## Completion Checklist' in content:
            # Check if checklist items are marked complete
            checklist_match = re.search(
                r'##\s+.*?Completion Checklist\s*\n(.*?)(?=\n##|\Z)',
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

    This function ensures all required sections are present before AI generation starts,
    preventing incomplete briefs and improving generation quality.

    Args:
        project_brief_path: Path to PROJECT_BRIEF.md file

    Raises:
        SystemExit: If validation fails (missing required sections or invalid format)
    """
    result = validate_project_brief(project_brief_path)

    print(result.get_summary())

    if not result.is_valid:
        print("\n⚠️  PROJECT_BRIEF.md validation failed!")
        print("⚠️  Please fix the errors before running AI generation.")
        print("⚠️  This validation prevents incomplete briefs and ensures quality output.")
        raise SystemExit(1)

    if result.warnings:
        print("\n⚠️  Consider addressing the warnings for better AI generation results.")
