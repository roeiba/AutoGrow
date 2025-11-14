#!/usr/bin/env python3
"""
Issue Resolver Agent - Core Logic

Takes an open issue, analyzes it with Claude AI using Agent SDK, implements a fix, and creates a PR
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
import git

# Add src directory to path to import modules
src_dir = Path(__file__).parent.parent
claude_agent_dir = src_dir / "claude-agent"
sys.path.insert(0, str(claude_agent_dir))
sys.path.insert(0, str(src_dir))

# Import logging
from logging_config import get_logger

# Import exception classes
from utils.exceptions import (
    GitHubAPIError,
    AnthropicAPIError,
    RateLimitError,
    AuthenticationError,
    BranchError,
    PushError,
    PRCreationError,
    AgentError,
    AgentResponseError,
    ValidationError,
    get_exception_for_github_error,
    get_exception_for_anthropic_error,
)

# Initialize logger
logger = get_logger(__name__)

# Import Claude CLI Agent
try:
    from claude_cli_agent import ClaudeAgent
    USE_CLAUDE_CLI = True
    logger.info("✅ Claude CLI Agent imported successfully")
except ImportError as e:
    logger.warning(f"⚠️  claude_cli_agent not available: {e}, falling back to anthropic SDK")
    from anthropic import Anthropic
    USE_CLAUDE_CLI = False

# Import model configuration
from models_config import CLAUDE_MODELS

# Import validator and retry utilities
from utils.project_brief_validator import validate_project_brief, get_project_brief
from utils.retry import retry_github_api
from utils.outcome_tracker import OutcomeTracker, ResolutionStatus
from utils.github_helpers import get_readme, get_open_issues_sorted, get_issue, create_pull_request


class IssueResolver:
    """Resolves GitHub issues using AI and creates pull requests"""

    def __init__(
        self,
        repo,
        git_repo,
        anthropic_api_key: Optional[str] = None,
        labels_to_handle: Optional[List[str]] = None,
        labels_to_skip: Optional[List[str]] = None,
        max_time: int = 480,
        dry_mode: bool = False,
    ):
        """
        Initialize the Issue Resolver

        Args:
            repo: PyGithub Repository object
            git_repo: GitPython Repo object
            anthropic_api_key: Anthropic API key (required if not using Claude CLI)
            labels_to_handle: List of labels to handle (default: bug, enhancement)
            labels_to_skip: List of labels to skip (default: wontfix, duplicate, in-progress)
            max_time: Maximum execution time in seconds
            dry_mode: If True, skip all GitHub write operations (for CI validation)
        """
        self.repo = repo
        self.git_repo = git_repo
        self.anthropic_api_key = anthropic_api_key
        self.labels_to_handle = labels_to_handle or ["bug", "enhancement"]
        self.labels_to_skip = labels_to_skip or ["wontfix", "duplicate", "in-progress"]
        self.max_time = max_time
        self.dry_mode = dry_mode
        self.start_time = time.time()

        # Initialize outcome tracker for feedback loop
        self.outcome_tracker = OutcomeTracker()

        logger.info("Issue Resolver Agent Initialized")
        logger.info(f"Config: labels_to_handle={self.labels_to_handle}, labels_to_skip={self.labels_to_skip}")
        logger.info(f"Config: dry_mode={self.dry_mode}, outcome_tracking=enabled")
        logger.info("Supports: features, bugs, documentation, refactoring, tests, performance, security, CI/CD")

    def resolve_issue(self, specific_issue: Optional[int] = None) -> bool:
        """
        Resolve an issue and create a PR

        Args:
            specific_issue: Specific issue number to resolve (optional)

        Returns:
            bool: True if issue was resolved, False otherwise
        """
        logger.info("=" * 80)
        logger.info("STARTING ISSUE RESOLUTION WORKFLOW")
        logger.info("=" * 80)

        # Select issue
        selected_issue = self._select_issue(specific_issue)

        if not selected_issue:
            logger.warning("WORKFLOW ABORTED: No suitable issues found")
            logger.info("=" * 80)
            return False

        logger.info(f"ISSUE SELECTED: #{selected_issue.number}")
        logger.info(f"Title: {selected_issue.title}")
        logger.info(f"Labels: {[label.name for label in selected_issue.labels]}")
        logger.info(f"Created: {selected_issue.created_at}")

        # Record attempt in outcome tracker
        issue_labels = [label.name for label in selected_issue.labels]
        if not self.dry_mode:
            self.outcome_tracker.record_attempt(
                issue_number=selected_issue.number,
                issue_title=selected_issue.title,
                labels=issue_labels,
                status=ResolutionStatus.PENDING
            )
            logger.debug("Outcome tracking: Recorded attempt")

        # Claim the issue
        issue_claimed = self._claim_issue(selected_issue)

        # Get issue details for validation check
        issue_body = selected_issue.body or "No description provided"
        issue_labels = [label.name for label in selected_issue.labels]

        # Validate PROJECT_BRIEF.md before proceeding
        is_valid, validation_msg = self._validate_project_brief_if_exists(
            issue_title=selected_issue.title,
            issue_body=issue_body,
            issue_labels=issue_labels,
        )

        if not is_valid:
            logger.error("PROJECT_BRIEF.md validation failed - aborting to save API calls")
            if not self.dry_mode:
                try:
                    selected_issue.create_comment(
                        f"**Pre-flight check failed**\n\n{validation_msg}\n\n"
                        "Please fix PROJECT_BRIEF.md validation errors before I can proceed.\n\n"
                        "---\n*Issue Resolver Agent*"
                    )
                except Exception as e:
                    github_error = get_exception_for_github_error(e, "Failed to post validation failure comment")
                    logger.exception(f"Failed to post validation failure comment: {github_error}")
            else:
                logger.debug("DRY MODE: Would post validation failure comment")
            return False

        # Add validation success to issue comment if there was a validation
        if validation_msg:
            if not self.dry_mode:
                try:
                    selected_issue.create_comment(validation_msg)
                except Exception as e:
                    github_error = get_exception_for_github_error(e, "Failed to post validation success comment")
                    logger.exception(f"Failed to post validation success comment: {github_error}")
            else:
                logger.debug("DRY MODE: Would post validation success comment")

        # Create branch
        branch_name = f"fix/issue-{selected_issue.number}-{int(time.time())}"
        if not self._create_branch(branch_name, selected_issue, issue_claimed):
            return False

        # Generate fix using Claude
        summary = self._generate_fix(selected_issue, issue_body, issue_labels)

        if summary is None:
            if issue_claimed and not self.dry_mode:
                try:
                    selected_issue.create_comment("Failed to generate fix")
                except Exception as e:
                    github_error = get_exception_for_github_error(e, "Failed to post fix generation failure comment")
                    logger.exception(f"Failed to post fix generation failure comment: {github_error}")
                # Track failure
                self.outcome_tracker.update_status(
                    issue_number=selected_issue.number,
                    status=ResolutionStatus.FAILED,
                    error_message="Failed to generate fix with Claude AI"
                )
                logger.debug("Outcome tracking: Marked as FAILED")
            elif issue_claimed:
                logger.debug("DRY MODE: Would post fix generation failure comment")
            return False

        # Check if files were modified and create PR
        return self._create_pr_if_changes(selected_issue, branch_name, summary)

    def _select_issue(self, specific_issue: Optional[int]) -> Optional[object]:
        """Select an issue to work on"""
        logger.info("-" * 80)
        logger.info("STEP 1: ISSUE SELECTION")
        logger.info("-" * 80)

        if specific_issue:
            logger.info(f"Mode: Specific issue requested (#{specific_issue})")

            try:
                issue = get_issue(self.repo, int(specific_issue))
                logger.info(f"Found issue: {issue.title}")
                return issue
            except Exception as e:
                github_error = get_exception_for_github_error(e, f"Failed to get issue #{specific_issue}")
                logger.exception(f"Failed to get issue #{specific_issue}: {github_error}")
                raise github_error

        logger.info("Mode: Searching for suitable issue")
        logger.info(f"Criteria: state=open, labels_to_handle={self.labels_to_handle}, labels_to_skip={self.labels_to_skip}")

        try:
            open_issues = get_open_issues_sorted(self.repo, sort="created", direction="asc")
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to get open issues")
            logger.exception(f"Failed to get open issues: {github_error}")
            raise github_error

        issues_checked = 0
        for issue in open_issues:
            issues_checked += 1

            if issue.pull_request:
                logger.debug(f"Skipping #{issue.number}: Is a pull request")
                continue

            issue_labels = [label.name for label in issue.labels]

            if any(skip_label in issue_labels for skip_label in self.labels_to_skip):
                skip_label_found = [l for l in issue_labels if l in self.labels_to_skip]
                logger.debug(f"Skipping #{issue.number}: Has skip label {skip_label_found}")
                continue

            if self.labels_to_handle and not any(
                handle_label in issue_labels for handle_label in self.labels_to_handle
            ):
                logger.debug(f"Skipping #{issue.number}: No matching labels (has: {issue_labels})")
                continue

            try:
                comments = list(issue.get_comments())
            except Exception as e:
                github_error = get_exception_for_github_error(e, f"Failed to get comments for issue #{issue.number}")
                logger.warning(f"Failed to get comments for issue #{issue.number}: {github_error}")
                continue

            if any(
                "Issue Resolver Agent" in c.body and "claimed" in c.body.lower()
                for c in comments
            ):
                logger.debug(f"Skipping #{issue.number}: Already claimed by agent")
                continue

            logger.info(f"SELECTED: Issue #{issue.number}")
            logger.info(f"Title: {issue.title}")
            logger.info(f"Labels: {issue_labels}")
            logger.info(f"Reason: Matches all criteria (checked {issues_checked} issues total)")
            return issue

        logger.warning(f"No suitable issues found (checked {issues_checked} issues)")
        return None

    def _claim_issue(self, issue) -> bool:
        """Claim an issue by adding a comment and label"""
        logger.info("-" * 80)
        logger.info("STEP 2: CLAIMING ISSUE")
        logger.info("-" * 80)

        claim_message = f"""**Issue Resolver Agent**

