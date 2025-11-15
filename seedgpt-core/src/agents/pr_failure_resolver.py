#!/usr/bin/env python3
"""
PR Failure Resolver Agent - Core Logic

Takes open PRs with failing checks, analyzes failures with Claude AI, fixes them, and updates the PR
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

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
from utils.github_helpers import (
    get_readme,
    get_pull_request,
    get_open_pull_requests,
    get_pr_checks,
    get_pr_files,
    get_pr_comments,
)
from utils.git_helpers import (
    checkout_branch,
    is_repo_dirty,
    get_all_changed_files,
    commit_changes,
    push_branch,
    create_commit_message,
)


class PRFailureResolver:
    """Resolves failing PR checks using AI and updates the PR"""

    def __init__(
        self,
        repo,
        git_repo,
        anthropic_api_key: Optional[str] = None,
        max_time: int = 480,
        dry_mode: bool = False,
    ):
        """
        Initialize the PR Failure Resolver

        Args:
            repo: PyGithub Repository object
            git_repo: GitPython Repo object
            anthropic_api_key: Anthropic API key (required if not using Claude CLI)
            max_time: Maximum execution time in seconds
            dry_mode: If True, skip all GitHub write operations (for CI validation)
        """
        self.repo = repo
        self.git_repo = git_repo
        self.anthropic_api_key = anthropic_api_key
        self.max_time = max_time
        self.dry_mode = dry_mode
        self.start_time = time.time()

        # Initialize outcome tracker for feedback loop
        self.outcome_tracker = OutcomeTracker()

        logger.info("PR Failure Resolver Agent Initialized")
        logger.info(f"Config: dry_mode={self.dry_mode}, outcome_tracking=enabled")
        logger.info("Supports: test failures, build errors, linting issues, CI/CD failures")

    def resolve_pr_failure(self, specific_pr: Optional[int] = None) -> bool:
        """
        Resolve a failing PR and update it

        Args:
            specific_pr: Specific PR number to resolve (optional)

        Returns:
            bool: True if PR was fixed, False otherwise
        """
        logger.info("=" * 80)
        logger.info("STARTING PR FAILURE RESOLUTION WORKFLOW")
        logger.info("=" * 80)

        # Select PR with failures
        selected_pr = self._select_failing_pr(specific_pr)

        if not selected_pr:
            logger.warning("WORKFLOW ABORTED: No failing PRs found")
            logger.info("=" * 80)
            return False

        logger.info(f"PR SELECTED: #{selected_pr.number}")
        logger.info(f"Title: {selected_pr.title}")
        logger.info(f"Branch: {selected_pr.head.ref}")
        logger.info(f"Created: {selected_pr.created_at}")

        # Record attempt in outcome tracker
        if not self.dry_mode:
            self.outcome_tracker.record_attempt(
                issue_number=selected_pr.number,
                issue_title=f"PR: {selected_pr.title}",
                labels=["pr-failure"],
                status=ResolutionStatus.PENDING
            )
            logger.debug("Outcome tracking: Recorded attempt")

        # Claim the PR
        pr_claimed = self._claim_pr(selected_pr)

        # Get PR failure details
        failure_details = self._get_failure_details(selected_pr)

        if not failure_details:
            logger.warning("No failure details found")
            if pr_claimed and not self.dry_mode:
                try:
                    selected_pr.create_issue_comment("Could not determine failure details")
                except Exception as e:
                    github_error = get_exception_for_github_error(e, "Failed to post failure details comment")
                    logger.exception(f"Failed to post failure details comment: {github_error}")
            return False

        # Checkout PR branch
        if not self._checkout_pr_branch(selected_pr, pr_claimed):
            return False

        # Generate fix using Claude
        summary = self._generate_fix(selected_pr, failure_details)

        if summary is None:
            if pr_claimed and not self.dry_mode:
                try:
                    selected_pr.create_issue_comment("Failed to generate fix for PR failures")
                except Exception as e:
                    github_error = get_exception_for_github_error(e, "Failed to post fix generation failure comment")
                    logger.exception(f"Failed to post fix generation failure comment: {github_error}")
                # Track failure
                self.outcome_tracker.update_status(
                    issue_number=selected_pr.number,
                    status=ResolutionStatus.FAILED,
                    error_message="Failed to generate fix with Claude AI"
                )
                logger.debug("Outcome tracking: Marked as FAILED")
            elif pr_claimed:
                logger.debug("DRY MODE: Would post fix generation failure comment")
            return False

        # Check if files were modified and push changes
        return self._push_changes_if_modified(selected_pr, summary)

    def _select_failing_pr(self, specific_pr: Optional[int]) -> Optional[object]:
        """Select a failing PR to work on"""
        logger.info("-" * 80)
        logger.info("STEP 1: PR SELECTION")
        logger.info("-" * 80)

        if specific_pr:
            logger.info(f"Mode: Specific PR requested (#{specific_pr})")

            try:
                pr = get_pull_request(self.repo, int(specific_pr))
                logger.info(f"Found PR: {pr.title}")
                return pr
            except Exception as e:
                github_error = get_exception_for_github_error(e, f"Failed to get PR #{specific_pr}")
                logger.exception(f"Failed to get PR #{specific_pr}: {github_error}")
                raise github_error

        logger.info("Mode: Searching for failing PR")
        logger.info("Criteria: state=open, checks=failing OR merge conflicts")

        try:
            open_prs = get_open_pull_requests(self.repo)
            open_prs_list = list(open_prs)
            logger.info(f"Found {len(open_prs_list)} open PR(s) to check")
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to get open PRs")
            logger.exception(f"Failed to get open PRs: {github_error}")
            raise github_error

        prs_checked = 0
        for pr in open_prs:
            prs_checked += 1
            
            logger.info(f"\n📋 Checking PR #{pr.number}: {pr.title}")
            logger.info(f"   Author: {pr.user.login}")
            logger.info(f"   Branch: {pr.head.ref} → {pr.base.ref}")
            logger.info(f"   Draft: {pr.draft}")

            # Skip draft PRs
            if pr.draft:
                logger.info(f"   ⏭️  SKIPPED: Is a draft PR")
                continue

            # Check if already claimed by this agent
            try:
                comments = list(get_pr_comments(pr))
            except Exception as e:
                github_error = get_exception_for_github_error(e, f"Failed to get comments for PR #{pr.number}")
                logger.warning(f"   ⚠️  Failed to get comments: {github_error}")
                continue

            if any(
                "PR Failure Resolver Agent" in c.body and "working on" in c.body.lower()
                for c in comments
            ):
                logger.info(f"   ⏭️  SKIPPED: Already claimed by agent")
                continue

            # Check if PR has failing checks or merge conflicts
            try:
                # Check for merge conflicts
                has_merge_conflict = False
                mergeable_state = pr.mergeable_state
                logger.info(f"   Mergeable State: {mergeable_state}")
                
                if mergeable_state in ['dirty', 'conflicting']:
                    has_merge_conflict = True
                    logger.info(f"   🔴 MERGE CONFLICT DETECTED")
                
                # Check for failing check runs
                checks = get_pr_checks(pr)
                logger.info(f"   Check Runs: {len(checks)} total")
                
                failing_checks = []
                for check in checks:
                    if check.conclusion in ['failure', 'timed_out', 'action_required']:
                        failing_checks.append(f"{check.name} ({check.conclusion})")
                        logger.info(f"      🔴 {check.name}: {check.conclusion}")
                    elif check.conclusion == 'success':
                        logger.info(f"      ✅ {check.name}: success")
                    elif check.conclusion is None:
                        logger.info(f"      ⏳ {check.name}: in_progress")
                    else:
                        logger.info(f"      ⚪ {check.name}: {check.conclusion}")
                
                has_check_failures = len(failing_checks) > 0
                
                # Check combined status (for older-style status checks)
                has_status_failures = False
                try:
                    commits = list(pr.get_commits())
                    if commits:
                        latest_commit = commits[-1]
                        combined_status = latest_commit.get_combined_status()
                        logger.info(f"   Combined Status: {combined_status.state}")
                        
                        if combined_status.state in ['failure', 'error']:
                            has_status_failures = True
                            logger.info(f"   🔴 STATUS CHECK FAILURES DETECTED")
                            for status in combined_status.statuses:
                                if status.state in ['failure', 'error']:
                                    logger.info(f"      🔴 {status.context}: {status.state}")
                except Exception as status_err:
                    logger.debug(f"   Could not check combined status: {status_err}")
                
                # Select PR if it has any type of failure
                if not (has_merge_conflict or has_check_failures or has_status_failures):
                    logger.info(f"   ✅ SKIPPED: No failures detected (all checks passing)")
                    continue

                # Determine failure reason
                failure_reasons = []
                if has_merge_conflict:
                    failure_reasons.append("merge conflicts")
                if has_check_failures:
                    failure_reasons.append(f"failing checks ({len(failing_checks)})")
                if has_status_failures:
                    failure_reasons.append("failing status")
                
                logger.info(f"\n🎯 SELECTED: PR #{pr.number}")
                logger.info(f"   Title: {pr.title}")
                logger.info(f"   Branch: {pr.head.ref}")
                logger.info(f"   Failures: {', '.join(failure_reasons)}")
                logger.info(f"   Total PRs checked: {prs_checked}")
                return pr

            except Exception as e:
                github_error = get_exception_for_github_error(e, f"Failed to check PR #{pr.number} status")
                logger.warning(f"   ⚠️  Failed to check status: {github_error}")
                continue

        logger.warning(f"\n❌ No failing PRs found (checked {prs_checked} PRs)")
        return None

    def _claim_pr(self, pr) -> bool:
        """Claim a PR by adding a comment"""
        logger.info("-" * 80)
        logger.info("STEP 2: CLAIMING PR")
        logger.info("-" * 80)

        claim_message = f"""**PR Failure Resolver Agent**

