#!/usr/bin/env python3
"""
Issue Generator Agent - Core Logic

Ensures minimum number of open issues by generating new ones with Claude AI using Agent SDK
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add src directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "claude-agent"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import model configuration
from models_config import CLAUDE_MODELS, SystemPrompts
from utils.retry import retry_anthropic_api, retry_github_api
from utils.deduplication import IssueDuplicateChecker

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


class IssueGenerator:
    """Generates GitHub issues using AI based on repository context"""

    def __init__(
        self, repo, anthropic_api_key: Optional[str] = None, min_issues: int = 3
    ):
        """
        Initialize the Issue Generator

        Args:
            repo: PyGithub Repository object
            anthropic_api_key: Anthropic API key (required if not using Claude CLI)
            min_issues: Minimum number of open issues to maintain
        """
        self.repo = repo
        self.anthropic_api_key = anthropic_api_key
        self.min_issues = min_issues
        # Initialize duplicate checker with tuned thresholds
        self.duplicate_checker = IssueDuplicateChecker(
            title_similarity_threshold=0.75,
            body_similarity_threshold=0.60,
            combined_similarity_threshold=0.65,
        )

    def check_and_generate(self) -> bool:
        """
        Check issue count and generate if needed

        Returns:
            bool: True if issues were generated, False otherwise
        """
        print(f"🔍 Checking issue count (minimum: {self.min_issues})")

        # Count open issues (excluding pull requests) with retry
        @retry_github_api
        def get_open_issues():
            return list(self.repo.get_issues(state="open"))

        open_issues = get_open_issues()
        open_issues = [i for i in open_issues if not i.pull_request]
        issue_count = len(open_issues)

        print(f"📊 Current open issues: {issue_count}")

        if issue_count >= self.min_issues:
            print(f"✅ Sufficient issues exist ({issue_count} >= {self.min_issues})")
            return False

        # Need to generate issues
        needed = self.min_issues - issue_count
        print(f"🤖 Generating {needed} new issue(s)...")

        self._generate_issues(needed, open_issues)
        return True

    def _generate_issues(self, needed: int, open_issues: List) -> None:
        """
        Generate issues using Claude AI

        Args:
            needed: Number of issues to generate
            open_issues: List of current open issues
        """
        # Get repository context with retry
        print("📖 Analyzing repository for potential issues...")

        @retry_github_api
        def get_readme():
            try:
                return self.repo.get_readme().decoded_content.decode("utf-8")[:1000]
            except:
                return "No README found"

        @retry_github_api
        def get_commits():
            return list(self.repo.get_commits()[:5])

        readme = get_readme()
        recent_commits = get_commits()
        commit_messages = "\n".join(
            [f"- {c.commit.message.split(chr(10))[0]}" for c in recent_commits]
        )

        # Build prompt for Claude
        prompt = self._build_prompt(needed, readme, commit_messages, open_issues)

        print(f"📝 Prompt length: {len(prompt)} chars")

        # Call Claude AI
        response_text = self._call_claude(prompt)

        if not response_text:
            print("❌ Failed to get response from Claude")
            sys.exit(1)

        # Parse and create issues (with deduplication)
        self._parse_and_create_issues(response_text, needed, open_issues)

    def _build_prompt(
        self, needed: int, readme: str, commit_messages: str, open_issues: List
    ) -> str:
        """Build the prompt for Claude"""
        return f"""Analyze this GitHub repository and suggest {needed} new issue(s).

Repository: {self.repo.full_name}

README excerpt:
{readme}

Recent commits:
{commit_messages}

Current open issues:
{chr(10).join([f"- #{i.number}: {i.title}" for i in open_issues[:10]])}

Generate {needed} realistic, actionable issue(s). 
Read the whole project and find the most important thing for it - from new features, UI, apps, marketing or sales tools to bug fixes, tests, devops etc. 

Respond with ONLY a JSON object in this exact format:
{{
  "issues": [
    {{
      "title": "Brief title (max 80 chars)",
      "body": "Description (max 300 chars)",
      "labels": ["feature"]
    }}
  ]
}}

Use appropriate labels: feature, bug, documentation, refactor, test, performance, security, ci/cd

