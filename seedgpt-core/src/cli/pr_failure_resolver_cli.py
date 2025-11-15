#!/usr/bin/env python3
"""
PR Failure Resolver CLI - Main entry point for PR failure resolution

This module contains the CLI logic for running the PR failure resolver agent.
It handles environment configuration, GitHub connection, and error handling.
"""

import os
import sys
from pathlib import Path

# Add src directory to path if running as script
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from github import Github, Auth
    import git
    print("✅ External dependencies imported successfully")
except ImportError as e:
    print(f"❌ Failed to import external dependencies: {e}")
    sys.exit(1)

from agents.pr_failure_resolver import PRFailureResolver
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
    """Main entry point for PR failure resolver CLI"""
    
    print(f"🔍 Python path configured:")
    print(f"   Python version: {sys.version}")
    
    # Configuration from environment
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    REPO_NAME = os.getenv('REPO_NAME')
    SPECIFIC_PR = os.getenv('SPECIFIC_PR')
    
    MAX_TIME = int(os.getenv('MAX_EXECUTION_TIME', '8')) * 60
    DRY_MODE = os.getenv('DRY_MODE', 'false').lower() in ('true', '1', 'yes')

    if not GITHUB_TOKEN or not REPO_NAME:
        print("\n" + "="*80)
        print("⏭️  SKIPPING: PR Failure Resolver Agent")
        print("="*80)
        print("\n📋 This workflow requires the following environment variables:")
        print("   • GITHUB_TOKEN - GitHub API access token")
        print("   • REPO_NAME - Repository name (owner/repo)")
        print("\n💡 These are typically not available in forked repositories.")
        print("   This is expected behavior and not an error.")
        print("\n🔒 Repository owners can configure these secrets in:")
        print("   Settings → Secrets and variables → Actions")
        print("="*80 + "\n")
        logger.info("Skipping execution due to missing environment variables (expected in forks)")
        sys.exit(0)

    # Initialize GitHub client with retry using shared utility
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        gh = Github(auth=auth)
        repo = get_repository(gh, REPO_NAME)
        logger.info(f"Connected to repository: {REPO_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to GitHub repository: {REPO_NAME}")
        raise get_exception_for_github_error(e, f"Failed to connect to repository {REPO_NAME}")

    git_repo = git.Repo('.')

    # Run the agent
    try:
        agent = PRFailureResolver(
            repo=repo,
            git_repo=git_repo,
            anthropic_api_key=ANTHROPIC_API_KEY,
            max_time=MAX_TIME,
            dry_mode=DRY_MODE
        )

        specific_pr_num = int(SPECIFIC_PR) if SPECIFIC_PR else None
        agent.resolve_pr_failure(specific_pr=specific_pr_num)
        logger.info("PR failure resolver completed successfully")

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
        logger.exception("❌ Fatal error in PR failure resolver")
        sys.exit(1)


if __name__ == '__main__':
    main()
