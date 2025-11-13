#!/usr/bin/env python3
"""
QA Agent - Core Logic

Monitors repository health by reviewing issues, PRs, and commits
Reports problems by creating issues
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "claude-agent"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import model configuration
from models_config import CLAUDE_MODELS, SystemPrompts
from utils.retry import retry_anthropic_api, retry_github_api

# Import Claude CLI Agent or fallback to Anthropic SDK
try:
    from claude_cli_agent import ClaudeAgent

    USE_CLAUDE_CLI = True
except ImportError:
    USE_CLAUDE_CLI = False
    try:
        from anthropic import Anthropic
    except ImportError:
        print("❌ Neither claude_cli_agent nor anthropic SDK available")
        raise


class QAAgent:
    """QA Agent for monitoring repository health"""

    def __init__(
        self,
        repo,
        anthropic_api_key: Optional[str] = None,
        max_issues_to_review: int = 10,
        max_prs_to_review: int = 5,
        max_commits_to_review: int = 10,
    ):
        """
        Initialize the QA Agent

        Args:
            repo: PyGithub Repository object
            anthropic_api_key: Anthropic API key (required if not using Claude CLI)
            max_issues_to_review: Maximum number of issues to review
            max_prs_to_review: Maximum number of PRs to review
            max_commits_to_review: Maximum number of commits to review
        """
        self.repo = repo
        self.anthropic_api_key = anthropic_api_key
        self.max_issues = max_issues_to_review
        self.max_prs = max_prs_to_review
        self.max_commits = max_commits_to_review

        print("🔍 QA Agent Initialized")
        print(
            f"📊 Will review: {self.max_issues} issues, {self.max_prs} PRs, {self.max_commits} commits"
        )

    def run_qa_check(self) -> bool:
        """
        Run QA check on repository

        Returns:
            bool: True if check completed successfully
        """
        # Gather context
        context = self._gather_repository_context()

        # Run analysis
        response = self._run_qa_analysis(context)

        if not response:
            print("\n❌ QA Agent failed to get analysis")
            return False

        # Parse and act on results
        success = self._parse_and_act_on_results(response)

        if success:
            print("\n🎉 QA Agent completed successfully")

        return success

    def _gather_repository_context(self) -> Dict:
        """Gather context about recent repository activity"""
        print("📖 Gathering repository context...")

        context = {"issues": [], "pull_requests": [], "commits": [], "repo_info": {}}

        # Get repository info with retry
        @retry_github_api
        def get_repo_info():
            return {
                "name": self.repo.name,
                "description": self.repo.description,
                "open_issues_count": self.repo.open_issues_count,
                "stargazers_count": self.repo.stargazers_count,
                "language": self.repo.language,
            }

        context["repo_info"] = get_repo_info()

        # Get recent issues with retry
        @retry_github_api
        def get_issues():
            return list(
                self.repo.get_issues(state="all", sort="updated", direction="desc")
            )[: self.max_issues]

        print(f"📋 Reviewing {self.max_issues} recent issues...")
        issues = get_issues()
        for issue in issues:
            if issue.pull_request:
                continue
            context["issues"].append(
                {
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "labels": [label.name for label in issue.labels],
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat(),
                    "body": (issue.body or "")[:500],
                }
            )

        # Get recent pull requests with retry
        @retry_github_api
        def get_prs():
            return list(self.repo.get_pulls(state="all", sort="updated", direction="desc"))[
                : self.max_prs
            ]

        print(f"🔀 Reviewing {self.max_prs} recent pull requests...")
        prs = get_prs()
        for pr in prs:
            context["pull_requests"].append(
                {
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "merged": pr.merged,
                    "created_at": pr.created_at.isoformat(),
                    "updated_at": pr.updated_at.isoformat(),
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files,
                }
            )

        # Get recent commits with retry
        @retry_github_api
        def get_commits():
            return list(self.repo.get_commits())[: self.max_commits]

        print(f"📝 Reviewing {self.max_commits} recent commits...")
        commits = get_commits()
        for commit in commits:
            context["commits"].append(
                {
                    "sha": commit.sha[:8],
                    "message": commit.commit.message.split("\n")[0][:100],
                    "author": commit.commit.author.name,
                    "date": commit.commit.author.date.isoformat(),
                    "files_changed": len(list(commit.files)) if commit.files else 0,
                }
            )

        print(
            f"✅ Gathered context: {len(context['issues'])} issues, {len(context['pull_requests'])} PRs, {len(context['commits'])} commits"
        )
        return context

    def _build_qa_prompt(self, context: Dict) -> str:
        """Build the QA analysis prompt"""
        prompt = f"""You are a QA engineer reviewing the AutoGrow repository: {self.repo.full_name}