Keep descriptions brief and output ONLY the JSON, nothing else."""

    def _call_claude(self, prompt: str) -> Optional[str]:
        """Call Claude AI (CLI or API)"""
        try:
            if USE_CLAUDE_CLI:
                print("🤖 Using Claude CLI...")
                agent = ClaudeAgent(output_format="text", verbose=True)

                result = agent.query(
                    prompt, system_prompt=SystemPrompts.ISSUE_GENERATOR
                )

                # Extract response
                if isinstance(result, dict) and "result" in result:
                    return result["result"]
                else:
                    return str(result)
            else:
                print("🤖 Using Anthropic API...")

                @retry_anthropic_api
                def call_anthropic():
                    client = Anthropic(api_key=self.anthropic_api_key)
                    return client.messages.create(
                        model=CLAUDE_MODELS.ISSUE_GENERATION,
                        max_tokens=CLAUDE_MODELS.DEFAULT_MAX_TOKENS,
                        system=SystemPrompts.ISSUE_GENERATOR,
                        messages=[{"role": "user", "content": prompt}],
                    )

                message = call_anthropic()
                return message.content[0].text

        except Exception as e:
            print(f"❌ Error calling Claude: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _parse_and_create_issues(self, response_text: str, needed: int, open_issues: List) -> None:
        """Parse Claude response and create GitHub issues after deduplication check"""
        try:
            print("🔍 Parsing Claude response...")

            # Clean up response - remove markdown code blocks if present
            cleaned_response = response_text.strip()
            if "```json" in cleaned_response:
                cleaned_response = (
                    cleaned_response.split("```json")[1].split("```")[0].strip()
                )
                print("📝 Removed ```json``` markers")
            elif "```" in cleaned_response:
                cleaned_response = (
                    cleaned_response.split("```")[1].split("```")[0].strip()
                )
                print("📝 Removed ``` markers")

            # Find JSON object in response
            start_idx = cleaned_response.find("{")
            end_idx = cleaned_response.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")

            json_str = cleaned_response[start_idx:end_idx]
            print(f"📊 Extracted JSON: {len(json_str)} chars")

            data = json.loads(json_str)
            issues_to_create = data.get("issues", [])[:needed]

            if not issues_to_create:
                print("⚠️  No issues generated by Claude")
                return

            # Perform deduplication check
            print(f"🔎 Checking {len(issues_to_create)} proposed issue(s) for duplicates...")
            unique_issues, duplicates = self.duplicate_checker.check_issue_list(
                issues_to_create, open_issues, verbose=True
            )

            # Report deduplication results
            if duplicates:
                print(f"🚫 Filtered out {len(duplicates)} duplicate issue(s):")
                for dup_issue, existing, scores in duplicates:
                    print(f"   - '{dup_issue['title'][:50]}' (similar to #{existing.number}, "
                          f"similarity: {scores['combined_similarity']:.1%})")

            if not unique_issues:
                print("⚠️  All proposed issues were duplicates - no new issues created")
                return

            print(f"✅ {len(unique_issues)} unique issue(s) to create")

            # Create issues with retry
            created_count = 0
            for issue_data in unique_issues:
                title = issue_data.get("title", "Untitled Issue")[
                    :80
                ]  # Limit title length
                body = issue_data.get("body", "")
                labels = issue_data.get("labels", [])

                full_body = f"{body}\n\n---\n*Generated by Issue Generator Agent*"

                @retry_github_api
                def create_issue():
                    return self.repo.create_issue(
                        title=title, body=full_body, labels=labels
                    )

                new_issue = create_issue()
                created_count += 1
                print(f"✅ Created issue #{new_issue.number}: {title}")

            # Report final statistics
            print(f"\n📊 Deduplication Summary:")
            print(f"   - Proposed: {len(issues_to_create)}")
            print(f"   - Duplicates filtered: {len(duplicates)}")
            print(f"   - Created: {created_count}")
            print(f"   - Spam reduction: {(len(duplicates) / len(issues_to_create) * 100):.1f}%")
            print(f"🎉 Successfully generated {created_count} issue(s)")

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Claude response as JSON: {e}")
            print(f"Response (first 1000 chars): {response_text[:1000]}")
            print(f"Response (last 500 chars): {response_text[-500:]}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error creating issues: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
