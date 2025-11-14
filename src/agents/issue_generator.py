#!/usr/bin/env python3
"""
Issue Generator Agent - Core Logic

Ensures minimum number of open issues by generating new ones with Claude AI using Agent SDK
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add src directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "claude-agent"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import model configuration
from models_config import CLAUDE_MODELS, SystemPrompts
from utils.retry import retry_anthropic_api, retry_github_api
from utils.deduplication import IssueDuplicateChecker
from utils.outcome_tracker import OutcomeTracker
from utils.feedback_analyzer import FeedbackAnalyzer
from utils.rate_limiter import RateLimiter, RateLimitConfig
from utils.exceptions import (
    AgentResponseError,
    JSONParseError,
    MissingEnvironmentVariableError,
    GitHubAPIError,
    AnthropicAPIError,
    get_exception_for_github_error,
    get_exception_for_anthropic_error,
)
from logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Import Claude CLI Agent or fallback to Anthropic SDK
try:
    from claude_cli_agent import ClaudeAgent

    USE_CLAUDE_CLI = True
except ImportError:
    USE_CLAUDE_CLI = False
    try:
        from anthropic import Anthropic
    except ImportError:
        logger.error("Neither claude_cli_agent nor anthropic SDK available")
        raise


class IssueGenerator:
    """Generates GitHub issues using AI based on repository context"""

    def __init__(
        self, repo, anthropic_api_key: Optional[str] = None, min_issues: int = 3, dry_mode: bool = False
    ):
        """
        Initialize the Issue Generator

        Args:
            repo: PyGithub Repository object
            anthropic_api_key: Anthropic API key (required if not using Claude CLI)
            min_issues: Minimum number of open issues to maintain
            dry_mode: If True, skip actual issue creation (for CI validation)
        """
        self.repo = repo
        self.anthropic_api_key = anthropic_api_key
        self.min_issues = min_issues
        self.dry_mode = dry_mode

        logger.info(f"Initialized IssueGenerator for repo {repo.full_name}", extra={
            "min_issues": min_issues,
            "dry_mode": dry_mode,
            "use_claude_cli": USE_CLAUDE_CLI
        })

        # Initialize duplicate checker with enhanced features
        self.duplicate_checker = IssueDuplicateChecker(
            title_similarity_threshold=0.75,
            body_similarity_threshold=0.60,
            combined_similarity_threshold=0.65,
            semantic_similarity_threshold=0.85,
            min_quality_score=0.5,
            anthropic_api_key=anthropic_api_key,
            enable_semantic_dedup=True,
            enable_quality_gates=True,
        )

        # Initialize feedback loop components
        self.outcome_tracker = OutcomeTracker()
        self.feedback_analyzer = FeedbackAnalyzer(self.outcome_tracker)

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            config=RateLimitConfig(
                max_issues_per_hour=10,
                max_issues_per_day=50,
                max_duplicate_rate=0.7,
                max_quality_reject_rate=0.5,
                cooldown_minutes=60,
                min_time_between_generations_minutes=5
            )
        )

    def check_and_generate(self) -> bool:
        """
        Check issue count and generate if needed (with rate limiting)

        Returns:
            bool: True if issues were generated, False otherwise
        """
        logger.info(f"Checking issue count (minimum: {self.min_issues})")

        # Check rate limiter first
        can_generate, reason = self.rate_limiter.can_generate()
        if not can_generate:
            logger.info(f"Rate limit check failed: {reason}")
            # Log statistics
            stats = self.rate_limiter.get_statistics()
            logger.info("Rate limit stats", extra=stats)
            return False

        # Count open issues (excluding pull requests) with retry
        @retry_github_api
        def get_open_issues():
            return list(self.repo.get_issues(state="open"))

        try:
            open_issues = get_open_issues()
        except Exception as e:
            raise get_exception_for_github_error(e, "Failed to fetch open issues")

        open_issues = [i for i in open_issues if not i.pull_request]
        issue_count = len(open_issues)

        logger.info(f"Current open issues: {issue_count}")

        if issue_count >= self.min_issues:
            logger.info(f"Sufficient issues exist ({issue_count} >= {self.min_issues})")
            return False

        # Need to generate issues
        needed = self.min_issues - issue_count
        logger.info(f"Generating {needed} new issue(s)...")

        self._generate_issues(needed, open_issues)
        return True

    def _generate_issues(self, needed: int, open_issues: List) -> None:
        """
        Generate issues using Claude AI

        Args:
            needed: Number of issues to generate
            open_issues: List of current open issues
        """
        # Get repository context with retry
        logger.info("Analyzing repository for potential issues...")

        @retry_github_api
        def get_readme():
            try:
                return self.repo.get_readme().decoded_content.decode("utf-8")[:1000]
            except Exception as e:
                logger.warning(f"Failed to fetch README: {e}")
                return "No README found"

        @retry_github_api
        def get_commits():
            return list(self.repo.get_commits()[:5])

        try:
            readme = get_readme()
            recent_commits = get_commits()
        except Exception as e:
            raise get_exception_for_github_error(e, "Failed to fetch repository context")

        commit_messages = "\n".join(
            [f"- {c.commit.message.split(chr(10))[0]}" for c in recent_commits]
        )

        # Get feedback-based generation guidance
        logger.info("Analyzing feedback data for adaptive generation...")
        guidance = self.feedback_analyzer.get_generation_guidance()
        overall_stats = self.outcome_tracker.get_overall_stats()

        if overall_stats['total_attempts'] > 0:
            logger.info(f"Historical success rate: {overall_stats['success_rate']:.1%}", extra={
                "success_rate": overall_stats['success_rate'],
                "focus_message": guidance.focus_message
            })
            if guidance.high_priority_types:
                logger.info(f"Prioritizing: {', '.join(guidance.high_priority_types)}")
            if guidance.low_priority_types:
                logger.info(f"De-emphasizing: {', '.join(guidance.low_priority_types)}")
        else:
            logger.info("No historical data yet - using default generation")

        # Build prompt for Claude with adaptive guidance
        prompt = self._build_prompt(needed, readme, commit_messages, open_issues, guidance)

        logger.debug(f"Prompt length: {len(prompt)} chars")

        # Call Claude AI
        response_text = self._call_claude(prompt)

        if not response_text:
            raise AgentResponseError("Failed to get response from Claude")

        # Parse and create issues (with deduplication)
        self._parse_and_create_issues(response_text, needed, open_issues)

    def _build_prompt(
        self, needed: int, readme: str, commit_messages: str, open_issues: List, guidance = None
    ) -> str:
        """Build the prompt for Claude with adaptive guidance"""
        base_prompt = f"""Analyze this GitHub repository and suggest {needed} new issue(s).

