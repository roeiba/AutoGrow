#!/usr/bin/env python3
"""
Issue Deduplication Utility

Provides semantic similarity checking to prevent duplicate issues.
Uses multiple techniques:
1. Exact/near-exact title matching
2. Token-based similarity (Jaccard similarity)
3. Normalized edit distance (Levenshtein distance)
"""

import re
from typing import List, Dict, Tuple, Any
from difflib import SequenceMatcher


class IssueDuplicateChecker:
    """Checks for duplicate or similar issues using multiple similarity metrics"""

    def __init__(
        self,
        title_similarity_threshold: float = 0.75,
        body_similarity_threshold: float = 0.60,
        combined_similarity_threshold: float = 0.65,
    ):
        """
        Initialize the duplicate checker

        Args:
            title_similarity_threshold: Minimum similarity score for titles (0-1)
            body_similarity_threshold: Minimum similarity score for bodies (0-1)
            combined_similarity_threshold: Minimum combined score for overall match (0-1)
        """
        self.title_threshold = title_similarity_threshold
        self.body_threshold = body_similarity_threshold
        self.combined_threshold = combined_similarity_threshold

    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison by lowercasing and removing extra whitespace

        Args:
            text: Input text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)

        # Collapse multiple spaces into one
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def calculate_sequence_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity using SequenceMatcher (based on Ratcliff/Obershelp algorithm)

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0

        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)

        return SequenceMatcher(None, norm1, norm2).ratio()

    def calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate Jaccard similarity based on word tokens

        Args:
            text1: First text
            text2: Second text

        Returns:
            Jaccard similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0

        # Tokenize into words
        words1 = set(self.normalize_text(text1).split())
        words2 = set(self.normalize_text(text2).split())

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def calculate_combined_similarity(
        self, title1: str, body1: str, title2: str, body2: str
    ) -> Dict[str, float]:
        """
        Calculate combined similarity scores using multiple methods

        Args:
            title1: First issue title
            body1: First issue body
            title2: Second issue title
            body2: Second issue body

        Returns:
            Dictionary with similarity scores and combined score
        """
        # Calculate title similarities
        title_seq_sim = self.calculate_sequence_similarity(title1, title2)
        title_jaccard_sim = self.calculate_jaccard_similarity(title1, title2)
        title_similarity = max(title_seq_sim, title_jaccard_sim)

        # Calculate body similarities
        body_seq_sim = self.calculate_sequence_similarity(body1, body2)
        body_jaccard_sim = self.calculate_jaccard_similarity(body1, body2)
        body_similarity = max(body_seq_sim, body_jaccard_sim)

        # Calculate combined score (weighted: title is more important)
        combined_score = (title_similarity * 0.7) + (body_similarity * 0.3)

        return {
            "title_similarity": title_similarity,
            "body_similarity": body_similarity,
            "combined_similarity": combined_score,
            "title_sequence": title_seq_sim,
            "title_jaccard": title_jaccard_sim,
            "body_sequence": body_seq_sim,
            "body_jaccard": body_jaccard_sim,
        }

    def is_duplicate(
        self,
        new_title: str,
        new_body: str,
        existing_title: str,
        existing_body: str,
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Check if a new issue is a duplicate of an existing one

        Args:
            new_title: Title of new issue
            new_body: Body of new issue
            existing_title: Title of existing issue
            existing_body: Body of existing issue

        Returns:
            Tuple of (is_duplicate: bool, similarity_scores: dict)
        """
        scores = self.calculate_combined_similarity(
            new_title, new_body, existing_title, existing_body
        )

        # Check if it's a duplicate based on thresholds
        is_dup = (
            scores["title_similarity"] >= self.title_threshold
            or scores["combined_similarity"] >= self.combined_threshold
        )

        return is_dup, scores

    def find_duplicates(
        self,
        new_title: str,
        new_body: str,
        existing_issues: List[Any],
    ) -> List[Tuple[Any, Dict[str, float]]]:
        """
        Find all duplicate issues from a list of existing issues

        Args:
            new_title: Title of new issue to check
            new_body: Body of new issue to check
            existing_issues: List of existing issue objects (must have .title and .body)

        Returns:
            List of tuples (issue, similarity_scores) for all duplicates found
        """
        duplicates = []

        for existing_issue in existing_issues:
            existing_title = getattr(existing_issue, 'title', '')
            existing_body = getattr(existing_issue, 'body', '') or ''

            is_dup, scores = self.is_duplicate(
                new_title, new_body, existing_title, existing_body
            )

            if is_dup:
                duplicates.append((existing_issue, scores))

        # Sort by combined similarity (highest first)
        duplicates.sort(key=lambda x: x[1]["combined_similarity"], reverse=True)

        return duplicates

    def check_issue_list(
        self,
        new_issues: List[Dict[str, str]],
        existing_issues: List[Any],
        verbose: bool = False,
    ) -> Tuple[List[Dict[str, str]], List[Tuple[Dict[str, str], Any, Dict[str, float]]]]:
        """
        Filter a list of new issues to remove duplicates

        Args:
            new_issues: List of new issue dicts with 'title', 'body', 'labels' keys
            existing_issues: List of existing issue objects from GitHub
            verbose: Whether to print detailed information

        Returns:
            Tuple of (non_duplicate_issues, duplicate_info)
            - non_duplicate_issues: List of issues that are not duplicates
            - duplicate_info: List of (new_issue, matching_existing_issue, scores)
        """
        non_duplicates = []
        duplicates_found = []

        for new_issue in new_issues:
            new_title = new_issue.get("title", "")
            new_body = new_issue.get("body", "")

            # Find duplicates
            duplicate_matches = self.find_duplicates(new_title, new_body, existing_issues)

            if duplicate_matches:
                # Found at least one duplicate
                best_match, best_scores = duplicate_matches[0]
                duplicates_found.append((new_issue, best_match, best_scores))

                if verbose:
                    print(f"🚫 DUPLICATE DETECTED:")
                    print(f"   New: {new_title[:60]}")
                    print(f"   Existing #{best_match.number}: {best_match.title[:60]}")
                    print(f"   Title similarity: {best_scores['title_similarity']:.2%}")
                    print(f"   Combined similarity: {best_scores['combined_similarity']:.2%}")
            else:
                # Not a duplicate
                non_duplicates.append(new_issue)
                if verbose:
                    print(f"✅ UNIQUE: {new_title[:60]}")

        return non_duplicates, duplicates_found
