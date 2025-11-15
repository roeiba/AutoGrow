"""
GitHub Repository Helper Functions

Centralized utilities for fetching GitHub repository data with retry logic.
"""

from typing import List, Optional
from logging_config import get_logger
from utils.retry import retry_github_api

logger = get_logger(__name__)


@retry_github_api
def get_repository(github_client, repo_full_name: str):
    """
    Get a repository object by full name (owner/repo)
    
    Args:
        github_client: PyGithub Github client object
        repo_full_name: Full repository name in format "owner/repo"
    
    Returns:
        Repository: Repository object
    """
    return github_client.get_repo(repo_full_name)


@retry_github_api
def get_readme(repo, max_length: int = 2000) -> str:
    """
    Get README content from a GitHub repository
    
    Args:
        repo: PyGithub Repository object
        max_length: Maximum length of README to return (default: 2000 chars)
    
    Returns:
        str: README content or "No README found" if not available
    """
    try:
        return repo.get_readme().decoded_content.decode("utf-8")[:max_length]
    except Exception as e:
        logger.warning(f"Failed to fetch README: {e}")
        return "No README found"


@retry_github_api
def get_recent_commits(repo, max_commits: int = 5) -> List:
    """
    Get recent commits from a GitHub repository
    
    Args:
        repo: PyGithub Repository object
        max_commits: Maximum number of commits to fetch (default: 5)
    
    Returns:
        List: List of commit objects
    """
    return list(repo.get_commits()[:max_commits])


@retry_github_api
def get_open_issues(repo, exclude_pull_requests: bool = True) -> List:
    """
    Get open issues from a GitHub repository
    
    Args:
        repo: PyGithub Repository object
        exclude_pull_requests: If True, filter out pull requests (default: True)
    
    Returns:
        List: List of open issue objects
    """
    issues = list(repo.get_issues(state="open"))
    
    if exclude_pull_requests:
        issues = [i for i in issues if not i.pull_request]
    
    return issues


@retry_github_api
def get_open_issues_sorted(repo, sort: str = "created", direction: str = "asc"):
    """
    Get open issues from a GitHub repository with sorting
    
    Args:
        repo: PyGithub Repository object
        sort: Sort field (default: "created")
        direction: Sort direction - "asc" or "desc" (default: "asc")
    
    Returns:
        PaginatedList: Paginated list of open issues
    """
    return repo.get_issues(state="open", sort=sort, direction=direction)


@retry_github_api
def create_issue(repo, title: str, body: str, labels: Optional[List[str]] = None):
    """
    Create a new issue in a GitHub repository
    
    Args:
        repo: PyGithub Repository object
        title: Issue title
        body: Issue body/description
        labels: Optional list of label names
    
    Returns:
        Issue: Created issue object
    """
    return repo.create_issue(title=title, body=body, labels=labels or [])


@retry_github_api
def get_issue(repo, issue_number: int):
    """
    Get a specific issue by number
    
    Args:
        repo: PyGithub Repository object
        issue_number: Issue number to fetch
    
    Returns:
        Issue: Issue object
    """
    return repo.get_issue(issue_number)


@retry_github_api
def get_recent_issues(repo, max_issues: int = 10, state: str = "all", sort: str = "updated", direction: str = "desc") -> List:
    """
    Get recent issues from a GitHub repository
    
    Args:
        repo: PyGithub Repository object
        max_issues: Maximum number of issues to fetch (default: 10)
        state: Issue state - "open", "closed", or "all" (default: "all")
        sort: Sort field (default: "updated")
        direction: Sort direction - "asc" or "desc" (default: "desc")
    
    Returns:
        List: List of recent issue objects
    """
    return list(repo.get_issues(state=state, sort=sort, direction=direction)[:max_issues])


@retry_github_api
def get_repo_info(repo) -> dict:
    """
    Get repository information
    
    Args:
        repo: PyGithub Repository object
    
    Returns:
        dict: Dictionary with repository information
    """
    return {
        "name": repo.name,
        "description": repo.description,
        "open_issues_count": repo.open_issues_count,
        "stargazers_count": repo.stargazers_count,
        "language": repo.language,
    }


@retry_github_api
def get_open_pull_requests_count(repo) -> int:
    """
    Get count of open pull requests in a GitHub repository
    
    Args:
        repo: PyGithub Repository object
    
    Returns:
        int: Number of open pull requests
    """
    return repo.get_pulls(state="open").totalCount


@retry_github_api
def create_pull_request(repo, title: str, body: str, head: str, base: str = "main"):
    """
    Create a pull request in a GitHub repository
    
    Args:
        repo: PyGithub Repository object
        title: PR title
        body: PR body/description
        head: Head branch name
        base: Base branch name (default: "main")
    
    Returns:
        PullRequest: Created pull request object
    """
    # Verify branch exists on remote before creating PR
    try:
        repo.get_branch(head)
    except Exception as e:
        logger.warning(f"Branch {head} not found on remote yet, retrying...")
        raise e
    
    return repo.create_pull(title=title, body=body, head=head, base=base)


@retry_github_api
def get_pull_request(repo, pr_number: int):
    """
    Get a specific pull request by number
    
    Args:
        repo: PyGithub Repository object
        pr_number: PR number to fetch
    
    Returns:
        PullRequest: Pull request object
    """
    return repo.get_pull(pr_number)


@retry_github_api
def get_open_pull_requests(repo):
    """
    Get open pull requests from a GitHub repository
    
    Args:
        repo: PyGithub Repository object
    
    Returns:
        PaginatedList: Paginated list of open pull requests
    """
    return repo.get_pulls(state="open", sort="created", direction="asc")


@retry_github_api
def get_pr_checks(pr):
    """
    Get check runs for a pull request
    
    Args:
        pr: PyGithub PullRequest object
    
    Returns:
        List: List of check run objects
    """
    # Get the latest commit
    commits = list(pr.get_commits())
    if not commits:
        return []
    
    latest_commit = commits[-1]
    
    # Get check runs for the commit
    check_runs = latest_commit.get_check_runs()
    return list(check_runs)


@retry_github_api
def get_pr_files(pr):
    """
    Get files changed in a pull request
    
    Args:
        pr: PyGithub PullRequest object
    
    Returns:
        List: List of file objects
    """
    return list(pr.get_files())


@retry_github_api
def get_pr_comments(pr):
    """
    Get comments on a pull request
    
    Args:
        pr: PyGithub PullRequest object
    
    Returns:
        List: List of issue comment objects
    """
    return list(pr.get_issue_comments())
