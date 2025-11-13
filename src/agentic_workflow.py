#!/usr/bin/env python3
"""
Claude Agentic Workflow
LLM-based role workflow for GitHub issue resolution using Claude AI
"""

import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from github import Github, GithubException
from anthropic import Anthropic
import git

from config import AgentConfig
from utils.logger import setup_logger
from utils.project_brief_validator import validate_project_brief
from prompt_loader import PromptLoader


class AgenticWorkflow:
    """Main workflow orchestrator for the Claude agentic system"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        # Load configuration
        self.config = config or AgentConfig.from_env()
        self.config.validate()
        
        # Setup logging
        self.logger = setup_logger()
        
        # Setup paths
        self.workspace = Path(self.config.workspace_path)
        self.repo_path = self.workspace / 'repo'
        
        # Initialize clients
        self.gh = Github(self.config.github_token)
        self.anthropic = Anthropic(api_key=self.config.anthropic_api_key)
        
        # Initialize prompt loader
        self.prompt_loader = PromptLoader()
        
        self.logger.info("Agentic workflow initialized")
        self.logger.info(f"Mode: {self.config.agent_mode}")
        self.logger.info(f"Prompt template: {self.config.prompt_template}")
    
    def _parse_repo_info(self) -> tuple[str, str]:
        """Extract owner and repo name from URL"""
        # Remove protocol and .git suffix
        path = self.config.repo_url.replace('https://github.com/', '')
        path = path.replace('http://github.com/', '')
        path = path.rstrip('.git')
        
        parts = path.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid repository URL: {self.config.repo_url}")
        
        return parts[0], parts[1]
    
    def _clone_repository(self, owner: str, repo_name: str):
        """Clone the target repository"""
        self.logger.info(f"Cloning repository: {owner}/{repo_name}")
        
        # Use token for authentication
        auth_url = f"https://x-access-token:{self.config.github_token}@github.com/{owner}/{repo_name}.git"
        
        git.Repo.clone_from(auth_url, self.repo_path)
        self.logger.info(f"Repository cloned to {self.repo_path}")
    
    def _get_issue(self, owner: str, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get issue details from GitHub"""
        try:
            repo = self.gh.get_repo(f"{owner}/{repo_name}")
            
            # Determine which issue to work on
            if self.config.issue_number:
                issue_num = self.config.issue_number
                self.logger.info(f"Using specified issue #{issue_num}")
            else:
                # Auto-select first open issue
                issues = repo.get_issues(state='open')
                first_issue = next(iter(issues), None)
                
                if not first_issue:
                    self.logger.info("No open issues found in repository")
                    return None
                
                issue_num = first_issue.number
                self.logger.info(f"Auto-selected issue #{issue_num}")
            
            issue = repo.get_issue(issue_num)
            
            return {
                'number': issue.number,
                'title': issue.title,
                'body': issue.body or '',
                'labels': [label.name for label in issue.labels],
                'state': issue.state,
                'url': issue.html_url
            }
            
        except GithubException as e:
            self.logger.error(f"Error fetching issue: {e}")
            raise
    
    def _create_branch(self, issue_number: int) -> str:
        """Create a new branch for the fix"""
        repo = git.Repo(self.repo_path)
        
        branch_name = f"fix/issue-{issue_number}-{int(datetime.now().timestamp())}"
        
        # Create and checkout new branch
        repo.git.checkout('-b', branch_name)
        self.logger.info(f"Created branch: {branch_name}")
        
        return branch_name
    
    def _analyze_codebase(self) -> Dict[str, Any]:
        """Analyze the codebase structure"""
        self.logger.info("Analyzing codebase structure...")
        
        analysis = {
            'languages': set(),
            'frameworks': [],
            'structure': {},
            'key_files': []
        }
        
        # Detect languages and frameworks
        for root, dirs, files in os.walk(self.repo_path):
            # Skip hidden and common ignore directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            for file in files:
                ext = Path(file).suffix
                if ext in ['.py', '.js', '.ts', '.go', '.java', '.rb']:
                    analysis['languages'].add(ext[1:])
                
                # Detect framework files
                if file in ['package.json', 'requirements.txt', 'go.mod', 'pom.xml', 'Gemfile']:
                    analysis['key_files'].append(file)
        
        analysis['languages'] = list(analysis['languages'])
        self.logger.info(f"Detected languages: {', '.join(analysis['languages'])}")
        
        return analysis
    
    def _generate_fix_with_claude(self, issue: Dict[str, Any], codebase_analysis: Dict[str, Any], owner: str, repo_name: str) -> str:
        """Use Claude to generate a fix for the issue"""
        self.logger.info("Generating fix with Claude AI...")
        self.logger.info(f"Using prompt template: {self.config.prompt_template}")
        
        # Build context for prompt template
        context = {
            'repo_owner': owner,
            'repo_name': repo_name,
            'languages': codebase_analysis['languages'],
            'key_files': codebase_analysis['key_files'],
            'issue_number': issue['number'],
            'issue_title': issue['title'],
            'issue_body': issue['body'],
            'issue_labels': issue['labels'],
            'issue_url': issue['url']
        }
        
        # Load and format prompt template
        try:
            template = self.prompt_loader.load_template(
                self.config.prompt_template,
                self.config.custom_prompt_path
            )
            prompt = self.prompt_loader.format_prompt(template, context)
            
            self.logger.info(f"Prompt length: {len(prompt)} characters")
            
        except FileNotFoundError as e:
            self.logger.error(f"Prompt template not found: {e}")
            self.logger.info("Falling back to default template")
            template = self.prompt_loader.load_template('default')
            prompt = self.prompt_loader.format_prompt(template, context)
        
        try:
            message = self.anthropic.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text
            self.logger.info("Claude response received")
            
            return response_text
            
        except Exception as e:
            self.logger.error(f"Error calling Claude API: {e}")
            raise
    
    def _apply_fix(self, fix_response: str) -> bool:
        """Apply the fix suggested by Claude"""
        self.logger.info("Applying fix to codebase...")
        
        try:
            # Try to parse as JSON
            fix_data = json.loads(fix_response)
            
            self.logger.info(f"Analysis: {fix_data.get('analysis', 'N/A')}")
            
            files_modified = []
            for file_change in fix_data.get('files_to_modify', []):
                file_path = self.repo_path / file_change['path']
                
                # Create parent directories if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write the code
                with open(file_path, 'w') as f:
                    f.write(file_change['code'])
                
                files_modified.append(file_change['path'])
                self.logger.info(f"Modified: {file_change['path']}")
            
            if not files_modified:
                self.logger.info("No files were modified")
                return False
            
            return True
            
        except json.JSONDecodeError:
            # If not JSON, treat as general guidance and create a placeholder
            self.logger.info("Response was not JSON, creating documentation of suggested fix")
            
            fix_doc_path = self.repo_path / 'CLAUDE_FIX_SUGGESTION.md'
            with open(fix_doc_path, 'w') as f:
                f.write(f"# Fix Suggestion from Claude AI\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                f.write(fix_response)
            
            self.logger.info(f"Fix suggestion saved to {fix_doc_path}")
            return True
    
    def _commit_and_push(self, issue: Dict[str, Any], branch_name: str):
        """Commit changes and push to GitHub"""
        self.logger.info("Committing and pushing changes...")
        
        repo = git.Repo(self.repo_path)
        
        # Stage all changes
        repo.git.add('-A')
        
        # Check if there are changes
        if not repo.is_dirty() and not repo.untracked_files:
            self.logger.info("No changes to commit")
            return False
        
        # Create commit
        commit_message = f"""Fix: Resolve issue #{issue['number']} - {issue['title']}

Automated fix generated by Claude Agent.

Closes #{issue['number']}
"""
        
        repo.index.commit(commit_message)
        self.logger.info("Changes committed")
        
        # Push to remote
        origin = repo.remote('origin')
        origin.push(branch_name)
        self.logger.info(f"Pushed branch: {branch_name}")
        
        return True
    
    def _create_pull_request(self, owner: str, repo_name: str, issue: Dict[str, Any], branch_name: str):
        """Create a pull request for the fix"""
        self.logger.info("Creating pull request...")
        
        try:
            repo = self.gh.get_repo(f"{owner}/{repo_name}")
            
            pr_title = f"Fix: Resolve issue #{issue['number']} - {issue['title']}"
            
            pr_body = f"""## Automated Fix for Issue #{issue['number']}

This PR was automatically generated by the Claude Agent to resolve issue #{issue['number']}.

### Issue
{issue['title']}

### Changes
The agent analyzed the codebase and implemented a fix for the reported issue using Claude AI.

### Testing
Please review the changes and test thoroughly before merging.

Closes #{issue['number']}

---
*Generated by Claude Agent - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base='main'
            )
            
            self.logger.info(f"Pull request created: {pr.html_url}")
            return pr
            
        except GithubException as e:
            self.logger.error(f"Error creating pull request: {e}")
            raise
    
    def _validate_project_brief(self) -> bool:
        """
        Validate PROJECT_BRIEF.md before AI generation starts

        This validation ensures all required sections are present, preventing
        incomplete briefs and improving AI generation quality.

        Returns:
            True if valid or not found (not required), False if invalid
        """
        project_brief_path = self.repo_path / "PROJECT_BRIEF.md"

        # PROJECT_BRIEF.md is optional - only validate if it exists
        if not project_brief_path.exists():
            self.logger.info("No PROJECT_BRIEF.md found (optional)")
            return True

        self.logger.info("Validating PROJECT_BRIEF.md format and required sections...")
        self.logger.info("This prevents incomplete briefs and ensures quality AI generation.")
        result = validate_project_brief(project_brief_path)

        if result.is_valid:
            self.logger.info("✅ PROJECT_BRIEF.md validation passed - All required sections present")
            if result.warnings:
                self.logger.warning(f"Validation warnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    self.logger.warning(f"  - {warning}")
        else:
            self.logger.error("❌ PROJECT_BRIEF.md validation failed - Incomplete brief detected")
            self.logger.error("Required sections: Overview, Core Features, Technical Requirements, Success Criteria")
            for error in result.errors:
                self.logger.error(f"  - {error}")

            if result.warnings:
                self.logger.warning("Additional warnings:")
                for warning in result.warnings:
                    self.logger.warning(f"  - {warning}")

        return result.is_valid

    def run(self):
        """Execute the complete workflow"""
        self.logger.info("=" * 60)
        self.logger.info("Claude Agentic Workflow Starting")
        self.logger.info("=" * 60)

        try:
            # Parse repository information
            owner, repo_name = self._parse_repo_info()
            self.logger.info(f"Target: {owner}/{repo_name}")

            # Clone repository
            self._clone_repository(owner, repo_name)

            # Validate PROJECT_BRIEF.md if it exists
            # This prevents incomplete briefs and ensures quality AI generation
            if not self._validate_project_brief():
                self.logger.error("\n⚠️  PROJECT_BRIEF.md validation failed!")
                self.logger.error("⚠️  Please ensure all required sections are complete before AI generation.")
                self.logger.error("⚠️  This validation improves generation quality and prevents wasted API calls.")
                return 1
            
            # Get issue details
            issue = self._get_issue(owner, repo_name)
            if not issue:
                self.logger.info("No issue to process")
                return 0
            
            self.logger.info(f"\nIssue #{issue['number']}: {issue['title']}")
            self.logger.info(f"URL: {issue['url']}")
            
            # Create branch
            branch_name = self._create_branch(issue['number'])
            
            # Analyze codebase
            codebase_analysis = self._analyze_codebase()
            
            # Generate fix with Claude
            fix_response = self._generate_fix_with_claude(issue, codebase_analysis, owner, repo_name)
            
            # Apply the fix
            if not self._apply_fix(fix_response):
                self.logger.info("No changes were applied")
                return 1
            
            # Commit and push
            if not self._commit_and_push(issue, branch_name):
                self.logger.info("Nothing to push")
                return 1
            
            # Create pull request
            pr = self._create_pull_request(owner, repo_name, issue, branch_name)
            
            self.logger.info("\n" + "=" * 60)
            self.logger.info("Workflow Completed Successfully!")
            self.logger.info(f"Pull Request: {pr.html_url}")
            self.logger.info("=" * 60)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"\nError during workflow execution: {e}")
            import traceback

# Logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_config import get_logger

logger = get_logger(__name__)

            traceback.print_exc()
            return 1


def main():
    """Main entry point"""
    workflow = AgenticWorkflow()
    exit_code = workflow.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
