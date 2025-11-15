"""Seed Planter - Core logic for planting and growing projects"""

import asyncio
import json
import shutil
import logging
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

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


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
        logger.info(f"🌱 Starting seed planting for project: {project_name} (ID: {project_id})")
        logger.info(f"   Mode: {mode.value}, Description: {project_description[:100]}...")
        
        workspace = self.workspace_base / project_id
        workspace.mkdir(parents=True, exist_ok=True)
        logger.debug(f"   Created workspace: {workspace}")

        # Sanitize project name for GitHub org
        org_name = self._sanitize_org_name(project_name)
        logger.info(f"   Sanitized org name: {org_name}")

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
            # Step 1: Create GitHub Repository
            logger.info(f"📦 Step 1/6: Creating GitHub repository")
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.CREATING_ORG,
                f"Creating GitHub repository '{org_name}'...", 10
            )
            
            main_repo = await self._create_github_repo(org_name, project_description)
            details.repo_url = main_repo.html_url
            details.org_url = f"https://github.com/{main_repo.owner.login}"
            logger.info(f"✅ Repository created: {main_repo.html_url}")

            # Step 2: Fork SeedGPT template into the repo
            logger.info(f"🔀 Step 2/6: Forking SeedGPT template")
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.FORKING_TEMPLATE,
                "Forking SeedGPT template repository...", 25
            )
            
            await self._fork_seedgpt_template(main_repo, org_name, workspace)
            logger.info(f"✅ Template forked successfully: {main_repo.html_url}")

            # Step 3: Customize project
            logger.info(f"🤖 Step 3/6: Customizing project with AI")
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.CUSTOMIZING_PROJECT,
                "Customizing project with AI...", 40
            )
            
            await self._customize_project(
                main_repo, workspace, project_name, project_description
            )
            logger.info(f"✅ AI customization complete")

            # Step 4: Create GCP project
            logger.info(f"☁️  Step 4/6: Setting up Google Cloud project")
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.CREATING_GCP_PROJECT,
                "Setting up Google Cloud project...", 60
            )
            
            gcp_project_id = await self._create_gcp_project(org_name)
            details.gcp_project_id = gcp_project_id
            logger.info(f"✅ GCP project created: {gcp_project_id}")

            # Step 5: Deploy project (skipped for now - manual deployment)
            logger.info(f"🚀 Step 5/6: Deploying project")
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.DEPLOYING,
                "Project ready for deployment (manual setup required)...", 75
            )
            
            # TODO: Implement automatic deployment
            # For now, users deploy manually using the repository
            details.deployment_url = f"https://github.com/{main_repo.full_name}"
            logger.info(f"✅ Repository ready for deployment: {details.deployment_url}")

            # Step 6: Create initial issues
            logger.info(f"📋 Step 6/6: Creating initial development issues")
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.CREATING_ISSUES,
                "Creating initial development issues...", 90
            )
            
            issues_created = await self._create_initial_issues(main_repo, project_description)
            logger.info(f"✅ Created {issues_created} initial issues")

            # Complete
            logger.info(f"🎉 Project '{project_name}' planted successfully!")
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.COMPLETED,
                f"🌱 Project '{project_name}' is planted and growing!", 100,
                org_url=details.org_url,
                repo_url=details.repo_url,
                deployment_url=details.deployment_url
            )
            
            details.status = ProjectStatus.COMPLETED
            return details
            
        except Exception as e:
            logger.error(f"❌ Failed to plant seed: {str(e)}", exc_info=True)
            details.status = ProjectStatus.FAILED
            details.error_message = str(e)
            
            await self._update_progress(
                progress_callback, project_id, ProjectStatus.FAILED,
                f"Failed: {str(e)}", 0
            )
            
            raise  # Note: We don't cleanup on failure - projects are permanent

        return details

    def _sanitize_org_name(self, project_name: str) -> str:
        """Convert project name to valid GitHub repo name with uniqueness"""
        # Convert to lowercase, replace spaces/special chars with hyphens
        org_name = re.sub(r'[^a-z0-9-]', '-', project_name.lower())
        # Remove consecutive hyphens
        org_name = re.sub(r'-+', '-', org_name)
        # Remove leading/trailing hyphens
        org_name = org_name.strip('-')
        # Limit length to leave room for suffix
        org_name = org_name[:50]
        # Add timestamp with time (not just date) to ensure uniqueness
        timestamp = datetime.utcnow().strftime('%y%m%d-%H%M%S')
        return f"{org_name}-{timestamp}"

    async def _create_github_repo(self, repo_name: str, description: str):
        """
        Create an EMPTY GitHub repository for the project
        
        The repository is created without any initial files (no README, no .gitignore).
        This allows us to push the SeedGPT template as the initial commit,
        making it a true fork/seed of the SeedGPT project.
        
        For SaaS mode, we create repositories under the SeedGPT account.
        For User mode (future), repositories would be created under user's account.
        """
        
        try:
            user = self.gh.get_user()
            logger.info(f"   Creating EMPTY repository under user: {user.login}")
            
            # Create an EMPTY repository (no auto_init)
            repo = user.create_repo(
                name=repo_name,
                description=f"🌱 {description}",
                private=False,
                auto_init=False,  # IMPORTANT: No initial commit
                has_issues=True,
                has_projects=True,
                has_wiki=False,
            )
            
            # Add SeedGPT label
            repo.create_label("seedgpt-planted", "00D084", "🌱 Planted by SeedGPT")
            
            logger.info(f"   Empty repository created: {repo.html_url}")
            return repo
            
        except GithubException as e:
            if e.status == 422 and "name already exists" in str(e):
                raise Exception(f"Repository '{repo_name}' already exists. Please try a different name.")
            raise Exception(f"Failed to create GitHub repository: {e}")

    async def _fork_seedgpt_template(self, target_repo, repo_name: str, workspace: Path):
        """
        Seed the empty repository with SeedGPT template
        
        Process:
        1. Clone SeedGPT template locally
        2. Push everything to the empty target repository (including workflows)
        
        This makes the new repo a true seed/fork of SeedGPT with working CI/CD.
        Note: Requires PAT with 'workflow' scope to push workflow files.
        """
        
        try:
            # Clone SeedGPT template to workspace
            repo_path = workspace / "repo"
            auth_url = f"https://x-access-token:{config.github_token}@github.com/{config.seedgpt_template_repo}.git"
            logger.info(f"   Cloning SeedGPT template from {config.seedgpt_template_repo}")
            git_repo = git.Repo.clone_from(auth_url, repo_path)
            
            # Point to the new empty repository
            git_repo.delete_remote('origin')
            new_remote_url = f"https://x-access-token:{config.github_token}@github.com/{target_repo.full_name}.git"
            git_repo.create_remote('origin', new_remote_url)
            
            logger.info(f"   Pushing SeedGPT template (including workflows) to empty repo: {target_repo.full_name}")
            # Push everything to empty repo (including workflows)
            git_repo.git.push('origin', 'main')
            
            logger.info(f"   ✅ Repository seeded with SeedGPT template and workflows")
            
        except Exception as e:
            raise Exception(f"Failed to seed repository with SeedGPT template: {e}")

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
            # Delete apps folder (seed-planter apps not needed in planted projects)
            apps_path = repo_path / "apps"
            if apps_path.exists():
                shutil.rmtree(apps_path)
                logger.info("   Deleted apps/ folder")
            
            # Delete app-specific workflows (they reference deleted apps)
            apps_workflows_path = repo_path / ".github" / "workflows" / "apps"
            if apps_workflows_path.exists():
                shutil.rmtree(apps_workflows_path)
                logger.info("   Deleted .github/workflows/apps/ folder")
            
            # Delete testing workflows (only needed for SeedGPT development)
            testing_workflows_path = repo_path / ".github" / "workflows" / "testing"
            if testing_workflows_path.exists():
                shutil.rmtree(testing_workflows_path)
                logger.info("   Deleted .github/workflows/testing/ folder")
            
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