Repository: {self.repo.full_name}

README excerpt:
{readme}

Recent commits:
{commit_messages}

Current open issues:
{chr(10).join([f"- #{i.number}: {i.title}" for i in open_issues[:10]])}

Generate {needed} realistic, actionable issue(s).
Read the whole project and find the most important thing for it - from new features, UI, apps, marketing or sales tools to bug fixes, tests, devops etc."""

        # Add adaptive guidance if available
        if guidance and guidance.prompt_adjustments and guidance.high_priority_types:
            base_prompt += f"""

{guidance.prompt_adjustments}"""

        base_prompt += """

Respond with ONLY a JSON object in this exact format:
{{
  "issues": [
    {{
      "title": "Brief title (max 80 chars)",
      "body": "Description (max 300 chars)",
      "labels": ["feature"]
    }}
  ]
}}

Use appropriate labels: feature, bug, documentation, refactor, test, performance, security, ci/cd

Keep descriptions brief and output ONLY the JSON, nothing else."""

        return base_prompt

    def _call_claude(self, prompt: str) -> Optional[str]:
        """Call Claude AI (CLI or API)"""
        try:
            if USE_CLAUDE_CLI:
                logger.info("Using Claude CLI for issue generation")
                agent = ClaudeAgent(output_format="text", verbose=True)

                result = agent.query(
                    prompt, system_prompt=SystemPrompts.ISSUE_GENERATOR
                )

                # Extract response
                if isinstance(result, dict) and "result" in result:
                    return result["result"]
                else:
                    return str(result)
            else:
                logger.info("Using Anthropic API for issue generation")

                @retry_anthropic_api
                def call_anthropic():
                    client = Anthropic(api_key=self.anthropic_api_key)
                    return client.messages.create(
                        model=CLAUDE_MODELS.ISSUE_GENERATION,
                        max_tokens=CLAUDE_MODELS.DEFAULT_MAX_TOKENS,
                        system=SystemPrompts.ISSUE_GENERATOR,
                        messages=[{"role": "user", "content": prompt}],
                    )

                message = call_anthropic()
                return message.content[0].text

        except Exception as e:
            logger.exception("Error calling Claude API")
            raise get_exception_for_anthropic_error(e, "Failed to call Claude API")

    def _parse_and_create_issues(self, response_text: str, needed: int, open_issues: List) -> None:
        """Parse Claude response and create GitHub issues after deduplication check"""
        try:
            logger.info("Parsing Claude response...")

            # Clean up response - remove markdown code blocks if present
            cleaned_response = response_text.strip()
            if "```json" in cleaned_response:
                cleaned_response = (
                    cleaned_response.split("```json")[1].split("```")[0].strip()
                )
                logger.debug("Removed ```json``` markers")
            elif "```" in cleaned_response:
                cleaned_response = (
                    cleaned_response.split("```")[1].split("```")[0].strip()
                )
                logger.debug("Removed ``` markers")

            # Find JSON object in response
            start_idx = cleaned_response.find("{")
            end_idx = cleaned_response.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise JSONParseError(response_text, "No JSON object found in response")

            json_str = cleaned_response[start_idx:end_idx]
            logger.debug(f"Extracted JSON: {len(json_str)} chars")

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise JSONParseError(json_str, str(e))

            issues_to_create = data.get("issues", [])[:needed]

            if not issues_to_create:
                logger.warning("No issues generated by Claude")
                return

            # Perform deduplication check
            logger.info(f"Checking {len(issues_to_create)} proposed issue(s) for duplicates...")
            unique_issues, duplicates = self.duplicate_checker.check_issue_list(
                issues_to_create, open_issues, verbose=True
            )

            # Report deduplication results
            if duplicates:
                logger.info(f"Filtered out {len(duplicates)} duplicate issue(s)")
                for dup_issue, existing, scores in duplicates:
                    logger.debug(
                        f"Duplicate detected: '{dup_issue['title'][:50]}' similar to #{existing.number}",
                        extra={"similarity_score": scores['combined_similarity']}
                    )

            if not unique_issues:
                logger.warning("All proposed issues were duplicates - no new issues created")
                return

            logger.info(f"{len(unique_issues)} unique issue(s) to create")

            # Create issues with retry
            created_count = 0
            for issue_data in unique_issues:
                title = issue_data.get("title", "Untitled Issue")[
                    :80
                ]  # Limit title length
                body = issue_data.get("body", "")
                labels = issue_data.get("labels", [])

                full_body = f"{body}\n\n---\n*Generated by Issue Generator Agent*"

                if self.dry_mode:
                    logger.info(f"DRY MODE: Would create issue: {title}", extra={"labels": labels})
                    created_count += 1
                else:
                    @retry_github_api
                    def create_issue():
                        return self.repo.create_issue(
                            title=title, body=full_body, labels=labels
                        )

                    try:
                        new_issue = create_issue()
                        created_count += 1
                        logger.info(f"Created issue #{new_issue.number}: {title}")
                    except Exception as e:
                        logger.error(f"Failed to create issue '{title}': {e}")
                        raise get_exception_for_github_error(e, f"Failed to create issue '{title}'")

            # Calculate quality rejections (proposed - created - duplicates)
            quality_rejected = len(issues_to_create) - created_count - len(duplicates)

            # Report final statistics
            logger.info("Deduplication Summary", extra={
                "proposed": len(issues_to_create),
                "duplicates_filtered": len(duplicates),
                "quality_rejected": quality_rejected,
                "created": created_count,
                "spam_reduction_pct": (len(duplicates) / len(issues_to_create) * 100) if len(issues_to_create) > 0 else 0
            })

            # Record in rate limiter
            if not self.dry_mode:
                self.rate_limiter.record_generation(
                    issues_proposed=len(issues_to_create),
                    issues_created=created_count,
                    duplicates_filtered=len(duplicates),
                    quality_rejected=quality_rejected
                )

            if self.dry_mode:
                logger.info(f"DRY MODE: Would have generated {created_count} unique issue(s)")
            else:
                logger.info(f"Successfully generated {created_count} issue(s)")

        except JSONParseError:
            logger.error("Failed to parse Claude response as JSON", extra={
                "response_preview": response_text[:1000],
                "response_end": response_text[-500:]
            })
            raise
        except Exception as e:
            logger.exception("Error creating issues")
            raise
