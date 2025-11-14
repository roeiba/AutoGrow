#!/usr/bin/env python3
"""
Issue Generator Agent - GitHub Actions Wrapper

Thin wrapper script for GitHub Actions workflows.
Core logic is in src/agents/issue_generator.py
"""

import os
import sys
from pathlib import Path
from github import Github, Auth

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# Import core agent, retry utilities, and exceptions
from agents.issue_generator import IssueGenerator
from utils.retry import retry_github_api
from utils.exceptions import MissingEnvironmentVariableError, GitHubAPIError, get_exception_for_github_error
from logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

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

# Initialize GitHub client with retry
@retry_github_api
def initialize_github():
    auth = Auth.Token(GITHUB_TOKEN)
    gh = Github(auth=auth)
    return gh.get_repo(REPO_NAME)

try:
    repo = initialize_github()
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

except Exception as e:
    logger.exception("Fatal error in issue generator")
    sys.exit(1)
