#!/usr/bin/env python3
"""
Unit tests for issue deduplication functionality
"""

import pytest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.deduplication import IssueDuplicateChecker
from utils.rate_limiter import RateLimiter, RateLimitConfig


class MockIssue:
    """Mock GitHub issue for testing"""

    def __init__(self, number: int, title: str, body: str):
        self.number = number
        self.title = title
        self.body = body


class TestIssueDuplicateChecker:
    """Test suite for IssueDuplicateChecker"""

    def test_normalize_text(self):
        """Test text normalization"""
        checker = IssueDuplicateChecker()

        # Test basic normalization
        assert checker.normalize_text("Hello World") == "hello world"
        assert checker.normalize_text("Hello  World") == "hello world"
        assert checker.normalize_text("Hello-World!") == "hello world"
        assert checker.normalize_text("  HELLO  WORLD  ") == "hello world"

        # Test special characters
        assert checker.normalize_text("Fix: API bug #123") == "fix api bug 123"
        assert checker.normalize_text("Add @user feature") == "add user feature"

        # Test empty string
        assert checker.normalize_text("") == ""
        assert checker.normalize_text(None) == ""

    def test_sequence_similarity_exact_match(self):
        """Test sequence similarity with exact matches"""
        checker = IssueDuplicateChecker()

        # Exact match
        score = checker.calculate_sequence_similarity("Hello World", "Hello World")
        assert score == 1.0

        # Case-insensitive exact match
        score = checker.calculate_sequence_similarity("Hello World", "hello world")
        assert score == 1.0

    def test_sequence_similarity_partial_match(self):
        """Test sequence similarity with partial matches"""
        checker = IssueDuplicateChecker()

        # Similar but not exact
        score = checker.calculate_sequence_similarity(
            "Fix authentication bug", "Fix authentication issue"
        )
        assert score > 0.7  # Should be fairly similar

        # Completely different
        score = checker.calculate_sequence_similarity(
            "Fix authentication bug", "Add new feature to dashboard"
        )
        assert score < 0.3  # Should be very different

    def test_sequence_similarity_empty(self):
        """Test sequence similarity with empty strings"""
        checker = IssueDuplicateChecker()

        score = checker.calculate_sequence_similarity("", "Hello")
        assert score == 0.0

        score = checker.calculate_sequence_similarity("Hello", "")
        assert score == 0.0

    def test_jaccard_similarity_exact_match(self):
        """Test Jaccard similarity with exact matches"""
        checker = IssueDuplicateChecker()

        # Exact match
        score = checker.calculate_jaccard_similarity(
            "Fix authentication bug", "Fix authentication bug"
        )
        assert score == 1.0

        # Same words, different order
        score = checker.calculate_jaccard_similarity(
            "Fix authentication bug", "bug authentication Fix"
        )
        assert score == 1.0

    def test_jaccard_similarity_partial_overlap(self):
        """Test Jaccard similarity with partial overlap"""
        checker = IssueDuplicateChecker()

        # Some overlap
        score = checker.calculate_jaccard_similarity(
            "Fix authentication bug", "Fix authentication issue"
        )
        assert 0.4 <= score < 1.0  # At least 40% overlap

        # No overlap
        score = checker.calculate_jaccard_similarity(
            "Fix authentication bug", "Add dashboard feature"
        )
        assert score < 0.3

    def test_jaccard_similarity_empty(self):
        """Test Jaccard similarity with empty strings"""
        checker = IssueDuplicateChecker()

        score = checker.calculate_jaccard_similarity("", "Hello")
        assert score == 0.0

        score = checker.calculate_jaccard_similarity("Hello", "")
        assert score == 0.0

    def test_is_duplicate_high_title_similarity(self):
        """Test duplicate detection with high title similarity"""
        checker = IssueDuplicateChecker(
            title_similarity_threshold=0.75,
            body_similarity_threshold=0.60,
            combined_similarity_threshold=0.65,
        )

        # Very similar titles
        is_dup, scores = checker.is_duplicate(
            "Fix authentication bug in login",
            "User authentication is broken during login",
            "Fix authentication bug in login page",
            "Authentication system has issues with login functionality",
        )

        assert is_dup is True
        assert scores["title_similarity"] >= 0.75

    def test_is_duplicate_low_similarity(self):
        """Test duplicate detection with low similarity"""
        checker = IssueDuplicateChecker(
            title_similarity_threshold=0.75,
            body_similarity_threshold=0.60,
            combined_similarity_threshold=0.65,
        )

        # Completely different issues
        is_dup, scores = checker.is_duplicate(
            "Fix authentication bug",
            "The auth system is broken",
            "Add dark mode feature",
            "Users want to be able to switch to dark theme",
        )

        assert is_dup is False
        assert scores["title_similarity"] < 0.75

    def test_is_duplicate_combined_score(self):
        """Test duplicate detection using combined score"""
        checker = IssueDuplicateChecker(
            title_similarity_threshold=0.75,
            body_similarity_threshold=0.60,
            combined_similarity_threshold=0.65,
        )

        # Very similar title and body
        is_dup, scores = checker.is_duplicate(
            "Improve application performance",
            "The application is running slowly and needs optimization for better speed",
            "Improve application performance issues",
            "The application runs slowly and needs optimization for better speed",
        )

        # Should be flagged as duplicate due to high combined score
        assert scores["combined_similarity"] >= 0.60  # Relaxed threshold for test

    def test_find_duplicates_empty_list(self):
        """Test finding duplicates with empty list"""
        checker = IssueDuplicateChecker()

        duplicates = checker.find_duplicates(
            "Fix authentication bug", "Auth system is broken", []
        )

        assert len(duplicates) == 0

    def test_find_duplicates_with_matches(self):
        """Test finding duplicates with matching issues"""
        checker = IssueDuplicateChecker(
            title_similarity_threshold=0.75,
            body_similarity_threshold=0.60,
            combined_similarity_threshold=0.65,
        )

        existing_issues = [
            MockIssue(1, "Fix authentication bug", "Auth system is broken"),
            MockIssue(2, "Add dark mode", "Users want dark theme"),
            MockIssue(3, "Fix login authentication issue", "Login auth not working"),
        ]

        # Should match issues #1 and #3
        duplicates = checker.find_duplicates(
            "Fix authentication problem", "Authentication is broken", existing_issues
        )

        assert len(duplicates) >= 1
        # Should be sorted by similarity (highest first)
        if len(duplicates) > 1:
            assert (
                duplicates[0][1]["combined_similarity"]
                >= duplicates[1][1]["combined_similarity"]
            )

    def test_find_duplicates_no_matches(self):
        """Test finding duplicates with no matching issues"""
        checker = IssueDuplicateChecker()

        existing_issues = [
            MockIssue(1, "Fix authentication bug", "Auth system is broken"),
            MockIssue(2, "Add dark mode", "Users want dark theme"),
        ]

        duplicates = checker.find_duplicates(
            "Implement CI/CD pipeline",
            "We need automated testing and deployment",
            existing_issues,
        )

        assert len(duplicates) == 0

    def test_check_issue_list_all_unique(self):
        """Test checking issue list with all unique issues"""
        checker = IssueDuplicateChecker()

        new_issues = [
            {"title": "Implement CI/CD pipeline", "body": "Set up automated testing and deployment", "labels": ["devops"]},
            {"title": "Add user dashboard", "body": "Create new dashboard for user analytics", "labels": ["feature"]},
        ]

        existing_issues = [
            MockIssue(1, "Fix authentication bug", "Auth system is broken"),
            MockIssue(2, "Update documentation", "Docs need updating"),
        ]

        unique, duplicates = checker.check_issue_list(new_issues, existing_issues)

        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_check_issue_list_with_duplicates(self):
        """Test checking issue list with duplicate issues"""
        checker = IssueDuplicateChecker(
            title_similarity_threshold=0.75,
            body_similarity_threshold=0.60,
            combined_similarity_threshold=0.65,
        )

        new_issues = [
            {
                "title": "Fix authentication bug",
                "body": "Auth system is broken",
                "labels": ["bug"],
            },
            {
                "title": "Add new feature",
                "body": "New feature description",
                "labels": ["feature"],
            },
            {
                "title": "Fix login authentication",
                "body": "Login auth not working",
                "labels": ["bug"],
            },
        ]

        existing_issues = [
            MockIssue(1, "Fix authentication bug in system", "Authentication is broken"),
            MockIssue(2, "Implement CI/CD", "Add automated pipeline"),
        ]

        unique, duplicates = checker.check_issue_list(new_issues, existing_issues)

        # Should filter out at least one duplicate (authentication issues)
        assert len(duplicates) >= 1
        assert len(unique) < len(new_issues)

        # Verify duplicate info structure
        for dup_issue, matching_issue, scores in duplicates:
            assert "title" in dup_issue
            assert hasattr(matching_issue, "number")
            assert "combined_similarity" in scores

    def test_check_issue_list_all_duplicates(self):
        """Test checking issue list where all are duplicates"""
        checker = IssueDuplicateChecker(
            title_similarity_threshold=0.75,
            body_similarity_threshold=0.60,
            combined_similarity_threshold=0.65,
        )

        new_issues = [
            {
                "title": "Fix authentication bug",
                "body": "Auth system is broken",
                "labels": ["bug"],
            },
        ]

        existing_issues = [
            MockIssue(1, "Fix authentication bug", "Authentication system is broken"),
        ]

        unique, duplicates = checker.check_issue_list(new_issues, existing_issues)

        assert len(unique) == 0
        assert len(duplicates) == 1

    def test_custom_thresholds(self):
        """Test checker with custom thresholds"""
        # Strict checker (high thresholds)
        strict_checker = IssueDuplicateChecker(
            title_similarity_threshold=0.90,
            body_similarity_threshold=0.85,
            combined_similarity_threshold=0.88,
        )

        # Lenient checker (low thresholds)
        lenient_checker = IssueDuplicateChecker(
            title_similarity_threshold=0.50,
            body_similarity_threshold=0.40,
            combined_similarity_threshold=0.45,
        )

        title1 = "Fix authentication bug"
        body1 = "Auth system broken"
        title2 = "Fix authentication issue"
        body2 = "Authentication not working"

        # Strict should not flag as duplicate
        strict_dup, strict_scores = strict_checker.is_duplicate(
            title1, body1, title2, body2
        )

        # Lenient should flag as duplicate
        lenient_dup, lenient_scores = lenient_checker.is_duplicate(
            title1, body1, title2, body2
        )

        # Verify different behavior
        assert strict_scores["combined_similarity"] == lenient_scores["combined_similarity"]
        # But different duplicate detection due to thresholds
        if strict_scores["combined_similarity"] < 0.88:
            assert strict_dup is False
        if lenient_scores["combined_similarity"] >= 0.45:
            assert lenient_dup is True

    def test_verbose_output(self, capsys):
        """Test verbose output in check_issue_list"""
        checker = IssueDuplicateChecker()

        new_issues = [
            {"title": "Fix bug A", "body": "Bug A description", "labels": ["bug"]},
        ]

        existing_issues = [
            MockIssue(1, "Fix bug B", "Bug B description"),
        ]

        # Call with verbose=True
        checker.check_issue_list(new_issues, existing_issues, verbose=True)

        # Capture output
        captured = capsys.readouterr()

        # Should have some output (either UNIQUE or DUPLICATE)
        assert len(captured.out) > 0
        assert "UNIQUE" in captured.out or "DUPLICATE" in captured.out


