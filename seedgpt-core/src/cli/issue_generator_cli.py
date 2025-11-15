#!/usr/bin/env python3
"""
Issue Generator CLI - Main entry point for issue generation

This module contains the CLI logic for running the issue generator agent.
It handles environment configuration, GitHub connection, and error handling.
"""

import os
import sys
from pathlib import Path
from github import Github, Auth

# Add src directory to path if running as script
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.issue_generator import IssueGenerator
from utils.github_helpers import get_repository
from utils.exceptions import (
    MissingEnvironmentVariableError,
    GitHubAPIError,
    CreditBalanceError,
    RateLimitError,
    AuthenticationError,
    AnthropicAPIError,
    get_exception_for_github_error
)
from logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


def main():
    """Main entry point for issue generator CLI"""
    
    # Configuration from environment
    MIN_ISSUES = int(os.getenv('MIN_OPEN_ISSUES', '3'))
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    REPO_NAME = os.getenv('REPO_NAME')
    DRY_MODE = os.getenv('DRY_MODE', 'false').lower() in ('true', '1', 'yes')

    if not GITHUB_TOKEN or not REPO_NAME:
        logger.error("Missing required environment variables", extra={
            "has_github_token": bool(GITHUB_TOKEN),
            "has_repo_name": bool(REPO_NAME)
        })
        raise MissingEnvironmentVariableError("GITHUB_TOKEN or REPO_NAME")

    # Initialize GitHub client with retry using shared utility
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        gh = Github(auth=auth)
        repo = get_repository(gh, REPO_NAME)
        logger.info(f"Connected to repository: {REPO_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to GitHub repository: {REPO_NAME}")
        raise get_exception_for_github_error(e, f"Failed to connect to repository {REPO_NAME}")

    # Run the agent
    try:
        agent = IssueGenerator(
            repo=repo,
            anthropic_api_key=ANTHROPIC_API_KEY,
            min_issues=MIN_ISSUES,
            dry_mode=DRY_MODE
        )

        agent.check_and_generate()
        logger.info("Issue generator completed successfully")

    except CreditBalanceError as e:
        logger.error(
            "❌ Claude CLI credit balance is too low. Please add credits to your Claude account.",
            extra={"error_details": e.details}
        )
        logger.error(f"Error: {e}")
        sys.exit(1)

    except RateLimitError as e:
        logger.error(
            f"❌ {e.service} API rate limit exceeded.",
            extra={
                "service": e.service,
                "retry_after": e.retry_after
            }
        )
        if e.retry_after:
            logger.error(f"Please retry after: {e.retry_after}")
        sys.exit(1)

    except AuthenticationError as e:
        logger.error(
            "❌ Authentication failed. Please check your API credentials.",
            extra={"error_details": e.details}
        )
        logger.error(f"Error: {e}")
        sys.exit(1)

    except AnthropicAPIError as e:
        logger.error(
            "❌ Claude API error occurred.",
            extra={
                "status_code": e.status_code,
                "error_type": e.error_type
            }
        )
        logger.error(f"Error: {e}")
        sys.exit(1)

    except GitHubAPIError as e:
        logger.error(
            "❌ GitHub API error occurred.",
            extra={
                "status_code": e.status_code,
                "response": e.response
            }
        )
        logger.error(f"Error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception("❌ Fatal error in issue generator")
        sys.exit(1)


if __name__ == '__main__':
    main()
