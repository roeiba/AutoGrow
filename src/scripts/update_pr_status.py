#!/usr/bin/env python3
"""
Update PR Status - Background job to track PR merge status

This script checks PRs linked to tracked issues and updates their status
when they are merged or closed.

Usage:
    python update_pr_status.py
"""

import os
import sys
import sqlite3
from pathlib import Path
from github import Github
from github.GithubException import GithubException, UnknownObjectException, RateLimitExceededException

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_config import get_logger
from utils.exceptions import (
    MissingEnvironmentVariableError,
    GitHubAPIError,
    RateLimitError,
    AuthenticationError,
)
from utils.outcome_tracker import OutcomeTracker, ResolutionStatus

logger = get_logger(__name__)


def main():
    # Get GitHub token from environment
    github_token = os.environ.get("GITHUB_TOKEN")
    repo_url = os.environ.get("GITHUB_REPOSITORY")

    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        raise MissingEnvironmentVariableError("GITHUB_TOKEN")

    if not repo_url:
        logger.error("GITHUB_REPOSITORY environment variable not set")
        raise MissingEnvironmentVariableError("GITHUB_REPOSITORY")

    logger.info("Updating PR merge status...")
    logger.info(f"Repository: {repo_url}")

    # Initialize GitHub client
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_url)
    except GithubException as e:
        logger.error(f"Failed to initialize GitHub client: {e}")
        if e.status == 401:
            raise AuthenticationError("GitHub authentication failed. Check GITHUB_TOKEN.")
        raise GitHubAPIError(f"GitHub API error: {e}", status_code=e.status)
    except Exception as e:
        logger.error(f"Unexpected error initializing GitHub client: {e}")
        raise

    # Initialize tracker
    tracker = OutcomeTracker()

    # Get all resolved issues that might need status update
    try:
        conn = sqlite3.connect(tracker.db_path)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    # Find all resolved (but not merged/closed) issues with PR numbers
    try:
        cursor.execute("""
            SELECT issue_number, pr_number
            FROM outcomes
            WHERE status = 'resolved'
            AND pr_number IS NOT NULL
            ORDER BY created_at DESC
        """)

        pending_prs = cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Database query failed: {e}")
        raise
    finally:
        conn.close()

    if not pending_prs:
        logger.info("No PRs pending status update")
        return

    logger.info(f"Found {len(pending_prs)} PR(s) to check")

    updated_count = 0
    for issue_number, pr_number in pending_prs:
        try:
            pr = repo.get_pull(pr_number)

            if pr.merged:
                logger.info(f"PR #{pr_number} (Issue #{issue_number}) was merged")
                tracker.update_status(
                    issue_number=issue_number,
                    status=ResolutionStatus.MERGED,
                    pr_number=pr_number
                )
                updated_count += 1
            elif pr.state == "closed":
                logger.info(f"PR #{pr_number} (Issue #{issue_number}) was closed without merge")
                tracker.update_status(
                    issue_number=issue_number,
                    status=ResolutionStatus.CLOSED,
                    pr_number=pr_number
                )
                updated_count += 1

        except UnknownObjectException as e:
            logger.warning(f"PR #{pr_number} not found (may have been deleted): {e}")
            continue
        except RateLimitExceededException as e:
            logger.error(f"GitHub rate limit exceeded while checking PR #{pr_number}: {e}")
            raise RateLimitError("GitHub", retry_after=e.reset.timestamp() if hasattr(e, 'reset') else None)
        except GithubException as e:
            logger.error(f"GitHub API error checking PR #{pr_number}: {e}")
            continue
        except sqlite3.Error as e:
            logger.error(f"Database error updating PR #{pr_number} status: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error checking PR #{pr_number}: {e}", exc_info=True)
            continue

    logger.info(f"Updated {updated_count} PR status(es)")


if __name__ == "__main__":
    main()
