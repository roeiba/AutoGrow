#!/usr/bin/env python3
"""
Base Issue Agent - Abstract base class for specialized issue generators

Provides common functionality for all domain-specific agents (Marketing, Product, Sales, etc.)
"""

import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Add src directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "claude-agent"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import model configuration
from models_config import CLAUDE_MODELS, SystemPrompts
from utils.deduplication import IssueDuplicateChecker
from utils.outcome_tracker import OutcomeTracker
from utils.feedback_analyzer import FeedbackAnalyzer
from utils.rate_limiter import RateLimiter, RateLimitConfig
from utils.project_brief_validator import get_project_brief
from utils.github_helpers import get_readme, get_recent_commits, get_open_issues, create_issue
from utils.anthropic_helpers import call_anthropic_api
from utils.exceptions import (
    AgentResponseError,
    JSONParseError,
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


@dataclass
class AgentConfig:
    """Configuration for a specialized agent"""
    domain: str  # e.g., "marketing", "product", "sales"
    default_labels: List[str]  # Default labels for this agent's issues
    min_issues: int = 2  # Minimum issues to maintain
    focus_areas: List[str] = None  # Specific focus areas for this domain
    priority_keywords: List[str] = None  # Keywords that indicate high priority


class BaseIssueAgent(ABC):
    """
    Abstract base class for specialized issue generation agents
    
    Subclasses must implement:
    - get_agent_config(): Return AgentConfig with domain-specific settings
    - build_domain_prompt(): Build domain-specific prompt additions
    """

    def __init__(
        self, 
        repo, 
        anthropic_api_key: Optional[str] = None, 
        dry_mode: bool = False,
        custom_config: Optional[AgentConfig] = None
    ):
        """
        Initialize the Base Issue Agent

        Args:
            repo: PyGithub Repository object
            anthropic_api_key: Anthropic API key (required if not using Claude CLI)
            dry_mode: If True, skip actual issue creation (for CI validation)
            custom_config: Optional custom configuration (overrides get_agent_config)
        """
        self.repo = repo
        self.anthropic_api_key = anthropic_api_key
        self.dry_mode = dry_mode
        
        # Get agent configuration
        self.config = custom_config or self.get_agent_config()
        
        logger.info(
            f"Initialized {self.__class__.__name__} for repo {repo.full_name}", 
            extra={
                "domain": self.config.domain,
                "min_issues": self.config.min_issues,
                "dry_mode": dry_mode,
                "use_claude_cli": USE_CLAUDE_CLI
            }
        )

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

        # Initialize rate limiter with domain-specific prefix
        self.rate_limiter = RateLimiter(
            config=RateLimitConfig(
                max_issues_per_hour=8,
                max_issues_per_day=30,
                max_duplicate_rate=0.7,
                max_quality_reject_rate=0.5,
                cooldown_minutes=60,
                min_time_between_generations_minutes=10
            )
        )

    @abstractmethod
    def get_agent_config(self) -> AgentConfig:
        """
        Return the configuration for this agent
        
        Returns:
            AgentConfig: Configuration with domain, labels, and settings
        """
        pass

    @abstractmethod
    def build_domain_prompt(self, context: Dict) -> str:
        """
        Build domain-specific prompt additions
        
        Args:
            context: Dictionary with repository context (readme, commits, etc.)
            
        Returns:
            str: Domain-specific prompt text to add to base prompt
        """
        pass

    def check_and_generate(self) -> bool:
        """
        Check issue count for this domain and generate if needed
        
        Returns:
            bool: True if issues were generated, False otherwise
        """
        logger.info(
            f"[{self.config.domain.upper()}] Checking issue count (minimum: {self.config.min_issues})"
        )

        # Check rate limiter first
        can_generate, reason = self.rate_limiter.can_generate()
        if not can_generate:
            logger.info(f"[{self.config.domain.upper()}] Rate limit check failed: {reason}")
            stats = self.rate_limiter.get_statistics()
            logger.info(f"[{self.config.domain.upper()}] Rate limit stats", extra=stats)
            return False

        # Count open issues with domain labels
        try:
            all_open_issues = get_open_issues(self.repo, exclude_pull_requests=True)
            domain_issues = self._filter_domain_issues(all_open_issues)
        except Exception as e:
            raise get_exception_for_github_error(e, "Failed to fetch open issues")

        issue_count = len(domain_issues)
        logger.info(
            f"[{self.config.domain.upper()}] Current domain issues: {issue_count} "
            f"(total open: {len(all_open_issues)})"
        )

        if issue_count >= self.config.min_issues:
            logger.info(
                f"[{self.config.domain.upper()}] Sufficient issues exist "
                f"({issue_count} >= {self.config.min_issues})"
            )
            return False

        # Need to generate issues
        needed = self.config.min_issues - issue_count
        logger.info(f"[{self.config.domain.upper()}] Generating {needed} new issue(s)...")

        self._generate_issues(needed, all_open_issues)
        return True

    def _filter_domain_issues(self, issues: List) -> List:
        """
        Filter issues that belong to this agent's domain
        
        Args:
            issues: List of all open issues
            
        Returns:
            List of issues matching this domain's labels
        """
        domain_issues = []
        for issue in issues:
            issue_labels = [label.name for label in issue.labels]
            # Check if any of the domain's default labels are present
            if any(label in issue_labels for label in self.config.default_labels):
                domain_issues.append(issue)
        return domain_issues

    def _generate_issues(self, needed: int, open_issues: List) -> None:
        """
        Generate issues using Claude AI with domain-specific context
        
        Args:
            needed: Number of issues to generate
            open_issues: List of current open issues
        """
        logger.info(f"[{self.config.domain.upper()}] Analyzing repository for potential issues...")

        try:
            readme = get_readme(self.repo, max_length=1000)
            recent_commits = get_recent_commits(self.repo, max_commits=5)
        except Exception as e:
            raise get_exception_for_github_error(e, "Failed to fetch repository context")

        commit_messages = "\n".join(
            [f"- {c.commit.message.split(chr(10))[0]}" for c in recent_commits]
        )

        # Load project brief
        project_brief = get_project_brief()
        if not project_brief:
            logger.warning("No PROJECT_BRIEF.md found")
        else:
            logger.info("Loaded PROJECT_BRIEF.md context")

        # Get feedback-based generation guidance
        logger.info(f"[{self.config.domain.upper()}] Analyzing feedback data...")
        guidance = self.feedback_analyzer.get_generation_guidance()
        overall_stats = self.outcome_tracker.get_overall_stats()

        if overall_stats['total_attempts'] > 0:
            logger.info(
                f"[{self.config.domain.upper()}] Historical success rate: "
                f"{overall_stats['success_rate']:.1%}",
                extra={
                    "success_rate": overall_stats['success_rate'],
                    "focus_message": guidance.focus_message
                }
            )

        # Build context for domain prompt
        context = {
            'readme': readme,
            'commits': commit_messages,
            'project_brief': project_brief,
            'open_issues': open_issues,
            'needed': needed
        }

        # Build prompt with domain-specific additions
        prompt = self._build_prompt(context, guidance)
        logger.debug(f"[{self.config.domain.upper()}] Prompt length: {len(prompt)} chars")

        # Call Claude AI
        response_text = self._call_claude(prompt)

        if not response_text:
            raise AgentResponseError("Failed to get response from Claude")

        # Parse and create issues
        self._parse_and_create_issues(response_text, needed, open_issues)

    def _build_prompt(self, context: Dict, guidance=None) -> str:
        """
        Build the complete prompt with base + domain-specific content
        
        Args:
            context: Repository context dictionary
            guidance: Feedback-based guidance
            
        Returns:
            str: Complete prompt for Claude
        """
        needed = context['needed']
        
        base_prompt = f"""You are a specialized {self.config.domain.upper()} agent analyzing this GitHub repository.

Repository: {self.repo.full_name}

README excerpt:
{context['readme']}

Recent commits:
{context['commits']}

Current open issues:
{chr(10).join([f"- #{i.number}: {i.title}" for i in context['open_issues'][:10]])}

Project Context:
{context['project_brief']}

"""
        # Add domain-specific prompt
        domain_prompt = self.build_domain_prompt(context)
        base_prompt += domain_prompt

        # Add adaptive guidance if available
        if guidance and guidance.prompt_adjustments and guidance.high_priority_types:
            base_prompt += f"""

{guidance.prompt_adjustments}"""

        # Add JSON format instructions
        base_prompt += f"""

Generate {needed} realistic, actionable {self.config.domain} issue(s).

Respond with ONLY a JSON object in this exact format:
{{
  "issues": [
    {{
      "title": "Brief title (max 80 chars)",
      "body": "Description (max 300 chars)",
      "labels": {json.dumps(self.config.default_labels)}
    }}
  ]
}}

Keep descriptions brief and output ONLY the JSON, nothing else."""

        return base_prompt

    def _call_claude(self, prompt: str) -> Optional[str]:
        """Call Claude AI (CLI or API)"""
        try:
            if USE_CLAUDE_CLI:
                logger.info(f"[{self.config.domain.upper()}] Using Claude CLI")
                agent = ClaudeAgent(output_format="text", verbose=True)

                result = agent.query(
                    prompt, system_prompt=SystemPrompts.ISSUE_GENERATOR
                )

                if isinstance(result, dict) and "result" in result:
                    return result["result"]
                else:
                    return str(result)
            else:
                logger.info(f"[{self.config.domain.upper()}] Using Anthropic API")
                return call_anthropic_api(
                    api_key=self.anthropic_api_key,
                    prompt=prompt,
                    model=CLAUDE_MODELS.ISSUE_GENERATION,
                    max_tokens=CLAUDE_MODELS.DEFAULT_MAX_TOKENS,
                    system_prompt=SystemPrompts.ISSUE_GENERATOR
                )

        except Exception as e:
            logger.exception(f"[{self.config.domain.upper()}] Error calling Claude API")
            raise get_exception_for_anthropic_error(e, "Failed to call Claude API")

    def _parse_and_create_issues(self, response_text: str, needed: int, open_issues: List) -> None:
        """Parse Claude response and create GitHub issues after deduplication check"""
        try:
            logger.info(f"[{self.config.domain.upper()}] Parsing Claude response...")

            # Clean up response - remove markdown code blocks if present
            cleaned_response = response_text.strip()
            if "```json" in cleaned_response:
                cleaned_response = (
                    cleaned_response.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in cleaned_response:
                cleaned_response = (
                    cleaned_response.split("```")[1].split("```")[0].strip()
                )

            # Find JSON object in response
            start_idx = cleaned_response.find("{")
            end_idx = cleaned_response.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise JSONParseError(response_text, "No JSON object found in response")

            json_str = cleaned_response[start_idx:end_idx]

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise JSONParseError(json_str, str(e))

            issues_to_create = data.get("issues", [])[:needed]

            if not issues_to_create:
                logger.warning(f"[{self.config.domain.upper()}] No issues generated by Claude")
                return

            # Ensure domain labels are present
            for issue in issues_to_create:
                if 'labels' not in issue or not issue['labels']:
                    issue['labels'] = self.config.default_labels.copy()
                else:
                    # Merge with default labels
                    issue['labels'] = list(set(issue['labels'] + self.config.default_labels))

            # Perform deduplication check
            logger.info(
                f"[{self.config.domain.upper()}] Checking {len(issues_to_create)} "
                f"proposed issue(s) for duplicates..."
            )
            unique_issues, duplicates = self.duplicate_checker.check_issue_list(
                issues_to_create, open_issues, verbose=True
            )

            # Report deduplication results
            if duplicates:
                logger.info(
                    f"[{self.config.domain.upper()}] Filtered out {len(duplicates)} duplicate(s)"
                )

            if not unique_issues:
                logger.warning(
                    f"[{self.config.domain.upper()}] All proposed issues were duplicates"
                )
                return

            logger.info(
                f"[{self.config.domain.upper()}] {len(unique_issues)} unique issue(s) to create"
            )

            # Create issues
            created_count = 0
            for issue_data in unique_issues:
                title = issue_data.get("title", "Untitled Issue")[:80]
                body = issue_data.get("body", "")
                labels = issue_data.get("labels", self.config.default_labels)

                full_body = (
                    f"{body}\n\n---\n"
                    f"*Generated by {self.__class__.__name__} ({self.config.domain.upper()})*"
                )

                if self.dry_mode:
                    logger.info(
                        f"[{self.config.domain.upper()}] DRY MODE: Would create issue: {title}",
                        extra={"labels": labels}
                    )
                    created_count += 1
                else:
                    try:
                        new_issue = create_issue(
                            self.repo, title=title, body=full_body, labels=labels
                        )
                        created_count += 1
                        logger.info(
                            f"[{self.config.domain.upper()}] Created issue #{new_issue.number}: {title}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[{self.config.domain.upper()}] Failed to create issue '{title}': {e}"
                        )
                        raise get_exception_for_github_error(
                            e, f"Failed to create issue '{title}'"
                        )

            # Calculate quality rejections
            quality_rejected = len(issues_to_create) - created_count - len(duplicates)

            # Report final statistics
            logger.info(
                f"[{self.config.domain.upper()}] Deduplication Summary",
                extra={
                    "proposed": len(issues_to_create),
                    "duplicates_filtered": len(duplicates),
                    "quality_rejected": quality_rejected,
                    "issues_created": created_count,
                }
            )

            # Record in rate limiter
            if not self.dry_mode:
                self.rate_limiter.record_generation(
                    issues_proposed=len(issues_to_create),
                    issues_created=created_count,
                    duplicates_filtered=len(duplicates),
                    quality_rejected=quality_rejected
                )

            if self.dry_mode:
                logger.info(
                    f"[{self.config.domain.upper()}] DRY MODE: Would have generated "
                    f"{created_count} unique issue(s)"
                )
            else:
                logger.info(
                    f"[{self.config.domain.upper()}] Successfully generated {created_count} issue(s)"
                )

        except JSONParseError:
            logger.error(
                f"[{self.config.domain.upper()}] Failed to parse Claude response as JSON",
                extra={
                    "response_preview": response_text[:1000],
                    "response_end": response_text[-500:]
                }
            )
            raise
        except Exception as e:
            logger.exception(f"[{self.config.domain.upper()}] Error creating issues")
            raise
