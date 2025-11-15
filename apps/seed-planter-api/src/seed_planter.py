"""Seed Planter - Core logic for planting and growing projects"""

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid
import re

from anthropic import Anthropic
from github import Github, GithubException
import git

from config import config
from models import ProjectStatus, ProjectDetails, ProjectProgress, DeploymentType, ProjectMode


class SeedPlanter:
    """Manages planting and growing of autonomous projects"""

    def __init__(self):
        self.gh = Github(config.github_token)
        self.anthropic = Anthropic(api_key=config.anthropic_api_key)
        self.workspace_base = Path(config.workspace_base_path)
        self.workspace_base.mkdir(parents=True, exist_ok=True)

    async def plant_seed(
        self, 
        project_name: str,
        project_description: str,
        mode: ProjectMode = ProjectMode.SAAS,
        user_email: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> ProjectDetails:
        """Plant a new project seed and watch it grow"""
        
        project_id = str(uuid.uuid4())
        workspace = self.workspace_base / project_id
        workspace.mkdir(parents=True, exist_ok=True)

        # Sanitize project name for GitHub org
        org_name = self._sanitize_org_name(project_name)

        details = ProjectDetails(
            project_id=project_id,
            project_name=project_name,
            status=ProjectStatus.INITIALIZING,
            project_description=project_description,
            created_at=datetime.utcnow(),
            mode=mode,
            org_name=org_name,
            owner_email=user_email,
        )

        try:
            # Step 1: Create GitHub Organization
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.CREATING_ORG,
                f"Creating GitHub organization '{org_name}'...", 10
            )
            
            org = await self._create_github_org(org_name, project_description)
            details.org_url = f"https://github.com/{org_name}"

            # Step 2: Fork SeedGPT template
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.FORKING_TEMPLATE,
                "Forking SeedGPT template repository...", 25
            )
            
            repo = await self._fork_seedgpt_template(org, org_name, workspace)
            details.repo_url = repo.html_url

            # Step 3: Customize project
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.CUSTOMIZING_PROJECT,
                "Customizing project with AI...", 40
            )
            
            await self._customize_project(
                repo, workspace, project_name, project_description
            )

            # Step 4: Create GCP project
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.CREATING_GCP_PROJECT,
                "Setting up Google Cloud project...", 60
            )
            
            gcp_project_id = await self._create_gcp_project(org_name)
            details.gcp_project_id = gcp_project_id

            # Step 5: Determine deployment type and deploy
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.DEPLOYING,
                "Analyzing and deploying project...", 75
            )
            
            deployment_type, deployment_url = await self._deploy_project(
                repo, workspace, gcp_project_id, project_description
            )
            details.deployment_type = deployment_type
            details.deployment_url = deployment_url
            details.is_deployed = deployment_url is not None

            # Step 6: Create initial issues
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.CREATING_ISSUES,
                "Creating initial development issues...", 90
            )
            
            issues_count = await self._create_initial_issues(repo, project_description)
            details.issues_created = issues_count

            # Complete
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.COMPLETED,
                f"🌱 Project '{project_name}' is planted and growing!", 100,
                org_url=details.org_url,
                repo_url=details.repo_url,
                deployment_url=deployment_url,
                gcp_project_id=gcp_project_id
            )
            
            details.status = ProjectStatus.COMPLETED

        except Exception as e:
            details.status = ProjectStatus.FAILED
            details.error_message = str(e)
            
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.FAILED,
                f"Failed: {str(e)}", 0
            )
            
            # Note: We don't cleanup on failure - projects are permanent

        return details

    def _sanitize_org_name(self, project_name: str) -> str:
        """Convert project name to valid GitHub org name"""
        # Convert to lowercase, replace spaces/special chars with hyphens
        org_name = re.sub(r'[^a-z0-9-]', '-', project_name.lower())
        # Remove consecutive hyphens
        org_name = re.sub(r'-+', '-', org_name)
        # Remove leading/trailing hyphens
        org_name = org_name.strip('-')
        # Add timestamp suffix to ensure uniqueness
        timestamp = datetime.utcnow().strftime('%y%m%d')
        return f"{org_name}-{timestamp}"

    async def _create_github_org(self, org_name: str, description: str):
        """Create a GitHub organization for the project"""
        
        try:
            # Note: GitHub API doesn't support org creation via API for regular users
            # For SaaS mode, we'll create repos under the user account with org-like naming
            # In production, this would use GitHub Apps or manual org creation
            
            # For now, we'll simulate by creating a repo that acts as the org
            user = self.gh.get_user()
            
            # Create a "meta" repository for the organization
            org_repo = user.create_repo(
                name=org_name,
                description=f"🌱 {description}",
                private=False,
                auto_init=True,
            )
            
            # Add organization label
            org_repo.create_label("seedgpt-project", "00D084", "SeedGPT planted project")
            
            return org_repo
            
        except GithubException as e:
            raise Exception(f"Failed to create GitHub organization: {e}")

    async def _fork_seedgpt_template(self, org, org_name: str, workspace: Path):
        """Fork SeedGPT template repository"""
        
        try:
            # Get the template repository
            template_repo = self.gh.get_repo(config.seedgpt_template_repo)
            
            # Clone template to workspace
            repo_path = workspace / "repo"
            auth_url = f"https://x-access-token:{config.github_token}@github.com/{config.seedgpt_template_repo}.git"
            git_repo = git.Repo.clone_from(auth_url, repo_path)
            
            # Create new repo under user account (simulating org)
            user = self.gh.get_user()
            new_repo = user.create_repo(
                name=f"{org_name}-main",
                description=f"Main repository for {org_name}",
                private=False,
            )
            
            # Change remote and push
            git_repo.delete_remote('origin')
            new_remote_url = f"https://x-access-token:{config.github_token}@github.com/{new_repo.full_name}.git"
            git_repo.create_remote('origin', new_remote_url)
            
            # Push all branches
            git_repo.git.push('origin', '--all')
            
            return new_repo
            
        except Exception as e:
            raise Exception(f"Failed to fork SeedGPT template: {e}")

    async def _customize_project(
        self, 
        repo, 
        workspace: Path, 
        project_name: str, 
        project_description: str
    ):
        """Customize the forked project with AI"""
        
        repo_path = workspace / "repo"
        
        try:
            # Delete apps folder
            apps_path = repo_path / "apps"
            if apps_path.exists():
                shutil.rmtree(apps_path)
            
            # Generate customized PROJECT_BRIEF.md
            brief_content = await self._generate_project_brief(project_name, project_description)
            brief_path = repo_path / "PROJECT_BRIEF.md"
            brief_path.write_text(brief_content)
            
            # Generate customized README.md
            readme_content = await self._generate_readme(project_name, project_description)
            readme_path = repo_path / "README.md"
            readme_path.write_text(readme_content)
            
            # Commit changes
            git_repo = git.Repo(repo_path)
            git_repo.git.add("-A")
            git_repo.index.commit(f"Customize project: {project_name}")
            git_repo.remote("origin").push("main")
            
        except Exception as e:
            raise Exception(f"Failed to customize project: {e}")

    async def _generate_project_brief(self, project_name: str, description: str) -> str:
        """Use Claude to generate PROJECT_BRIEF.md"""
        
        prompt = f"""Generate a PROJECT_BRIEF.md file for this project following the SeedGPT format.

Project Name: {project_name}
Description: {description}

Create a comprehensive project brief with:
- Project Overview
- Problem Statement
- Target Users
- Proposed Solution
- Business Model
- Technical Details

Format it exactly like a professional PROJECT_BRIEF.md file."""

        try:
            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
            
        except Exception:
            # Fallback template
            return f"""## 🎯 Project Overview

**Project Name**: {project_name}

**Goal**: {description}

**Brief Description**: 
This project was planted by SeedGPT and will grow autonomously with AI-driven development.

**Problem Statement**:
To be defined based on project evolution.

**Target Users**:
To be identified as the project grows.

**Proposed Solution**:
{description}

**Business Model**:
To be developed.

**Technical Details**:
This is a SeedGPT-planted project using autonomous AI agents for development.
"""

    async def _generate_readme(self, project_name: str, description: str) -> str:
        """Generate README.md"""
        
        return f"""# {project_name}

{description}

## 🌱 Planted by SeedGPT

This project was created and is maintained by [SeedGPT](https://github.com/roeiba/SeedGPT) - an autonomous AI-driven development platform.

## About

This project grows autonomously using AI agents that:
- Generate and resolve issues
- Write and review code
- Deploy and maintain infrastructure
- Evolve based on requirements

## Getting Started

Check the [PROJECT_BRIEF.md](./PROJECT_BRIEF.md) for detailed information.

## Development

This project uses SeedGPT's autonomous workflow. Issues are automatically generated and resolved by AI agents.

---

*🤖 Autonomously maintained by SeedGPT*
"""

    async def _create_gcp_project(self, org_name: str) -> str:
        """Create Google Cloud project"""
        
        # For Phase 1, we'll use a simplified approach
        # In production, this would use GCP SDK to create actual projects
        
        # Generate GCP project ID (must be globally unique)
        gcp_project_id = f"seedgpt-{org_name}"[:30]  # GCP has 30 char limit
        
        # TODO: Implement actual GCP project creation using google-cloud-resource-manager
        # For now, return the ID that would be created
        
        return gcp_project_id

    async def _deploy_project(
        self, 
        repo, 
        workspace: Path, 
        gcp_project_id: str,
        description: str
    ) -> tuple[DeploymentType, Optional[str]]:
        """Determine deployment type and deploy"""
        
        repo_path = workspace / "repo"
        
        # Analyze project to determine deployment type
        is_simple_page = await self._is_simple_page_app(repo_path, description)
        
        if is_simple_page:
            # Deploy to GitHub Pages
            deployment_url = await self._deploy_github_pages(repo)
            return DeploymentType.GITHUB_PAGES, deployment_url
        else:
            # Deploy to GCP with Docker
            deployment_url = await self._deploy_docker_gcp(repo, gcp_project_id)
            return DeploymentType.DOCKER_GCP, deployment_url

    async def _is_simple_page_app(self, repo_path: Path, description: str) -> bool:
        """Determine if project can use GitHub Pages"""
        
        # Check for static site indicators
        has_html = list(repo_path.glob("**/*.html"))
        has_index = (repo_path / "index.html").exists()
        
        # Use AI to analyze
        prompt = f"""Is this a simple static website that can be hosted on GitHub Pages?

Description: {description}
Has HTML files: {len(has_html) > 0}
Has index.html: {has_index}

Answer with just 'yes' or 'no'."""

        try:
            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = message.content[0].text.strip().lower()
            return answer == 'yes'
            
        except Exception:
            # Default: if has index.html, use GitHub Pages
            return has_index

    async def _deploy_github_pages(self, repo) -> Optional[str]:
        """Deploy to GitHub Pages"""
        
        try:
            # Enable GitHub Pages
            repo.create_pages_site(
                source={"branch": "main", "path": "/"}
            )
            
            # Return GitHub Pages URL
            return f"https://{repo.owner.login}.github.io/{repo.name}"
            
        except Exception as e:
            # Pages might already be enabled or not available
            return None

    async def _deploy_docker_gcp(self, repo, gcp_project_id: str) -> Optional[str]:
        """Deploy to GCP using Docker and Cloud Run"""
        
        # TODO: Implement actual GCP deployment
        # This would:
        # 1. Build Docker images for each service
        # 2. Push to GCR (Google Container Registry)
        # 3. Deploy to Cloud Run with min_instances=0
        # 4. Return the Cloud Run URL
        
        # For now, return placeholder
        return f"https://{gcp_project_id}.run.app"

    async def _create_initial_issues(self, repo, description: str) -> int:
        """Create initial development issues"""
        
        issues_created = 0
        
        try:
            # Use AI to generate relevant issues
            prompt = f"""Generate 3-5 initial development issues for this project:

{description}

Return as JSON array with format:
[
  {{"title": "Issue title", "body": "Issue description", "labels": ["label1", "label2"]}}
]"""

            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            
            # Extract JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text
            
            issues_data = json.loads(json_str)
            
            # Create issues
            for issue_data in issues_data:
                repo.create_issue(
                    title=issue_data["title"],
                    body=issue_data["body"],
                    labels=issue_data.get("labels", [])
                )
                issues_created += 1
                
        except Exception:
            # Fallback: create basic issues
            basic_issues = [
                {
                    "title": "Setup development environment",
                    "body": "Initialize development environment and dependencies",
                    "labels": ["setup", "good first issue"]
                },
                {
                    "title": "Implement core functionality",
                    "body": f"Build the main features: {description}",
                    "labels": ["enhancement"]
                },
            ]
            
            for issue_data in basic_issues:
                repo.create_issue(
                    title=issue_data["title"],
                    body=issue_data["body"],
                    labels=issue_data["labels"]
                )
                issues_created += 1
        
        return issues_created

    async def _update_progress(
        self, 
        callback: Optional[callable],
        project_id: str,
        status: ProjectStatus,
        message: str,
        progress: int,
        **kwargs
    ):
        """Send progress update via callback"""
        
        print(f"📊 Progress Update [{project_id}]: {status.value} - {message} ({progress}%)")
        
        if callback:
            progress_data = ProjectProgress(
                project_id=project_id,
                status=status,
                message=message,
                progress_percent=progress,
                timestamp=datetime.utcnow(),
                **kwargs
            )
            await callback(progress_data)
        else:
            print(f"⚠️  No callback provided for progress update")

    async def get_project_details(self, project_id: str) -> Optional[ProjectDetails]:
        """Get details for a specific project"""
        # This would typically query a database
        # For now, return None as we'll implement storage next
        return None

    async def list_projects(self) -> list[ProjectDetails]:
        """List all planted projects"""
        # This would typically query a database
        return []

    async def transfer_ownership(self, project_id: str, new_owner_github: str) -> bool:
        """Transfer project ownership to user"""
        # TODO: Implement ownership transfer
        # This would transfer the GitHub org/repo to the user
        return False