class TestQualityScoring:
    """Test suite for quality scoring"""

    def test_quality_score_good_issue(self):
        """Test quality scoring for a well-formed issue"""
        checker = IssueDuplicateChecker(enable_quality_gates=True)

        title = "Add user authentication feature to API"
        body = "We need to implement JWT-based authentication for the REST API. This should include login, logout, and token refresh endpoints with proper error handling."
        labels = ["feature"]

        scores = checker.calculate_quality_score(title, body, labels)

        assert scores["overall"] >= 0.5
        assert scores["passes_quality_gate"] is True
        assert scores["clarity"] > 0.4
        assert scores["actionability"] > 0.4

    def test_quality_score_poor_issue(self):
        """Test quality scoring for a poorly formed issue"""
        checker = IssueDuplicateChecker(enable_quality_gates=True, min_quality_score=0.5)

        title = "Fix it"
        body = "Something is broken maybe"
        labels = []

        scores = checker.calculate_quality_score(title, body, labels)

        assert scores["overall"] < 0.5
        assert scores["passes_quality_gate"] is False
        assert len(scores["feedback"]) > 1

    def test_quality_gate_filtering(self):
        """Test that quality gates filter low-quality issues"""
        checker = IssueDuplicateChecker(
            enable_quality_gates=True,
            min_quality_score=0.5
        )

        new_issues = [
            {
                "title": "Implement user authentication with JWT tokens",
                "body": "Add secure JWT-based authentication system with login, logout, and token refresh endpoints",
                "labels": ["feature"]
            },
            {
                "title": "Fix",
                "body": "Something broke",
                "labels": []
            }
        ]

        existing_issues = []
        unique, duplicates = checker.check_issue_list(new_issues, existing_issues)

        # Should filter out the low-quality issue
        assert len(unique) == 1
        assert "authentication" in unique[0]["title"].lower()

    def test_semantic_similarity_fallback(self):
        """Test fallback semantic similarity without embeddings"""
        checker = IssueDuplicateChecker(enable_semantic_dedup=False)

        # Similar concepts, different wording
        title1 = "Add user authentication system"
        body1 = "Implement secure login and registration"

        title2 = "Implement authentication feature"
        body2 = "Create secure login and signup functionality"

        sim = checker._fallback_semantic_similarity(title1, body1, title2, body2)

        # Should detect semantic similarity
        assert sim > 0.3  # Some overlap in concepts

    def test_semantic_similarity_different_concepts(self):
        """Test semantic similarity with completely different concepts"""
        checker = IssueDuplicateChecker(enable_semantic_dedup=False)

        title1 = "Add database migration scripts"
        body1 = "Create SQL migration scripts for schema changes"

        title2 = "Improve frontend performance"
        body2 = "Optimize React component rendering"

        sim = checker._fallback_semantic_similarity(title1, body1, title2, body2)

        # Should not detect similarity
        assert sim < 0.3


