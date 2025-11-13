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

# Import core agent and retry utilities
from agents.issue_resolver import IssueResolver
from utils.retry import retry_github_api

# Configuration from environment
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
REPO_NAME = os.getenv('REPO_NAME')
SPECIFIC_ISSUE = os.getenv('SPECIFIC_ISSUE')
LABELS_TO_HANDLE = os.getenv('ISSUE_LABELS_TO_HANDLE', 'feature,bug,documentation,refactor,test,performance,security,ci/cd,enhancement').split(',')
LABELS_TO_SKIP = os.getenv('ISSUE_LABELS_TO_SKIP', 'wontfix,duplicate,invalid,in-progress').split(',')
MAX_TIME = int(os.getenv('MAX_EXECUTION_TIME', '8')) * 60

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

git_repo = git.Repo('.')

# Run the agent
try:
    agent = IssueResolver(
        repo=repo,
        git_repo=git_repo,
        anthropic_api_key=ANTHROPIC_API_KEY,
        labels_to_handle=LABELS_TO_HANDLE,
        labels_to_skip=LABELS_TO_SKIP,
        max_time=MAX_TIME
    )
    
    specific_issue_num = int(SPECIFIC_ISSUE) if SPECIFIC_ISSUE else None
    agent.resolve_issue(specific_issue=specific_issue_num)
    
except Exception as e:
    print(f"❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
