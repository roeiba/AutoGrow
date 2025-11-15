#!/usr/bin/env python3
"""
QA Agent CLI - Main entry point for QA checks

This module contains the CLI logic for running the QA agent.
It handles environment configuration, GitHub connection, and error handling.
"""

import os
import sys
from pathlib import Path
from github import Github, Auth

# Add src directory to path if running as script
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.qa_agent import QAAgent
from utils.retry import retry_github_api
from utils.exceptions import MissingEnvironmentVariableError, get_exception_for_github_error
from logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


def main():
    """Main entry point for QA agent CLI"""
    
    # Configuration from environment
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    REPO_NAME = os.getenv('REPO_NAME')
    MAX_ISSUES_TO_REVIEW = int(os.getenv('MAX_ISSUES_TO_REVIEW', '10'))
    MAX_PRS_TO_REVIEW = int(os.getenv('MAX_PRS_TO_REVIEW', '5'))
    MAX_COMMITS_TO_REVIEW = int(os.getenv('MAX_COMMITS_TO_REVIEW', '10'))

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
        agent = QAAgent(
            repo=repo,
            anthropic_api_key=ANTHROPIC_API_KEY,
            max_issues_to_review=MAX_ISSUES_TO_REVIEW,
            max_prs_to_review=MAX_PRS_TO_REVIEW,
            max_commits_to_review=MAX_COMMITS_TO_REVIEW
        )

        success = agent.run_qa_check()
        logger.info("QA agent completed successfully")

        if not success:
            sys.exit(1)

    except Exception as e:
        logger.exception("Fatal error in QA agent")
        sys.exit(1)


if __name__ == '__main__':
    main()
