"""
Git Repository Helper Functions

Centralized utilities for git operations with proper error handling.
"""

from typing import List, Tuple, Optional
import git
from logging_config import get_logger
from utils.exceptions import BranchError, PushError

logger = get_logger(__name__)


def create_branch(git_repo: git.Repo, branch_name: str) -> None:
    """
    Create a new git branch
    
    Args:
        git_repo: GitPython Repo object
        branch_name: Name of the branch to create
        
    Raises:
        BranchError: If branch creation fails
    """
    try:
        git_repo.git.checkout("-b", branch_name)
        logger.info(f"Branch '{branch_name}' created successfully")
    except git.GitCommandError as e:
        error = BranchError(f"Failed to create branch {branch_name}: {e}")
        logger.exception(f"Failed to create branch: {error}")
        raise error


def checkout_branch(git_repo: git.Repo, branch_name: str, remote_name: str = "origin") -> None:
    """
    Checkout an existing branch (fetch from remote if needed)
    
    Args:
        git_repo: GitPython Repo object
        branch_name: Name of the branch to checkout
        remote_name: Name of the remote (default: "origin")
        
    Raises:
        BranchError: If checkout fails
    """
    try:
        # Fetch latest from remote
        origin = git_repo.remote(remote_name)
        origin.fetch()
        
        # Try to checkout the branch
        try:
            git_repo.git.checkout(branch_name)
            logger.info(f"Checked out branch '{branch_name}'")
        except git.GitCommandError:
            # Branch doesn't exist locally, try to create from remote
            git_repo.git.checkout("-b", branch_name, f"{remote_name}/{branch_name}")
            logger.info(f"Checked out branch '{branch_name}' from {remote_name}")
            
    except git.GitCommandError as e:
        error = BranchError(f"Failed to checkout branch {branch_name}: {e}")
        logger.exception(f"Failed to checkout branch: {error}")
        raise error


def is_repo_dirty(git_repo: git.Repo, include_untracked: bool = True) -> bool:
    """
    Check if repository has uncommitted changes
    
    Args:
        git_repo: GitPython Repo object
        include_untracked: Whether to include untracked files in check
        
    Returns:
        bool: True if repository has changes, False otherwise
    """
    return git_repo.is_dirty(untracked_files=include_untracked)


def get_changed_files(git_repo: git.Repo) -> Tuple[List[str], List[str]]:
    """
    Get list of changed and untracked files
    
    Args:
        git_repo: GitPython Repo object
        
    Returns:
        Tuple[List[str], List[str]]: (changed_files, untracked_files)
    """
    changed_files = [item.a_path for item in git_repo.index.diff(None)]
    untracked_files = git_repo.untracked_files
    return changed_files, untracked_files


def commit_changes(git_repo: git.Repo, commit_message: str) -> None:
    """
    Stage all changes and commit
    
    Args:
        git_repo: GitPython Repo object
        commit_message: Commit message
        
    Raises:
        BranchError: If commit fails
    """
    try:
        git_repo.git.add("-A")
        git_repo.index.commit(commit_message)
        logger.info("Changes committed successfully")
    except git.GitCommandError as e:
        error = BranchError(f"Failed to commit changes: {e}")
        logger.exception(f"Failed to commit changes: {error}")
        raise error


def push_branch(git_repo: git.Repo, branch_name: str, remote_name: str = "origin") -> None:
    """
    Push branch to remote repository
    
    Args:
        git_repo: GitPython Repo object
        branch_name: Name of the branch to push
        remote_name: Name of the remote (default: "origin")
        
    Raises:
        PushError: If push fails
    """
    try:
        origin = git_repo.remote(remote_name)
        push_info = origin.push(branch_name)
        
        if push_info and push_info[0].flags & push_info[0].ERROR:
            raise PushError(f"Push failed: {push_info[0].summary}")
            
        logger.info(f"Branch '{branch_name}' pushed to {remote_name} successfully")
    except git.GitCommandError as e:
        error = PushError(f"Failed to push branch: {e}")
        logger.exception(f"Failed to push branch: {error}")
        raise error


def get_all_changed_files(git_repo: git.Repo) -> List[str]:
    """
    Get combined list of all changed and untracked files
    
    Args:
        git_repo: GitPython Repo object
        
    Returns:
        List[str]: List of all file paths that have been modified or added
    """
    changed_files, untracked_files = get_changed_files(git_repo)
    return changed_files + untracked_files


def create_commit_message(issue_number: int, issue_title: str, agent_name: str = "Issue Resolver Agent") -> str:
    """
    Create a standardized commit message for issue resolution
    
    Args:
        issue_number: GitHub issue number
        issue_title: GitHub issue title
        agent_name: Name of the agent creating the commit
        
    Returns:
        str: Formatted commit message
    """
    return f"""Fix: Resolve issue #{issue_number}

{issue_title}

Closes #{issue_number}

---
Generated by {agent_name} using Claude Agent SDK"""
