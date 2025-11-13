#!/usr/bin/env python3
"""
Test script for PROJECT_BRIEF.md validator
Tests validation with different scenarios
"""

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

sys.path.insert(0, 'src')
from utils.project_brief_validator import validate_project_brief, ProjectBriefValidator


def test_valid_project_brief():
    """Test with the actual PROJECT_BRIEF.md"""
    print("=" * 70)
    print("Test 1: Validate actual PROJECT_BRIEF.md")
    print("=" * 70)

    result = validate_project_brief(Path('PROJECT_BRIEF.md'))
    print(result.get_summary())
    print()

    assert result.is_valid, "PROJECT_BRIEF.md should be valid"
    print("✅ Test 1 PASSED: Valid PROJECT_BRIEF.md accepted\n")


def test_missing_success_criteria():
    """Test with missing Success Criteria section"""
    print("=" * 70)
    print("Test 2: Missing Success Criteria section")
    print("=" * 70)

    content = """# Project Brief

## Project Overview

**Project Name**: Test Project

**Brief Description**: This is a test project with a sufficiently long description to pass validation.

**Problem Statement**: This is a problem statement that is long enough to meet the minimum length requirement for validation purposes.

**Target Users**: Developers and testers

---

## Core Requirements

### Functional Requirements
1. Feature one
2. Feature two
3. Feature three

---

## Technical Preferences

- Python
- Django
- PostgreSQL

---
"""

    with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()

        result = validate_project_brief(Path(f.name))
        print(result.get_summary())
        print()

        Path(f.name).unlink()

    assert not result.is_valid, "Should fail without Success Criteria"
    assert any("Success Criteria" in error for error in result.errors), \
        "Should have error about missing Success Criteria"
    print("✅ Test 2 PASSED: Missing Success Criteria detected\n")


def test_section_variations():
    """Test that section variations are accepted"""
    print("=" * 70)
    print("Test 3: Section name variations")
    print("=" * 70)

    content = """# Project Brief

## Overview

**Project Name**: Test Project

**Brief Description**: This is a test project with a sufficiently long description to pass validation and meet minimum length requirements.

**Problem Statement**: This is a problem statement that is long enough to meet the minimum length requirement for validation purposes. We need to solve the issue of insufficient testing coverage and improve deployment speed.

**Target Users**: Developers, testers, DevOps engineers, and project managers

---

## Core Features

### Functional Requirements
1. Feature one - implement user authentication with OAuth2 support
2. Feature two - create RESTful API endpoints for data management
3. Feature three - build responsive dashboard with real-time updates
4. Feature four - integrate third-party payment processing
5. Feature five - implement comprehensive logging and monitoring

### Non-Functional Requirements
- Performance: Response time under 200ms
- Security: Industry-standard encryption
- Scalability: Support 10,000+ concurrent users

---

## Technical Requirements

### Backend
- Python 3.11+
- Django 4.2+
- PostgreSQL 14+
- Redis for caching

### Frontend
- React 18+
- TypeScript
- Material-UI

### Infrastructure
- Docker containers
- Kubernetes orchestration
- AWS cloud hosting

---

## Success Criteria

1. Metric one - achieve 90% code coverage with automated tests
2. Metric two - deploy to production within 1 hour of commit
3. Metric three - zero critical security vulnerabilities
4. Metric four - API response time under 200ms for 95% of requests
5. Metric five - successfully handle 10,000 concurrent users

---
"""

    with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()

        result = validate_project_brief(Path(f.name))
        print(result.get_summary())
        print()

        Path(f.name).unlink()

    assert result.is_valid, "Should accept section variations"
    print("✅ Test 3 PASSED: Section variations accepted\n")


def test_empty_success_criteria():
    """Test with empty Success Criteria section"""
    print("=" * 70)
    print("Test 4: Empty Success Criteria section")
    print("=" * 70)

    content = """# Project Brief

## Project Overview

**Project Name**: Test Project

**Brief Description**: This is a test project with a sufficiently long description to pass validation.

**Problem Statement**: This is a problem statement that is long enough to meet the minimum length requirement for validation purposes.

**Target Users**: Developers and testers

---

## Core Requirements

### Functional Requirements
1. Feature one
2. Feature two
3. Feature three

---

## Technical Preferences

- Python
- Django
- PostgreSQL

---

## Success Criteria

---
"""

    with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()

        result = validate_project_brief(Path(f.name))
        print(result.get_summary())
        print()

        Path(f.name).unlink()

    assert not result.is_valid, "Should fail with empty Success Criteria"
    assert any("too short" in error.lower() for error in result.errors), \
        "Should have error about Success Criteria being too short"
    print("✅ Test 4 PASSED: Empty Success Criteria detected\n")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "PROJECT_BRIEF.md VALIDATOR TESTS" + " " * 20 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    try:
        test_valid_project_brief()
        test_missing_success_criteria()
        test_section_variations()
        test_empty_success_criteria()

        print("=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