I'm working on fixing the failing checks in this PR.

**Started at:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Status:** In Progress

---
*Automated by GitHub Actions*"""

        if self.dry_mode:
            logger.debug("DRY MODE: Would post claim comment to PR")
            return True

        @retry_github_api
        def create_comment():
            return pr.create_issue_comment(claim_message)

        try:
            create_comment()
            logger.info("Posted claim comment to PR")
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to post claim comment")
            logger.exception(f"Failed to post claim comment: {github_error}")
            raise github_error

        return True

    def _get_failure_details(self, pr) -> Optional[str]:
        """Get detailed information about PR failures"""
        logger.info("-" * 80)
        logger.info("STEP 3: ANALYZING FAILURES")
        logger.info("-" * 80)

        failure_details = []
        
        # Check for merge conflicts
        mergeable_state = pr.mergeable_state
        if mergeable_state in ['dirty', 'conflicting']:
            logger.info("Merge conflict detected")
            conflict_detail = f"""
Merge Conflict Detected
Status: {mergeable_state}
Description: This PR has merge conflicts that need to be resolved before it can be merged.
The conflicts may be in one or more files that have been modified in both this branch and the base branch.
"""
            failure_details.append(conflict_detail)

        # Check for failing check runs
        try:
            checks = get_pr_checks(pr)
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to get PR checks")
            logger.exception(f"Failed to get PR checks: {github_error}")
            checks = []

        failing_checks = [
            check for check in checks
            if check.conclusion in ['failure', 'timed_out', 'action_required']
        ]

        if failing_checks:
            logger.info(f"Found {len(failing_checks)} failing check(s)")

            for check in failing_checks:
                logger.info(f"- {check.name}: {check.conclusion}")
                
                detail = f"""