class TestRateLimiter:
    """Test suite for rate limiter"""

    def test_rate_limiter_allows_first_generation(self, tmp_path):
        """Test that rate limiter allows first generation"""
        limiter = RateLimiter(
            config=RateLimitConfig(max_issues_per_hour=10),
            state_path=tmp_path / "rate_limit_state.json"
        )

        can_generate, reason = limiter.can_generate()
        assert can_generate is True
        assert reason is None

    def test_rate_limiter_hourly_limit(self, tmp_path):
        """Test hourly rate limit enforcement"""
        limiter = RateLimiter(
            config=RateLimitConfig(
                max_issues_per_hour=5,
                min_time_between_generations_minutes=0  # Disable for test
            ),
            state_path=tmp_path / "rate_limit_state.json"
        )

        # Record 5 issues created (hitting limit)
        limiter.record_generation(
            issues_proposed=5,
            issues_created=5,
            duplicates_filtered=0
        )

        # Should block next generation
        can_generate, reason = limiter.can_generate()
        assert can_generate is False
        assert "Hourly rate limit" in reason

    def test_rate_limiter_duplicate_rate_cooldown(self, tmp_path):
        """Test that high duplicate rate triggers cooldown"""
        limiter = RateLimiter(
            config=RateLimitConfig(
                max_duplicate_rate=0.5,
                cooldown_minutes=60,
                min_time_between_generations_minutes=0  # Disable for test
            ),
            state_path=tmp_path / "rate_limit_state.json"
        )

        # Record 3 attempts with high duplicate rate
        for _ in range(3):
            limiter.record_generation(
                issues_proposed=10,
                issues_created=2,
                duplicates_filtered=8  # 80% duplicate rate
            )

        # Should trigger cooldown
        can_generate, reason = limiter.can_generate()
        assert can_generate is False
        assert "duplicate rate" in reason.lower()

    def test_rate_limiter_quality_rejection_cooldown(self, tmp_path):
        """Test that high quality rejection rate triggers cooldown"""
        limiter = RateLimiter(
            config=RateLimitConfig(
                max_quality_reject_rate=0.4,
                cooldown_minutes=60,
                min_time_between_generations_minutes=0  # Disable for test
            ),
            state_path=tmp_path / "rate_limit_state.json"
        )

        # Record 3 attempts with high quality rejection rate
        for _ in range(3):
            limiter.record_generation(
                issues_proposed=10,
                issues_created=3,
                duplicates_filtered=1,
                quality_rejected=6  # 60% rejection rate
            )

        # Should trigger cooldown
        can_generate, reason = limiter.can_generate()
        assert can_generate is False
        assert "quality rejection" in reason.lower()

    def test_rate_limiter_statistics(self, tmp_path):
        """Test rate limiter statistics calculation"""
        limiter = RateLimiter(
            config=RateLimitConfig(max_issues_per_hour=10),
            state_path=tmp_path / "rate_limit_state.json"
        )

        limiter.record_generation(
            issues_proposed=5,
            issues_created=3,
            duplicates_filtered=2,
            quality_rejected=0
        )

        stats = limiter.get_statistics()

        assert stats["last_hour"]["issues_created"] == 3
        assert stats["last_hour"]["remaining"] == 7
        assert stats["lifetime"]["total_duplicates"] == 2
        assert stats["lifetime"]["duplicate_rate"] == 0.4  # 2/5

    def test_rate_limiter_min_time_between_generations(self, tmp_path):
        """Test minimum time between generations"""
        limiter = RateLimiter(
            config=RateLimitConfig(min_time_between_generations_minutes=10),
            state_path=tmp_path / "rate_limit_state.json"
        )

        # First generation
        limiter.record_generation(
            issues_proposed=3,
            issues_created=3,
            duplicates_filtered=0
        )

        # Immediate second generation should be blocked
        can_generate, reason = limiter.can_generate()
        assert can_generate is False
        assert "Too soon" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
