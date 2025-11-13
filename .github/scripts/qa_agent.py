#!/usr/bin/env python3
"""
QA Agent - GitHub Actions Wrapper

Thin wrapper script for GitHub Actions workflows.
Core logic is in src/agents/qa_agent.py
"""

import os
import sys
from pathlib import Path
from github import Github, Auth

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# Import core agent and retry utilities
from agents.qa_agent import QAAgent
from utils.retry import retry_github_api

# Configuration from environment
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
REPO_NAME = os.getenv('REPO_NAME')
MAX_ISSUES_TO_REVIEW = int(os.getenv('MAX_ISSUES_TO_REVIEW', '10'))
MAX_PRS_TO_REVIEW = int(os.getenv('MAX_PRS_TO_REVIEW', '5'))
MAX_COMMITS_TO_REVIEW = int(os.getenv('MAX_COMMITS_TO_REVIEW', '10'))

if not GITHUB_TOKEN or not REPO_NAME:
    print("❌ Missing required environment variables: GITHUB_TOKEN, REPO_NAME")
    sys.exit(1)

# Initialize GitHub client with retry
@retry_github_api
def initialize_github():
    auth = Auth.Token(GITHUB_TOKEN)
    gh = Github(auth=auth)
    return gh.get_repo(REPO_NAME)

repo = initialize_github()
print(f"✅ Connected to repository: {REPO_NAME}")


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
    
    if not success:
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