Check: {check.name}
Status: {check.conclusion}
"""
                
                # Try to get check run details
                if hasattr(check, 'output') and check.output:
                    if hasattr(check.output, 'title') and check.output.title:
                        detail += f"Title: {check.output.title}\n"
                    if hasattr(check.output, 'summary') and check.output.summary:
                        detail += f"Summary: {check.output.summary[:500]}\n"
                    if hasattr(check.output, 'text') and check.output.text:
                        detail += f"Details: {check.output.text[:1000]}\n"
                
                failure_details.append(detail)
        
        # Check combined status (for older-style status checks)
        try:
            commits = list(pr.get_commits())
            if commits:
                latest_commit = commits[-1]
                combined_status = latest_commit.get_combined_status()
                if combined_status.state in ['failure', 'error']:
                    logger.info(f"Found failing combined status: {combined_status.state}")
                    for status in combined_status.statuses:
                        if status.state in ['failure', 'error']:
                            logger.info(f"- {status.context}: {status.state}")
                            status_detail = f"""
Status Check: {status.context}
State: {status.state}
Description: {status.description or 'No description available'}
"""
                            failure_details.append(status_detail)
        except Exception as status_err:
            logger.debug(f"Could not check combined status: {status_err}")

        if not failure_details:
            logger.warning("No failure details found")
            return None

        return "\n---\n".join(failure_details)

    def _checkout_pr_branch(self, pr, pr_claimed: bool) -> bool:
        """Checkout the PR branch"""
        logger.info("-" * 80)
        logger.info("STEP 4: CHECKING OUT PR BRANCH")
        logger.info("-" * 80)
        logger.info(f"Branch name: {pr.head.ref}")

        try:
            checkout_branch(self.git_repo, pr.head.ref, remote_name="origin")
            return True
        except BranchError as error:
            if pr_claimed and not self.dry_mode:
                try:
                    pr.create_issue_comment(f"Failed to checkout branch: {error}")
                except Exception as comment_error:
                    github_error = get_exception_for_github_error(comment_error, "Failed to post checkout failure comment")
                    logger.exception(f"Failed to post checkout failure comment: {github_error}")
            elif pr_claimed:
                logger.debug("DRY MODE: Would post checkout failure comment")
            return False

    def _generate_fix(self, pr, failure_details: str) -> Optional[str]:
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

        # Get PR files
        try:
            pr_files = get_pr_files(pr)
            files_changed = [f.filename for f in pr_files]
            logger.info(f"PR modifies {len(files_changed)} file(s)")
        except Exception as e:
            files_changed = []
            github_error = get_exception_for_github_error(e, "Failed to get PR files")
            logger.warning(f"Failed to get PR files: {github_error}")
        
        # Build prompt for Claude CLI
        cli_prompt = f"""You are an expert software engineer fixing failing CI/CD checks.