I'm working on this issue now.

**Started at:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Status:** In Progress

---
*Automated by GitHub Actions*"""

        if self.dry_mode:
            logger.debug("DRY MODE: Would add 'in-progress' label")
            logger.debug("DRY MODE: Would post claim comment to issue")
            return True

        @retry_github_api
        def create_comment():
            return issue.create_comment(claim_message)

        @retry_github_api
        def add_label():
            return issue.add_to_labels("in-progress")

        try:
            create_comment()
            logger.info("Posted claim comment to issue")
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to post claim comment")
            logger.exception(f"Failed to post claim comment: {github_error}")
            raise github_error

        try:
            add_label()
            logger.info("Added 'in-progress' label")
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to add in-progress label")
            logger.warning(f"Failed to add in-progress label: {github_error}")
            # Don't raise here - claiming without label is acceptable

        return True

    def _should_skip_validation(
        self, issue_title: str, issue_body: str, issue_labels: List[str]
    ) -> bool:
        """Determine if PROJECT_BRIEF.md validation should be skipped"""
        skip_keywords = [
            "project_brief",
            "project brief",
            "template",
            "example",
            "documentation",
            "readme",
            "setup",
            "initial",
            "bootstrap",
        ]

        text_to_check = f"{issue_title} {issue_body}".lower()
        if any(keyword in text_to_check for keyword in skip_keywords):
            return True

        skip_labels = ["documentation", "setup", "template"]
        if any(label in skip_labels for label in issue_labels):
            return True

        return False

    def _validate_project_brief_if_exists(
        self,
        issue_title: str = "",
        issue_body: str = "",
        issue_labels: Optional[List[str]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate PROJECT_BRIEF.md if it exists"""
        logger.info("-" * 80)
        logger.info("STEP 3: PROJECT BRIEF VALIDATION")
        logger.info("-" * 80)

        issue_labels = issue_labels or []

        if self._should_skip_validation(issue_title, issue_body, issue_labels):
            logger.info("Skipping validation (issue is about templates/documentation)")
            return True, None

        project_brief_path = Path("PROJECT_BRIEF.md")

        if not project_brief_path.exists():
            logger.info("No PROJECT_BRIEF.md found (optional)")
            return True, None

        logger.info("Validating PROJECT_BRIEF.md...")
        try:
            result = validate_project_brief(project_brief_path)
        except Exception as e:
            logger.exception(f"PROJECT_BRIEF.md validation error: {e}")
            raise ValidationError(f"Failed to validate PROJECT_BRIEF.md: {e}")

        if result.is_valid:
            logger.info("PROJECT_BRIEF.md validation passed")
            validation_msg = "PROJECT_BRIEF.md validated successfully"

            if result.warnings:
                logger.warning(f"Validation warnings: {len(result.warnings)}")
                for warning in result.warnings[:3]:
                    logger.warning(f"- {warning}")
                validation_msg += f"\n\n**Warnings ({len(result.warnings)}):**\n"
                for warning in result.warnings[:5]:
                    validation_msg += f"- {warning}\n"

            return True, validation_msg
        else:
            logger.error("PROJECT_BRIEF.md validation failed")
            for error in result.errors[:5]:
                logger.error(f"- {error}")

            validation_msg = "PROJECT_BRIEF.md validation failed\n\n**Errors:**\n"
            for error in result.errors[:5]:
                validation_msg += f"- {error}\n"

            if result.warnings:
                validation_msg += f"\n**Warnings:**\n"
                for warning in result.warnings[:3]:
                    validation_msg += f"- {warning}\n"

            return False, validation_msg

    def _create_branch(self, branch_name: str, issue, issue_claimed: bool) -> bool:
        """Create a new git branch"""
        logger.info("-" * 80)
        logger.info("STEP 4: BRANCH CREATION")
        logger.info("-" * 80)
        logger.info(f"Branch name: {branch_name}")

        try:
            self.git_repo.git.checkout("-b", branch_name)
            logger.info("Branch created successfully")
            return True
        except git.GitCommandError as e:
            error = BranchError(f"Failed to create branch {branch_name}: {e}")
            logger.exception(f"Failed to create branch: {error}")
            if issue_claimed and not self.dry_mode:
                try:
                    issue.create_comment(f"Failed to create branch: {error}")
                except Exception as comment_error:
                    github_error = get_exception_for_github_error(comment_error, "Failed to post branch creation failure comment")
                    logger.exception(f"Failed to post branch creation failure comment: {github_error}")
            elif issue_claimed:
                logger.debug("DRY MODE: Would post branch creation failure comment")
            return False

    def _generate_fix(
        self, issue, issue_body: str, issue_labels: List[str]
    ) -> Optional[str]:
        """Generate a fix using Claude AI"""
        logger.info("-" * 80)
        logger.info("STEP 5: GENERATING FIX WITH CLAUDE AI")
        logger.info("-" * 80)

        # Get context with retry
        try:
            readme = get_readme(self.repo, max_length=2000)
            if readme == "No README found":
                logger.warning("No README found")
            else:
                logger.info("Loaded README context")
        except Exception as e:
            readme = "No README found"
            github_error = get_exception_for_github_error(e, "Failed to load README")
            logger.warning(f"Failed to load README: {github_error}")

        project_brief = get_project_brief()
        if not project_brief:
            logger.warning("No PROJECT_BRIEF.md found")
        else:
            logger.info("Loaded PROJECT_BRIEF.md context")
        
        # Build prompt for Claude CLI
        cli_prompt = f"""You are an expert software engineer. 
Fix this GitHub issue by modifying the necessary files.
Save your tokens and don't write documents unless asked. 

Repository: {self.repo.full_name}
Issue #{issue.number}: {issue.title}

Description:
{issue_body}

Labels: {', '.join(issue_labels)}

Context from README:
{readme}

Project Context:
{project_brief}
"""

        logger.debug(f"Prompt prepared ({len(cli_prompt)} chars)")
        logger.info(f"Issue type: {', '.join(issue_labels)}")

        # Try Claude CLI first if available
        if USE_CLAUDE_CLI:
            logger.info("Attempting to use Claude CLI Agent...")
            logger.debug("Tools enabled: Read, Write, Bash")
            logger.debug("Permission mode: acceptEdits")

            try:
                # Try to initialize with require_cli=False to check availability
                agent = ClaudeAgent(
                    output_format="text",
                    verbose=True,
                    allowed_tools=["Read", "Write", "Bash"],
                    permission_mode="acceptEdits",
                    require_cli=False,
                )

                if agent.cli_available:
                    logger.info("Sending query to Claude CLI...")
                    logger.info("=" * 76)
                    result = agent.query(cli_prompt, stream_output=True)
                    logger.info("=" * 76)

                    # Extract the response
                    if isinstance(result, dict) and "result" in result:
                        summary = result["result"]
                    else:
                        summary = str(result)

                    logger.info("Claude CLI completed work successfully")
                    logger.info(f"Response length: {len(summary)} chars")

                    # Print the full output
                    logger.info("CLAUDE OUTPUT:")
                    logger.info("-" * 76)
                    for line in summary.split('\n'):
                        logger.info(line)
                    logger.info("-" * 76)

                    return summary
                else:
                    logger.warning("Claude CLI not available, falling back to Anthropic SDK")

            except Exception as e:
                agent_error = AgentError(f"Claude CLI error: {e}")
                logger.warning(f"Claude CLI error: {agent_error}")
                logger.info("Falling back to Anthropic SDK")

        # Fallback to Anthropic SDK
        logger.info("Using Anthropic SDK (API-based approach)")

        if not self.anthropic_api_key:
            logger.error("No Anthropic API key provided")
            return None

        try:
            client = Anthropic(api_key=self.anthropic_api_key)

            # Build a simpler prompt for API (no tool use)
            api_prompt = f"""You are an expert software engineer. Analyze this GitHub issue and provide a detailed solution.

Repository: {self.repo.full_name}
Issue #{issue.number}: {issue.title}

Description:
{issue_body}

Labels: {', '.join(issue_labels)}

Context from README:
{readme}

Project Context:
{project_brief}

Please provide:
1. Analysis of the issue
2. Detailed solution approach
3. Specific code changes needed (with file paths and code snippets)
4. Testing recommendations

Format your response clearly with sections."""

            logger.info("Sending query to Claude API...")

            response = client.messages.create(
                model=CLAUDE_MODELS.ISSUE_RESOLUTION,
                max_tokens=CLAUDE_MODELS.WORKFLOW_MAX_TOKENS,
                messages=[{"role": "user", "content": api_prompt}]
            )

            summary = response.content[0].text

            logger.info("Claude API completed successfully")
            logger.info(f"Response length: {len(summary)} chars")

            # Print the output
            logger.info("CLAUDE OUTPUT:")
            logger.info("-" * 76)
            summary_lines = summary.split('\n')
            for line in summary_lines[:50]:  # Limit output
                logger.info(line)
            if len(summary_lines) > 50:
                remaining_lines = len(summary_lines) - 50
                logger.info(f"... ({remaining_lines} more lines)")
            logger.info("-" * 76)

            logger.warning("Note: API mode provides guidance only")
            logger.info("Manual code changes may be needed based on the suggestions")

            return summary

        except Exception as e:
            anthropic_error = get_exception_for_anthropic_error(e, "Anthropic SDK error")
            logger.exception(f"Anthropic SDK error: {anthropic_error}")
            return None

    def _create_pr_if_changes(self, issue, branch_name: str, summary: str) -> bool:
        """Create a PR if files were modified"""
        logger.info("-" * 80)
        logger.info("STEP 6: COMMITTING CHANGES & CREATING PR")
        logger.info("-" * 80)

        if not self.git_repo.is_dirty(untracked_files=True):
            logger.warning("No files were modified")
            if not self.dry_mode:
                try:
                    issue.create_comment(
                        "No changes were made. The issue may need manual review."
                    )
                except Exception as e:
                    github_error = get_exception_for_github_error(e, "Failed to post no changes comment")
                    logger.exception(f"Failed to post no changes comment: {github_error}")
                # Track as failed (no changes)
                self.outcome_tracker.update_status(
                    issue_number=issue.number,
                    status=ResolutionStatus.FAILED,
                    error_message="No file changes generated"
                )
                logger.debug("Outcome tracking: Marked as FAILED (no changes)")
            else:
                logger.debug("DRY MODE: Would post no changes comment")
            return False

        # Get list of changed files
        changed_files = [item.a_path for item in self.git_repo.index.diff(None)]
        untracked_files = self.git_repo.untracked_files
        files_modified = changed_files + untracked_files

        logger.info(f"Files modified: {len(files_modified)}")
        for f in files_modified:
            logger.info(f"- {f}")

        # Commit changes
        logger.info("Committing changes...")
        try:
            self.git_repo.git.add("-A")
            commit_message = f"""Fix: Resolve issue #{issue.number}

{issue.title}

Closes #{issue.number}

---
Generated by Issue Resolver Agent using Claude Agent SDK"""

            self.git_repo.index.commit(commit_message)
            logger.info("Changes committed")
        except git.GitCommandError as e:
            error = BranchError(f"Failed to commit changes: {e}")
            logger.exception(f"Failed to commit changes: {error}")
            raise error

        if self.dry_mode:
            logger.debug(f"DRY MODE: Would push branch '{branch_name}' to origin")
            logger.debug("DRY MODE: Would create pull request")
            logger.debug("DRY MODE: Would update issue with results")
            logger.info("=" * 80)
            logger.info("DRY MODE: WORKFLOW VALIDATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"SUMMARY (DRY MODE):")
            logger.info(f"Issue: #{issue.number} - {issue.title}")
            logger.info(f"Branch: {branch_name}")
            logger.info(f"Files changed: {len(files_modified)}")
            logger.info(f"Status: Would be ready for review")
            logger.info("=" * 80)
            return True

        # Push
        logger.info(f"Pushing branch '{branch_name}' to origin...")
        origin = self.git_repo.remote("origin")
        try:
            push_info = origin.push(branch_name)
            if push_info and push_info[0].flags & push_info[0].ERROR:
                raise PushError(f"Push failed: {push_info[0].summary}")
            logger.info("Branch pushed successfully")
        except git.GitCommandError as e:
            error = PushError(f"Failed to push branch: {e}")
            logger.exception(f"Failed to push branch: {error}")
            raise error

        # Create PR with retry
        logger.info("Creating Pull Request...")
        pr_title = f"Fix: {issue.title}"
        pr_body = f"""{summary[:500]}

## Changes
{chr(10).join(['- ' + f for f in files_modified[:20]])}

Closes #{issue.number}

---
*Generated by Issue Resolver Agent using Claude Agent SDK*"""

        try:
            pr = create_pull_request(
                self.repo, 
                title=pr_title, 
                body=pr_body, 
                head=branch_name, 
                base="main"
            )
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to create pull request")
            error = PRCreationError(f"Failed to create pull request: {github_error}")
            logger.exception(f"Failed to create pull request: {error}")
            raise error

        logger.info(f"Pull Request created: #{pr.number}")
        logger.info(f"URL: {pr.html_url}")

        # Track successful PR creation
        self.outcome_tracker.update_status(
            issue_number=issue.number,
            status=ResolutionStatus.RESOLVED,
            pr_number=pr.number,
            files_changed=len(files_modified)
        )
        logger.debug(f"Outcome tracking: Marked as RESOLVED (PR #{pr.number})")

        # Update issue with retry
        logger.info("Updating issue with results...")

        @retry_github_api
        def update_issue():
            return issue.create_comment(
                f"""**Solution Ready**

Pull Request: #{pr.number}

**Changes:**
{chr(10).join(['- ' + f for f in files_modified[:10]])}

---
*Completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*"""
            )

        try:
            update_issue()
            logger.info("Issue updated")
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to update issue")
            logger.exception(f"Failed to update issue: {github_error}")
            # Don't raise here - PR was created successfully

        logger.info("=" * 80)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"SUMMARY:")
        logger.info(f"Issue: #{issue.number} - {issue.title}")
        logger.info(f"Branch: {branch_name}")
        logger.info(f"PR: #{pr.number}")
        logger.info(f"Files changed: {len(files_modified)}")
        logger.info(f"Status: Ready for review")
        logger.info("=" * 80)
        return True