Your job is to analyze recent activity and identify any problems, inconsistencies, or areas of concern.

## Repository Overview
- Name: {context['repo_info']['name']}
- Description: {context['repo_info']['description']}
- Open Issues: {context['repo_info']['open_issues_count']}
- Language: {context['repo_info']['language']}

## Recent Issues ({len(context['issues'])})
"""

        for issue in context["issues"]:
            prompt += f"\n### Issue #{issue['number']}: {issue['title']}\n"
            prompt += f"- State: {issue['state']}\n"
            prompt += f"- Labels: {', '.join(issue['labels'])}\n"
            prompt += f"- Created: {issue['created_at']}\n"
            if issue["body"]:
                prompt += f"- Description: {issue['body'][:200]}...\n"

        prompt += f"\n## Recent Pull Requests ({len(context['pull_requests'])})\n"
        for pr in context["pull_requests"]:
            prompt += f"\n### PR #{pr['number']}: {pr['title']}\n"
            prompt += f"- State: {pr['state']}, Merged: {pr['merged']}\n"
            prompt += f"- Changes: +{pr['additions']} -{pr['deletions']} in {pr['changed_files']} files\n"
            prompt += f"- Updated: {pr['updated_at']}\n"

        prompt += f"\n## Recent Commits ({len(context['commits'])})\n"
        for commit in context["commits"]:
            prompt += f"- [{commit['sha']}] {commit['message']} by {commit['author']} ({commit['files_changed']} files)\n"

        prompt += """

## Your Task

Analyze the above information and identify any problems or concerns:

1. **Code Quality Issues**
   - Are there PRs that should have been merged but weren't?
   - Are there stale issues or PRs?
   - Are commit messages clear and descriptive?

2. **Process Issues**
   - Are issues properly labeled?
   - Are there duplicate issues?
   - Are PRs being reviewed in a timely manner?

3. **Project Health**
   - Is the project progressing well?
   - Are there any red flags?
   - Are the AI agents working correctly?

4. **Specific Problems**
   - Any broken workflows?
   - Any security concerns?
   - Any performance issues mentioned?

Respond in this EXACT JSON format:
{
  "status": "healthy" or "warning" or "critical",
  "summary": "Brief overall assessment (max 200 chars)",
  "problems": [
    {
      "severity": "low" or "medium" or "high",
      "category": "code_quality" or "process" or "health" or "security",
      "title": "Brief problem title (max 80 chars)",
      "description": "Detailed description (max 300 chars)",
      "recommendation": "What should be done (max 200 chars)"
    }
  ],
  "positive_observations": [
    "Things that are going well (max 150 chars each)"
  ]
}