Repository: {self.repo.full_name}
PR #{pr.number}: {pr.title}

PR Description:
{pr.body or 'No description provided'}

Files Changed in PR:
{chr(10).join(['- ' + f for f in files_changed[:20]])}

Failing Checks:
{failure_details}

Context from README:
{readme}

Project Context:
{project_brief}

Your task:
1. Analyze the failing checks and identify the root cause
2. Fix the issues in the codebase
3. Ensure all tests pass and code quality checks succeed
4. Make minimal, focused changes to resolve the failures

Save your tokens and don't write documents unless asked.
"""

        logger.debug(f"Prompt prepared ({len(cli_prompt)} chars)")

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
            api_prompt = f"""You are an expert software engineer. Analyze this failing PR and provide a detailed solution.

Repository: {self.repo.full_name}
PR #{pr.number}: {pr.title}

PR Description:
{pr.body or 'No description provided'}

Files Changed in PR:
{chr(10).join(['- ' + f for f in files_changed[:20]])}

Failing Checks:
{failure_details}

Context from README:
{readme}

Project Context:
{project_brief}

Please provide:
1. Analysis of the failures
2. Root cause identification
3. Detailed solution approach
4. Specific code changes needed (with file paths and code snippets)
5. Testing recommendations

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

    def _push_changes_if_modified(self, pr, summary: str) -> bool:
        """Push changes if files were modified"""
        logger.info("-" * 80)
        logger.info("STEP 6: COMMITTING & PUSHING CHANGES")
        logger.info("-" * 80)

        if not is_repo_dirty(self.git_repo, include_untracked=True):
            logger.warning("No files were modified")
            if not self.dry_mode:
                try:
                    pr.create_issue_comment(
                        "No changes were made. The failures may need manual review."
                    )
                except Exception as e:
                    github_error = get_exception_for_github_error(e, "Failed to post no changes comment")
                    logger.exception(f"Failed to post no changes comment: {github_error}")
                # Track as failed (no changes)
                self.outcome_tracker.update_status(
                    issue_number=pr.number,
                    status=ResolutionStatus.FAILED,
                    error_message="No file changes generated"
                )
                logger.debug("Outcome tracking: Marked as FAILED (no changes)")
            else:
                logger.debug("DRY MODE: Would post no changes comment")
            return False

        # Get list of changed files
        files_modified = get_all_changed_files(self.git_repo)

        logger.info(f"Files modified: {len(files_modified)}")
        for f in files_modified:
            logger.info(f"- {f}")

        # Commit changes
        logger.info("Committing changes...")
        try:
            commit_message = create_commit_message(
                issue_number=pr.number,
                issue_title=f"Fix PR checks: {pr.title}",
                agent_name="PR Failure Resolver Agent"
            )
            commit_changes(self.git_repo, commit_message)
        except BranchError as error:
            logger.exception(f"Failed to commit changes: {error}")
            raise error

        if self.dry_mode:
            logger.debug(f"DRY MODE: Would push branch '{pr.head.ref}' to origin")
            logger.debug("DRY MODE: Would update PR with results")
            logger.info("=" * 80)
            logger.info("DRY MODE: WORKFLOW VALIDATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"SUMMARY (DRY MODE):")
            logger.info(f"PR: #{pr.number} - {pr.title}")
            logger.info(f"Branch: {pr.head.ref}")
            logger.info(f"Files changed: {len(files_modified)}")
            logger.info(f"Status: Would be updated")
            logger.info("=" * 80)
            return True

        # Push
        logger.info(f"Pushing branch '{pr.head.ref}' to origin...")
        try:
            push_branch(self.git_repo, pr.head.ref, remote_name="origin")
        except PushError as error:
            logger.exception(f"Failed to push branch: {error}")
            raise error

        # Track successful fix
        self.outcome_tracker.update_status(
            issue_number=pr.number,
            status=ResolutionStatus.RESOLVED,
            pr_number=pr.number,
            files_changed=len(files_modified)
        )
        logger.debug(f"Outcome tracking: Marked as RESOLVED (PR #{pr.number})")

        # Update PR with retry
        logger.info("Updating PR with results...")

        @retry_github_api
        def update_pr():
            return pr.create_issue_comment(
                f"""**Fixes Applied**

I've pushed fixes to address the failing checks.

**Changes:**
{chr(10).join(['- ' + f for f in files_modified[:10]])}

The CI/CD checks should re-run automatically. Please review the changes.

---
*Completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*"""
            )

        try:
            update_pr()
            logger.info("PR updated")
        except Exception as e:
            github_error = get_exception_for_github_error(e, "Failed to update PR")
            logger.exception(f"Failed to update PR: {github_error}")
            # Don't raise here - changes were pushed successfully

        logger.info("=" * 80)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"SUMMARY:")
        logger.info(f"PR: #{pr.number} - {pr.title}")
        logger.info(f"Branch: {pr.head.ref}")
        logger.info(f"Files changed: {len(files_modified)}")
        logger.info(f"Status: Fixes pushed, awaiting CI/CD re-run")
        logger.info("=" * 80)
        return True
