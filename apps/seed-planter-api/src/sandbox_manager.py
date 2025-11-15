"""Sandbox environment manager"""

import asyncio
import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import uuid

from anthropic import Anthropic
from github import Github, GithubException
import git

from config import config
from models import SandboxStatus, SandboxDetails, SandboxProgress


class SandboxManager:
    """Manages isolated sandbox environments for demos"""

    def __init__(self):
        self.gh = Github(config.github_token)
        self.anthropic = Anthropic(api_key=config.anthropic_api_key)
        self.workspace_base = Path(config.workspace_base_path)
        self.workspace_base.mkdir(parents=True, exist_ok=True)

    async def create_sandbox(
        self, 
        project_idea: str, 
        progress_callback: Optional[callable] = None
    ) -> SandboxDetails:
        """Create a new sandbox environment"""
        
        sandbox_id = str(uuid.uuid4())
        workspace = self.workspace_base / sandbox_id
        workspace.mkdir(parents=True, exist_ok=True)

        details = SandboxDetails(
            sandbox_id=sandbox_id,
            status=SandboxStatus.INITIALIZING,
            project_idea=project_idea,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=config.sandbox_ttl),
        )

        try:
            # Step 1: Create GitHub repository
            await self._update_progress(
                progress_callback, sandbox_id, SandboxStatus.CREATING_REPO,
                "Creating temporary GitHub repository...", 10
            )
            
            repo = await self._create_github_repo(sandbox_id, project_idea)
            details.repo_url = repo.html_url
            details.repo_name = repo.name

            # Step 2: Generate project structure
            await self._update_progress(
                progress_callback, sandbox_id, SandboxStatus.GENERATING_STRUCTURE,
                "Generating project structure with AI...", 30
            )
            
            structure = await self._generate_project_structure(project_idea, workspace)
            await self._push_initial_structure(repo, workspace)

            # Step 3: Create issues
            await self._update_progress(
                progress_callback, sandbox_id, SandboxStatus.CREATING_ISSUES,
                "Creating initial issues...", 60
            )
            
            issues = await self._create_initial_issues(repo, project_idea)
            details.issues_created = len(issues)
            
            if issues:
                details.issue_url = issues[0].html_url

            # Step 4: Create first PR
            await self._update_progress(
                progress_callback, sandbox_id, SandboxStatus.CREATING_PR,
                "Creating first pull request...", 80
            )
            
            pr = await self._create_first_pr(repo, workspace, issues[0] if issues else None)
            if pr:
                details.pr_created = True
                details.pr_url = pr.html_url

            # Complete
            await self._update_progress(
                progress_callback, sandbox_id, SandboxStatus.COMPLETED,
                "Sandbox ready! Explore your demo project.", 100,
                repo_url=details.repo_url, pr_url=details.pr_url
            )
            
            details.status = SandboxStatus.COMPLETED

        except Exception as e:
            details.status = SandboxStatus.FAILED
            details.error_message = str(e)
            
            await self._update_progress(
                progress_callback, sandbox_id, SandboxStatus.FAILED,
                f"Failed: {str(e)}", 0
            )
            
            # Cleanup on failure
            await self._cleanup_sandbox(sandbox_id, details.repo_name)

        return details

    async def _create_github_repo(self, sandbox_id: str, project_idea: str):
        """Create a temporary GitHub repository"""
        
        # Generate repo name from project idea
        repo_name = f"demo-{sandbox_id[:8]}"
        
        try:
            if config.github_org:
                org = self.gh.get_organization(config.github_org)
                repo = org.create_repo(
                    name=repo_name,
                    description=f"AutoGrow Demo: {project_idea[:100]}",
                    private=False,
                    auto_init=True,
                )
            else:
                user = self.gh.get_user()
                repo = user.create_repo(
                    name=repo_name,
                    description=f"AutoGrow Demo: {project_idea[:100]}",
                    private=False,
                    auto_init=True,
                )
            
            # Add sandbox label
            repo.create_label("sandbox-demo", "FFA500", "Temporary demo repository")
            
            return repo
            
        except GithubException as e:
            raise Exception(f"Failed to create GitHub repository: {e}")

    async def _generate_project_structure(self, project_idea: str, workspace: Path) -> dict:
        """Use Claude to generate initial project structure"""
        
        prompt = f"""Generate a minimal but functional project structure for this idea:

Project Idea: {project_idea}

Create:
1. README.md with project overview
2. PROJECT_BRIEF.md following the SeedGPT format
3. Basic directory structure
4. A simple implementation file

Return as JSON with this structure:
{{
    "files": [
        {{"path": "README.md", "content": "..."}},
        {{"path": "PROJECT_BRIEF.md", "content": "..."}}
    ]
}}"""

        try:
            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            
            # Extract JSON from response
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text
            
            structure = json.loads(json_str)
            
            # Write files to workspace
            for file_info in structure.get("files", []):
                file_path = workspace / file_info["path"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_info["content"])
            
            return structure
            
        except Exception as e:
            # Fallback: create basic structure
            readme = workspace / "README.md"
            readme.write_text(f"# {project_idea}\n\nAutoGrow Demo Project\n")
            
            brief = workspace / "PROJECT_BRIEF.md"
            brief.write_text(f"""## 🎯 Project Overview

**Project Name**: Demo Project

**Goal**: {project_idea}

**Brief Description**: 
This is a demo project generated by AutoGrow to showcase AI-driven development.
""")
            
            return {"files": [{"path": "README.md"}, {"path": "PROJECT_BRIEF.md"}]}

    async def _push_initial_structure(self, repo, workspace: Path):
        """Push initial structure to GitHub"""
        
        try:
            # Clone the repo
            repo_path = workspace / "repo"
            auth_url = f"https://x-access-token:{config.github_token}@github.com/{repo.full_name}.git"
            git_repo = git.Repo.clone_from(auth_url, repo_path)
            
            # Copy files
            for file in workspace.iterdir():
                if file.name != "repo" and file.is_file():
                    shutil.copy(file, repo_path / file.name)
            
            # Commit and push
            git_repo.git.add("-A")
            git_repo.index.commit("Initial project structure generated by AutoGrow")
            git_repo.remote("origin").push("main")
            
        except Exception as e:
            raise Exception(f"Failed to push initial structure: {e}")

    async def _create_initial_issues(self, repo, project_idea: str) -> list:
        """Create initial issues for the project"""
        
        issues = []
        
        try:
            # Create a few starter issues
            issue_templates = [
                {
                    "title": "Setup development environment",
                    "body": f"Initialize development environment for: {project_idea}\n\n- [ ] Setup dependencies\n- [ ] Configure tooling\n- [ ] Add documentation",
                    "labels": ["enhancement", "good first issue"]
                },
                {
                    "title": "Implement core functionality",
                    "body": f"Build the main features for this project.\n\nProject goal: {project_idea}",
                    "labels": ["enhancement"]
                },
            ]
            
            for template in issue_templates:
                issue = repo.create_issue(
                    title=template["title"],
                    body=template["body"],
                    labels=template["labels"]
                )
                issues.append(issue)
                
        except Exception as e:
            # Non-critical, continue
            pass
        
        return issues

    async def _create_first_pr(self, repo, workspace: Path, issue=None):
        """Create a demonstration PR"""
        
        try:
            repo_path = workspace / "repo"
            git_repo = git.Repo(repo_path)
            
            # Create a new branch
            branch_name = "feature/initial-setup"
            git_repo.git.checkout("-b", branch_name)
            
            # Add a simple change
            contributing = repo_path / "CONTRIBUTING.md"
            contributing.write_text("""# Contributing

Thank you for your interest in contributing to this AutoGrow demo project!

## Getting Started
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
""")
            
            git_repo.git.add("-A")
            git_repo.index.commit("Add contributing guidelines")
            git_repo.remote("origin").push(branch_name)
            
            # Create PR
            pr_body = "Initial setup for the project.\n\n"
            if issue:
                pr_body += f"Addresses #{issue.number}"
            
            pr = repo.create_pull(
                title="Initial project setup",
                body=pr_body,
                head=branch_name,
                base="main"
            )
            
            return pr
            
        except Exception as e:
            # Non-critical
            return None

    async def _update_progress(
        self, 
        callback: Optional[callable],
        sandbox_id: str,
        status: SandboxStatus,
        message: str,
        progress: int,
        **kwargs
    ):
        """Send progress update via callback"""
        
        if callback:
            progress_data = SandboxProgress(
                sandbox_id=sandbox_id,
                status=status,
                message=message,
                progress_percent=progress,
                timestamp=datetime.utcnow(),
                **kwargs
            )
            await callback(progress_data)

    async def _cleanup_sandbox(self, sandbox_id: str, repo_name: Optional[str] = None):
        """Clean up sandbox resources"""
        
        # Remove workspace
        workspace = self.workspace_base / sandbox_id
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
        
        # Optionally delete GitHub repo (for now, keep it for demo purposes)
        # if repo_name:
        #     try:
        #         repo = self.gh.get_repo(f"{config.github_org or self.gh.get_user().login}/{repo_name}")
        #         repo.delete()
        #     except:
        #         pass

    async def get_sandbox_details(self, sandbox_id: str) -> Optional[SandboxDetails]:
        """Get details for a specific sandbox"""
        # This would typically query Redis or a database
        # For now, return None as we'll implement storage next
        return None

    async def list_active_sandboxes(self) -> list[SandboxDetails]:
        """List all active sandboxes"""
        # This would typically query Redis or a database
        return []