If everything looks good, return status "healthy" with empty problems array.
Output ONLY the JSON, nothing else.
"""
        return prompt

    def _run_qa_analysis(self, context: Dict) -> Optional[str]:
        """Run QA analysis using Claude AI"""
        prompt = self._build_qa_prompt(context)
        print(f"📝 Prompt length: {len(prompt)} chars")

        try:
            if USE_CLAUDE_CLI:
                print("🤖 Using Claude CLI...")
                agent = ClaudeAgent(output_format="text", verbose=False)
                result = agent.query(prompt, system_prompt=SystemPrompts.QA_ENGINEER)
                if isinstance(result, dict) and "result" in result:
                    response_text = result["result"]
                else:
                    response_text = str(result)
            else:
                print("🤖 Using Anthropic API...")

                @retry_anthropic_api
                def call_anthropic():
                    client = Anthropic(api_key=self.anthropic_api_key)
                    return client.messages.create(
                        model=CLAUDE_MODELS.QA_ANALYSIS,
                        max_tokens=CLAUDE_MODELS.QA_MAX_TOKENS,
                        system=SystemPrompts.QA_ENGINEER,
                        messages=[{"role": "user", "content": prompt}],
                    )

                message = call_anthropic()
                response_text = message.content[0].text

            print(f"✅ Received response ({len(response_text)} chars)")
            return response_text

        except Exception as e:
            print(f"❌ Error calling Claude: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _parse_and_act_on_results(self, response_text: str) -> bool:
        """Parse QA results and create issues if needed"""
        try:
            # Clean up response
            cleaned = response_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            # Find JSON object
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")

            json_str = cleaned[start_idx:end_idx]
            data = json.loads(json_str)

            status = data.get("status", "unknown")
            summary = data.get("summary", "")
            problems = data.get("problems", [])
            positive = data.get("positive_observations", [])

            print(f"\n{'='*60}")
            print(f"📊 QA Status: {status.upper()}")
            print(f"📝 Summary: {summary}")
            print(f"{'='*60}\n")

            # Show positive observations
            if positive:
                print("✅ Positive Observations:")
                for obs in positive:
                    print(f"   ✓ {obs}")
                print()

            # Show problems
            if problems:
                print(f"⚠️  Found {len(problems)} problem(s):")
                for i, problem in enumerate(problems, 1):
                    severity = problem.get("severity", "unknown")
                    category = problem.get("category", "unknown")
                    title = problem.get("title", "Untitled")
                    description = problem.get("description", "")
                    recommendation = problem.get("recommendation", "")

                    emoji = {"low": "🟡", "medium": "🟠", "high": "🔴"}.get(
                        severity, "⚪"
                    )
                    print(f"\n   {emoji} Problem {i}: {title}")
                    print(f"      Severity: {severity} | Category: {category}")
                    print(f"      {description}")
                    if recommendation:
                        print(f"      💡 Recommendation: {recommendation}")

                # Create issue for problems
                if status in ["warning", "critical"]:
                    self._create_qa_issue(status, summary, problems, positive)
            else:
                print("✅ No problems found - repository health looks good!")

            return True

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse QA response as JSON: {e}")
            print(f"Response: {response_text[:500]}")
            return False
        except Exception as e:
            print(f"❌ Error processing results: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _create_qa_issue(
        self, status: str, summary: str, problems: List[Dict], positive: List[str]
    ) -> Optional[object]:
        """Create a GitHub issue for QA findings"""
        print(f"\n📝 Creating QA issue for {status} status...")

        # Build issue body
        severity_emoji = {"warning": "⚠️", "critical": "🔴"}.get(status, "⚠️")

        body = f"""# {severity_emoji} QA Agent Report - {status.upper()}

**Summary:** {summary}

**Scan Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## 🔍 Problems Detected

"""

        for i, problem in enumerate(problems, 1):
            severity = problem.get("severity", "unknown")
            category = problem.get("category", "unknown")
            title = problem.get("title", "Untitled")
            description = problem.get("description", "")
            recommendation = problem.get("recommendation", "")

            emoji = {"low": "🟡", "medium": "🟠", "high": "🔴"}.get(severity, "⚪")

            body += f"""
### {emoji} Problem {i}: {title}

**Severity:** {severity.upper()}  
**Category:** {category}

**Description:**  
{description}

**Recommendation:**  
{recommendation}

---
"""

        # Add positive observations if any
        if positive:
            body += "\n## ✅ Positive Observations\n\n"
            for obs in positive:
                body += f"- {obs}\n"
            body += "\n---\n"

        body += "\n*Generated by QA Agent*"

        # Determine labels
        labels = ["qa-report"]
        if status == "critical":
            labels.append("priority-high")
        elif status == "warning":
            labels.append("priority-medium")

        # Add category labels
        categories = set(p.get("category", "") for p in problems)
        for cat in categories:
            if cat in ["security", "code_quality", "process", "health"]:
                labels.append(cat)

        # Create the issue with retry
        try:
            @retry_github_api
            def create_issue():
                issue_title = f"QA Report: {summary[:60]}"
                return self.repo.create_issue(
                    title=issue_title, body=body, labels=labels
                )

            new_issue = create_issue()
            print(f"✅ Created QA issue #{new_issue.number}: {new_issue.title}")
            return new_issue
        except Exception as e:
            print(f"❌ Failed to create issue: {e}")
            return None
