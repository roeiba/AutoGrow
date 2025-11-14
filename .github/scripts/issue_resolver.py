#!/usr/bin/env python3
"""
Issue Resolver Agent - GitHub Actions Wrapper

Thin wrapper script for GitHub Actions workflows.
Core logic is in src/agents/issue_resolver.py
"""

import os
import sys
from pathlib import Path
from github import Github, Auth
import git

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# Import core agent and utilities
from agents.issue_resolver import IssueResolver
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

# Configuration from environment
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
REPO_NAME = os.getenv('REPO_NAME')
SPECIFIC_ISSUE = os.getenv('SPECIFIC_ISSUE')
LABELS_TO_HANDLE = os.getenv('ISSUE_LABELS_TO_HANDLE', 'feature,bug,documentation,refactor,test,performance,security,ci/cd,enhancement').split(',')
LABELS_TO_SKIP = os.getenv('ISSUE_LABELS_TO_SKIP', 'wontfix,duplicate,invalid,in-progress').split(',')
MAX_TIME = int(os.getenv('MAX_EXECUTION_TIME', '8')) * 60
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

git_repo = git.Repo('.')

# Run the agent
try:
    agent = IssueResolver(
        repo=repo,
        git_repo=git_repo,
        anthropic_api_key=ANTHROPIC_API_KEY,
        labels_to_handle=LABELS_TO_HANDLE,
        labels_to_skip=LABELS_TO_SKIP,
        max_time=MAX_TIME,
        dry_mode=DRY_MODE
    )

    specific_issue_num = int(SPECIFIC_ISSUE) if SPECIFIC_ISSUE else None
    agent.resolve_issue(specific_issue=specific_issue_num)
    logger.info("Issue resolver completed successfully")

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
    logger.exception("❌ Fatal error in issue resolver")
    sys.exit(1)
