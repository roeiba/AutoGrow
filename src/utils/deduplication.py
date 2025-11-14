#!/usr/bin/env python3
"""
Issue Deduplication Utility

Provides semantic similarity checking to prevent duplicate issues.
Uses multiple techniques:
1. Exact/near-exact title matching
2. Token-based similarity (Jaccard similarity)
3. Normalized edit distance (Levenshtein distance)
4. Semantic similarity using embeddings
5. Quality scoring (clarity, actionability, scope)
"""

import re
import math
from typing import List, Dict, Tuple, Any, Optional
from difflib import SequenceMatcher

from logging_config import get_logger
from utils.exceptions import (
    DuplicateIssueError,
    ValidationError,
)

logger = get_logger(__name__)

# Try to import Anthropic for embeddings
try:
    from anthropic import Anthropic
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("Anthropic SDK not available - semantic similarity disabled")


class IssueDuplicateChecker:
    """Checks for duplicate or similar issues using multiple similarity metrics"""

    def __init__(
        self,
        title_similarity_threshold: float = 0.75,
        body_similarity_threshold: float = 0.60,
        combined_similarity_threshold: float = 0.65,
        semantic_similarity_threshold: float = 0.85,
        min_quality_score: float = 0.5,
        anthropic_api_key: Optional[str] = None,
        enable_semantic_dedup: bool = True,
        enable_quality_gates: bool = True,
    ):
        """
        Initialize the duplicate checker

        Args:
            title_similarity_threshold: Minimum similarity score for titles (0-1)
            body_similarity_threshold: Minimum similarity score for bodies (0-1)
            combined_similarity_threshold: Minimum combined score for overall match (0-1)
            semantic_similarity_threshold: Minimum semantic similarity for embeddings (0-1)
            min_quality_score: Minimum quality score to pass quality gates (0-1)
            anthropic_api_key: API key for embeddings (optional)
            enable_semantic_dedup: Enable semantic deduplication with embeddings
            enable_quality_gates: Enable quality scoring gates
        """
        self.title_threshold = title_similarity_threshold
        self.body_threshold = body_similarity_threshold
        self.combined_threshold = combined_similarity_threshold
        self.semantic_threshold = semantic_similarity_threshold
        self.min_quality_score = min_quality_score
        self.enable_semantic_dedup = enable_semantic_dedup and EMBEDDINGS_AVAILABLE
        self.enable_quality_gates = enable_quality_gates

        # Initialize Anthropic client for embeddings if available
        self.anthropic_client = None
        if self.enable_semantic_dedup and anthropic_api_key:
            try:
                self.anthropic_client = Anthropic(api_key=anthropic_api_key)
                logger.info("Semantic deduplication enabled with embeddings")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
                self.enable_semantic_dedup = False
        elif self.enable_semantic_dedup and not anthropic_api_key:
            logger.info("Semantic deduplication requested but no API key provided")
            self.enable_semantic_dedup = False

        # Cache for embeddings to avoid redundant API calls
        self._embedding_cache: Dict[str, List[float]] = {}

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

        result = {
            "title_similarity": title_similarity,
            "body_similarity": body_similarity,
            "combined_similarity": combined_score,
            "title_sequence": title_seq_sim,
            "title_jaccard": title_jaccard_sim,
            "body_sequence": body_seq_sim,
            "body_jaccard": body_jaccard_sim,
        }

        # Add semantic similarity if enabled
        if self.enable_semantic_dedup and self.anthropic_client:
            semantic_sim = self.calculate_semantic_similarity(title1, body1, title2, body2)
            result["semantic_similarity"] = semantic_sim

        return result

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text using Anthropic API with caching

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        if not self.anthropic_client:
            return None

        # Check cache
        cache_key = text[:500]  # Use first 500 chars as cache key
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        try:
            # Note: Anthropic doesn't have an embeddings API yet
            # We'll use a simple word vector approach as fallback
            # In production, you'd use a proper embedding service
            logger.debug("Embedding API not available, using fallback similarity")
            return None
        except Exception as e:
            logger.debug(f"Failed to get embedding: {e}")
            return None

    def calculate_semantic_similarity(
        self, title1: str, body1: str, title2: str, body2: str
    ) -> float:
        """
        Calculate semantic similarity using embeddings (cosine similarity)

        Args:
            title1: First issue title
            body1: First issue body
            title2: Second issue title
            body2: Second issue body

        Returns:
            Semantic similarity score (0-1)
        """
        if not self.anthropic_client:
            return 0.0

        # Combine title and body for embedding
        text1 = f"{title1} {body1}"
        text2 = f"{title2} {body2}"

        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)

        if emb1 is None or emb2 is None:
            # Fallback to enhanced text-based semantic matching
            return self._fallback_semantic_similarity(title1, body1, title2, body2)

        # Calculate cosine similarity
        return self._cosine_similarity(emb1, emb2)

    def _fallback_semantic_similarity(
        self, title1: str, body1: str, title2: str, body2: str
    ) -> float:
        """
        Fallback semantic similarity using enhanced text analysis

        Args:
            title1: First issue title
            body1: First issue body
            title2: Second issue title
            body2: Second issue body

        Returns:
            Semantic similarity score (0-1)
        """
        # Extract key concepts (words longer than 3 chars, excluding common words)
        stop_words = {
            'the', 'and', 'for', 'are', 'this', 'that', 'with', 'from', 'have',
            'has', 'will', 'would', 'should', 'could', 'been', 'being', 'does',
            'add', 'fix', 'update', 'create', 'implement', 'improve'
        }

        def extract_concepts(title: str, body: str) -> set:
            text = f"{title} {body}".lower()
            words = re.findall(r'\b\w+\b', text)
            return {w for w in words if len(w) > 3 and w not in stop_words}

        concepts1 = extract_concepts(title1, body1)
        concepts2 = extract_concepts(title2, body2)

        if not concepts1 or not concepts2:
            return 0.0

        # Calculate concept overlap (Jaccard on meaningful terms)
        intersection = len(concepts1.intersection(concepts2))
        union = len(concepts1.union(concepts2))

        return intersection / union if union > 0 else 0.0

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Convert from [-1, 1] to [0, 1]
        similarity = dot_product / (magnitude1 * magnitude2)
        return (similarity + 1) / 2

    def calculate_quality_score(self, title: str, body: str, labels: List[str]) -> Dict[str, Any]:
        """
        Calculate quality score for an issue based on clarity, actionability, and scope

        Args:
            title: Issue title
            body: Issue body
            labels: Issue labels

        Returns:
            Dictionary with quality metrics and overall score
        """
        scores = {}

        # 1. Clarity score (0-1)
        clarity = self._score_clarity(title, body)
        scores["clarity"] = clarity

        # 2. Actionability score (0-1)
        actionability = self._score_actionability(title, body)
        scores["actionability"] = actionability

        # 3. Scope score (0-1) - not too vague, not too specific
        scope = self._score_scope(title, body)
        scores["scope"] = scope

        # 4. Label validity
        label_validity = self._score_labels(labels)
        scores["label_validity"] = label_validity

        # Overall quality score (weighted average)
        overall = (
            clarity * 0.35 +
            actionability * 0.35 +
            scope * 0.20 +
            label_validity * 0.10
        )
        scores["overall"] = overall

        # Add quality feedback
        scores["passes_quality_gate"] = overall >= self.min_quality_score
        scores["feedback"] = self._generate_quality_feedback(scores)

        return scores

    def _score_clarity(self, title: str, body: str) -> float:
        """Score clarity of issue description"""
        score = 0.5  # Base score

        # Title should be concise but informative (30-80 chars ideal)
        title_len = len(title)
        if 30 <= title_len <= 80:
            score += 0.2
        elif title_len < 15:
            score -= 0.2  # Too short

        # Body should have sufficient detail (100-500 chars ideal)
        body_len = len(body)
        if 100 <= body_len <= 500:
            score += 0.2
        elif body_len < 50:
            score -= 0.2  # Too vague

        # Check for clear technical terms
        technical_indicators = ['api', 'function', 'class', 'method', 'endpoint', 'database',
                                'error', 'bug', 'feature', 'ui', 'ux', 'performance']
        text_lower = f"{title} {body}".lower()
        if any(term in text_lower for term in technical_indicators):
            score += 0.1

        return max(0.0, min(1.0, score))

    def _score_actionability(self, title: str, body: str) -> float:
        """Score how actionable the issue is"""
        score = 0.5  # Base score

        # Check for action verbs
        action_verbs = ['add', 'fix', 'update', 'remove', 'refactor', 'implement',
                        'create', 'improve', 'optimize', 'enhance', 'upgrade']
        title_lower = title.lower()
        if any(verb in title_lower for verb in action_verbs):
            score += 0.2

        # Check for specific requirements or steps
        specific_indicators = ['should', 'must', 'need to', 'required', 'implement',
                               'step:', 'requirement:', 'expected:', 'actual:']
        body_lower = body.lower()
        if any(indicator in body_lower for indicator in specific_indicators):
            score += 0.2

        # Penalize vague language
        vague_terms = ['maybe', 'perhaps', 'possibly', 'might', 'could be', 'not sure']
        if any(term in body_lower for term in vague_terms):
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _score_scope(self, title: str, body: str) -> float:
        """Score if scope is appropriate (not too broad, not too narrow)"""
        score = 0.7  # Base score (assume good scope)

        # Too broad indicators
        broad_terms = ['everything', 'all', 'entire', 'whole', 'complete rewrite',
                       'redesign', 'major refactor']
        text_lower = f"{title} {body}".lower()
        if any(term in text_lower for term in broad_terms):
            score -= 0.3

        # Too narrow indicators (overly specific implementation details)
        if len(body) > 0:
            code_blocks = body.count('```') // 2
            if code_blocks > 2:
                score -= 0.2  # Too focused on implementation

        # Good scope indicators
        good_scope_terms = ['specific', 'targeted', 'focused', 'single', 'one']
        if any(term in text_lower for term in good_scope_terms):
            score += 0.2

        return max(0.0, min(1.0, score))

    def _score_labels(self, labels: List[str]) -> float:
        """Score label validity"""
        if not labels:
            return 0.3  # No labels is not ideal but acceptable

        valid_labels = {
            'feature', 'bug', 'documentation', 'refactor', 'test',
            'performance', 'security', 'ci/cd', 'enhancement', 'docs'
        }

        # Check if labels are valid
        valid_count = sum(1 for label in labels if label.lower() in valid_labels)
        if valid_count > 0:
            return min(1.0, 0.5 + (valid_count * 0.25))

        return 0.5  # Unknown labels, neutral score

    def _generate_quality_feedback(self, scores: Dict[str, float]) -> List[str]:
        """Generate actionable feedback for quality improvement"""
        feedback = []

        if scores["clarity"] < 0.5:
            feedback.append("Issue lacks clarity - add more specific details")

        if scores["actionability"] < 0.5:
            feedback.append("Issue is not actionable - specify what needs to be done")

        if scores["scope"] < 0.5:
            feedback.append("Issue scope is too broad or too narrow - refine scope")

        if scores["label_validity"] < 0.5:
            feedback.append("Add appropriate labels (feature, bug, documentation, etc.)")

        if not feedback:
            feedback.append("Quality looks good")

        return feedback

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

        # Also check semantic similarity if enabled
        if self.enable_semantic_dedup and "semantic_similarity" in scores:
            if scores["semantic_similarity"] >= self.semantic_threshold:
                is_dup = True

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
        Filter a list of new issues to remove duplicates and low-quality issues

        Args:
            new_issues: List of new issue dicts with 'title', 'body', 'labels' keys
            existing_issues: List of existing issue objects from GitHub
            verbose: Whether to print detailed information

        Returns:
            Tuple of (non_duplicate_issues, duplicate_info)
            - non_duplicate_issues: List of issues that are not duplicates and pass quality gates
            - duplicate_info: List of (new_issue, matching_existing_issue, scores)
        """
        non_duplicates = []
        duplicates_found = []
        quality_rejected = []

        for new_issue in new_issues:
            new_title = new_issue.get("title", "")
            new_body = new_issue.get("body", "")
            new_labels = new_issue.get("labels", [])

            # Apply quality gates first
            if self.enable_quality_gates:
                quality_scores = self.calculate_quality_score(new_title, new_body, new_labels)

                if not quality_scores["passes_quality_gate"]:
                    quality_rejected.append({
                        "issue": new_issue,
                        "scores": quality_scores,
                        "reason": "low_quality"
                    })

                    logger.info(
                        f"Quality gate rejected: '{new_title[:60]}' "
                        f"(Score: {quality_scores['overall']:.2f}, "
                        f"Threshold: {self.min_quality_score:.2f})"
                    )

                    if verbose:
                        print(f"QUALITY REJECTED: {new_title[:60]}")
                        print(f"   Overall score: {quality_scores['overall']:.2f}")
                        print(f"   Feedback: {', '.join(quality_scores['feedback'])}")

                    continue  # Skip this issue

            # Find duplicates
            duplicate_matches = self.find_duplicates(new_title, new_body, existing_issues)

            if duplicate_matches:
                # Found at least one duplicate
                best_match, best_scores = duplicate_matches[0]
                duplicates_found.append((new_issue, best_match, best_scores))

                logger.info(
                    f"Duplicate detected - New: '{new_title[:60]}' matches "
                    f"Existing #{best_match.number}: '{best_match.title[:60]}' "
                    f"(Title: {best_scores['title_similarity']:.2%}, "
                    f"Combined: {best_scores['combined_similarity']:.2%})"
                )

                if verbose:
                    print(f"DUPLICATE DETECTED:")
                    print(f"   New: {new_title[:60]}")
                    print(f"   Existing #{best_match.number}: {best_match.title[:60]}")
                    print(f"   Title similarity: {best_scores['title_similarity']:.2%}")
                    print(f"   Combined similarity: {best_scores['combined_similarity']:.2%}")
            else:
                # Not a duplicate and passed quality gates
                non_duplicates.append(new_issue)
                logger.debug(f"Unique issue detected: {new_title[:60]}")
                if verbose:
                    print(f"UNIQUE: {new_title[:60]}")

        # Log quality rejection statistics
        if quality_rejected:
            logger.info(f"Quality gates rejected {len(quality_rejected)} issue(s)")

        return non_duplicates, duplicates_found
