"""
PROJECT_BRIEF.md Validator

Validates PROJECT_BRIEF.md structure and required fields before AI generation
to prevent wasted API calls and provide better error messages.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from logging_config import get_logger
from utils.exceptions import (
    FileNotFoundError as SeedGPTFileNotFoundError,
    FileReadError,
    ProjectBriefValidationError,
    ValidationError,
)

logger = get_logger(__name__)


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
    REQUIRED_SECTIONS = [
        "Project Overview",
        "Core Requirements",
        "Technical Preferences",
        "User Roles & Permissions",
        "Key User Flows",
    ]

    # Optional but recommended sections
    RECOMMENDED_SECTIONS = [
        "Data Model",
        "External Integrations",
        "Timeline & Priorities",
        "Budget & Resources",
    ]

    # Required fields in Project Overview
    REQUIRED_OVERVIEW_FIELDS = [
        "Project Name",
        "Brief Description",
        "Problem Statement",
        "Target Users",
    ]

    # Minimum content length thresholds (characters) - lenient for AI consumption
    MIN_DESCRIPTION_LENGTH = 20
    MIN_PROBLEM_STATEMENT_LENGTH = 30
    MIN_REQUIREMENTS_LENGTH = 30

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
            result.add_error(
                f"PROJECT_BRIEF.md not found at: {self.project_brief_path}"
            )
            return result

        # Read file content
        try:
            content = self.project_brief_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode PROJECT_BRIEF.md with UTF-8 encoding: {e}")
            result.add_error(f"Failed to read PROJECT_BRIEF.md: Invalid UTF-8 encoding")
            return result
        except PermissionError as e:
            logger.error(f"Permission denied when reading PROJECT_BRIEF.md: {e}")
            result.add_error(f"Failed to read PROJECT_BRIEF.md: Permission denied")
            return result
        except OSError as e:
            logger.error(f"OS error reading PROJECT_BRIEF.md: {e}")
            result.add_error(f"Failed to read PROJECT_BRIEF.md: {e}")
            return result

        if not content.strip():
            result.add_error("PROJECT_BRIEF.md is empty")
            return result

        # Store metadata
        result.metadata["file_size"] = len(content)
        result.metadata["line_count"] = content.count("\n") + 1

        # Validate structure
        self._validate_sections(content, result)

        # Validate content
        self._validate_content(content, result)

        # Validate overview section
        self._validate_overview_section(content, result)

        # Validate requirements section
        self._validate_requirements_section(content, result)

        # Check for common issues
        self._check_common_issues(content, result)

        return result

    def _validate_sections(self, content: str, result: ValidationResult):
        """Validate that required sections exist"""
        # Extract all headers (## Section Name)
        headers = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)

        result.metadata["sections_found"] = headers

        # Check required sections - just search for section name case-insensitively
        for required_section in self.REQUIRED_SECTIONS:
            if required_section.lower() not in content.lower():
                result.add_error(f"Missing required section: '{required_section}'")

        # Check recommended sections
        for recommended_section in self.RECOMMENDED_SECTIONS:
            if recommended_section.lower() not in content.lower():
                result.add_warning(
                    f"Missing recommended section: '{recommended_section}'"
                )

    def _validate_content(self, content: str, result: ValidationResult):
        """Validate overall content quality"""
        # Check minimum length - reduced to be more lenient
        if len(content) < 500:
            result.add_warning(
                f"PROJECT_BRIEF.md is quite short ({len(content)} chars). "
                "Recommended minimum: 1000 characters for comprehensive documentation"
            )

        # Check for placeholder text
        placeholder_patterns = [
            r"\[.*?\]",  # [Placeholder text]
            r"TODO",
            r"FIXME",
            r"TBD",
            r"Fill.*here",
            r"Your.*here",
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
        # Just search for "project overview" case-insensitively
        if "project overview" not in content.lower():
            result.add_warning("Could not find Project Overview section - skipping detailed validation")
            return
            
        overview_match = re.search(
            r"project overview.*?\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if not overview_match:
            result.add_warning("Could not parse Project Overview section - skipping detailed validation")
            return

        overview_content = overview_match.group(1)

        # Check required fields
        for field in self.REQUIRED_OVERVIEW_FIELDS:
            pattern = re.compile(
                r"\*\*" + re.escape(field) + r"\*\*\s*:\s*(.+)", re.IGNORECASE
            )
            match = pattern.search(overview_content)

            if not match:
                result.add_error(
                    f"Missing required field in Project Overview: '{field}'"
                )
            else:
                # Check field content length
                field_content = match.group(1).strip()

                if (
                    field == "Brief Description"
                    and len(field_content) < self.MIN_DESCRIPTION_LENGTH
                ):
                    result.add_warning(
                        f"'{field}' is too short ({len(field_content)} chars). "
                        f"Recommended minimum: {self.MIN_DESCRIPTION_LENGTH} characters"
                    )

                if (
                    field == "Problem Statement"
                    and len(field_content) < self.MIN_PROBLEM_STATEMENT_LENGTH
                ):
                    result.add_warning(
                        f"'{field}' is too short ({len(field_content)} chars). "
                        f"Recommended minimum: {self.MIN_PROBLEM_STATEMENT_LENGTH} characters"
                    )

    def _validate_requirements_section(self, content: str, result: ValidationResult):
        """Validate Core Requirements section"""
        # Just search for "core requirements" case-insensitively
        if "core requirements" not in content.lower():
            result.add_warning("Could not find Core Requirements section - skipping detailed validation")
            return
            
        requirements_match = re.search(
            r"core requirements.*?\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if not requirements_match:
            result.add_warning("Could not parse Core Requirements section - skipping detailed validation")
            return

        requirements_content = requirements_match.group(1)

        # Check minimum length - make this a warning instead of error
        if len(requirements_content.strip()) < self.MIN_REQUIREMENTS_LENGTH:
            result.add_warning(
                f"Core Requirements section is too short ({len(requirements_content)} chars). "
                f"Minimum recommended: {self.MIN_REQUIREMENTS_LENGTH} characters"
            )

        # Check for both functional and non-functional requirements
        has_functional = re.search(
            r"Functional Requirements", requirements_content, re.IGNORECASE
        )
        has_non_functional = re.search(
            r"Non-Functional Requirements", requirements_content, re.IGNORECASE
        )

        if not has_functional:
            result.add_warning("Missing 'Functional Requirements' subsection")

        if not has_non_functional:
            result.add_warning("Missing 'Non-Functional Requirements' subsection")

        # Count requirements (numbered or bulleted lists) - more lenient pattern
        functional_reqs = len(
            re.findall(r"^\s*[-*]\s+", requirements_content, re.MULTILINE)
        )

        if functional_reqs < 2:
            result.add_warning(
                f"Only {functional_reqs} requirements found. Consider adding more specific requirements."
            )

    def _check_common_issues(self, content: str, result: ValidationResult):
        """Check for common issues and anti-patterns"""
        # Check for excessively long lines
        lines = content.split("\n")
        long_lines = [
            i + 1
            for i, line in enumerate(lines)
            if len(line) > 200 and not line.startswith("http")
        ]

        if long_lines:
            result.add_warning(
                f"Found {len(long_lines)} lines longer than 200 characters. "
                "Consider breaking them up for readability."
            )

        # Skip empty section check - AI can handle free-form text and various formats

        # Check completion checklist if exists
        if "completion checklist" in content.lower():
            # Check if checklist items are marked complete
            checklist_match = re.search(
                r"completion checklist.*?\n(.*?)(?=\n##|\Z)",
                content,
                re.DOTALL | re.IGNORECASE,
            )

            if checklist_match:
                checklist_content = checklist_match.group(1)
                unchecked = len(re.findall(r"-\s+\[\s\]", checklist_content))
                checked = len(
                    re.findall(r"-\s+\[x\]", checklist_content, re.IGNORECASE)
                )

                result.metadata["checklist_progress"] = {
                    "checked": checked,
                    "unchecked": unchecked,
                    "total": checked + unchecked,
                }

                if unchecked > 0:
                    result.add_warning(
                        f"Completion checklist has {unchecked} unchecked items. "
                        "Ensure all sections are complete before AI generation."
                    )


def validate_project_brief(
    project_brief_path: Optional[Path] = None,
) -> ValidationResult:
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

    summary = result.get_summary()

    if result.is_valid:
        logger.info(summary)
    else:
        logger.error(summary)

    if not result.is_valid:
        logger.warning("Please fix the errors before running AI generation.")
        raise SystemExit(1)

    if result.warnings:
        logger.warning("Consider addressing the warnings for better AI generation results.")


def get_project_brief(max_length: int = 5000) -> str:
    """
    Load PROJECT_BRIEF.md content if it exists
    
    Args:
        max_length: Maximum length of content to return (default: 5000 chars)
    
    Returns:
        str: Content of PROJECT_BRIEF.md or empty string if not found
    """
    project_brief_path = Path("PROJECT_BRIEF.md")
    
    if not project_brief_path.exists():
        return ""
    
    try:
        with open(project_brief_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Limit to reasonable size to avoid token limits
        return content[:max_length]
    except Exception as e:
        logger.warning(f"Failed to read PROJECT_BRIEF.md: {e}")
        return ""
