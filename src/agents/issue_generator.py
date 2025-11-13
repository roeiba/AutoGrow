#!/usr/bin/env python3
"""
Issue Generator Agent - Core Logic

Ensures minimum number of open issues by generating new ones with Claude AI using Agent SDK
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple

# Add src directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'claude-agent'))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import model configuration
from models_config import CLAUDE_MODELS, SystemPrompts

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
    
    def __init__(self, repo, anthropic_api_key: Optional[str] = None, min_issues: int = 3):
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
        
    def check_and_generate(self) -> bool:
        """
        Check issue count and generate if needed
        
        Returns:
            bool: True if issues were generated, False otherwise
        """
        print(f"🔍 Checking issue count (minimum: {self.min_issues})")
        
        # Count open issues (excluding pull requests)
        open_issues = list(self.repo.get_issues(state='open'))
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
        # Get repository context
        print("📖 Analyzing repository for potential issues...")

        try:
            readme = self.repo.get_readme().decoded_content.decode('utf-8')[:1000]
        except:
            readme = "No README found"

        recent_commits = list(self.repo.get_commits()[:5])
        commit_messages = "\n".join([f"- {c.commit.message.split(chr(10))[0]}" for c in recent_commits])

        # Analyze project structure
        print("🔍 Analyzing project structure...")
        project_context = self._analyze_project_structure()

        # Build prompt for Claude
        prompt = self._build_prompt(needed, readme, commit_messages, open_issues, project_context)

        print(f"📝 Prompt length: {len(prompt)} chars")

        # Call Claude AI
        response_text = self._call_claude(prompt)

        if not response_text:
            print("❌ Failed to get response from Claude")
            sys.exit(1)

        # Parse and create issues
        self._parse_and_create_issues(response_text, needed)

    def _analyze_project_structure(self) -> Dict:
        """
        Analyze the full project structure including directories, file types, and code patterns

        Returns:
            Dict containing project structure analysis
        """
        try:
            # Get directory structure
            dir_structure = self._get_directory_structure()

            # Get file types distribution
            file_types = self._get_file_types_distribution()

            # Detect code patterns and frameworks
            code_patterns = self._detect_code_patterns()

            # Get key configuration files
            config_files = self._get_config_files()

            return {
                'directory_structure': dir_structure,
                'file_types': file_types,
                'code_patterns': code_patterns,
                'config_files': config_files
            }
        except Exception as e:
            print(f"⚠️  Error analyzing project structure: {e}")
            return {
                'directory_structure': {},
                'file_types': {},
                'code_patterns': [],
                'config_files': []
            }

    def _get_directory_structure(self) -> Dict:
        """Get the main directory structure of the repository"""
        try:
            contents = self.repo.get_contents("")
            structure = {}

            # Track main directories
            directories = []
            key_files = []

            for content in contents:
                if content.type == "dir":
                    directories.append(content.name)
                    # Get first level subdirectories for important dirs
                    if content.name in ['src', 'lib', 'app', 'tests', 'docs', 'scripts', '.github']:
                        try:
                            subcontents = self.repo.get_contents(content.path)
                            subdirs = [c.name for c in subcontents if c.type == "dir"]
                            structure[content.name] = subdirs[:10]  # Limit to 10 subdirs
                        except:
                            structure[content.name] = []
                else:
                    key_files.append(content.name)

            structure['_root_dirs'] = directories
            structure['_root_files'] = key_files

            return structure
        except Exception as e:
            print(f"⚠️  Error getting directory structure: {e}")
            return {}

    def _get_file_types_distribution(self) -> Dict:
        """Analyze distribution of file types in the repository"""
        try:
            # Get all files from git tree (more efficient than recursive API calls)
            tree = self.repo.get_git_tree(self.repo.default_branch, recursive=True)

            file_extensions = []
            for item in tree.tree[:1000]:  # Limit to first 1000 files
                if item.type == "blob":
                    path = Path(item.path)
                    if path.suffix:
                        file_extensions.append(path.suffix.lower())

            # Count file types
            extension_counts = Counter(file_extensions)

            # Return top 15 file types
            return dict(extension_counts.most_common(15))
        except Exception as e:
            print(f"⚠️  Error getting file types: {e}")
            return {}

    def _detect_code_patterns(self) -> List[str]:
        """Detect programming languages, frameworks, and patterns used in the project"""
        patterns = []

        try:
            # Check for language-specific files
            language_indicators = {
                'Python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
                'JavaScript/Node.js': ['package.json', 'yarn.lock', 'npm-shrinkwrap.json'],
                'TypeScript': ['tsconfig.json'],
                'Go': ['go.mod', 'go.sum'],
                'Rust': ['Cargo.toml', 'Cargo.lock'],
                'Java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
                'Ruby': ['Gemfile', 'Gemfile.lock'],
                'PHP': ['composer.json', 'composer.lock'],
                'C#/.NET': ['.csproj', '.sln'],
                'Docker': ['Dockerfile', 'docker-compose.yml'],
                'Kubernetes': ['deployment.yaml', 'service.yaml'],
                'Terraform': ['.tf'],
                'CI/CD': ['.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile'],
                'Testing': ['pytest.ini', 'jest.config.js', 'phpunit.xml'],
                'Documentation': ['docs/', 'README.md', 'CONTRIBUTING.md']
            }

            contents = self.repo.get_contents("")
            file_names = [c.name for c in contents]

            # Check root directory for indicators
            for pattern_name, indicators in language_indicators.items():
                for indicator in indicators:
                    if indicator in file_names or any(indicator in f for f in file_names):
                        patterns.append(pattern_name)
                        break

            # Check for workflows directory
            try:
                workflows = self.repo.get_contents(".github/workflows")
                if workflows:
                    patterns.append('GitHub Actions')
            except:
                pass

            # Check for common frameworks in package.json
            try:
                package_json = self.repo.get_contents("package.json")
                package_data = json.loads(package_json.decoded_content.decode('utf-8'))
                dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}

                framework_indicators = {
                    'React': 'react',
                    'Vue': 'vue',
                    'Angular': '@angular/core',
                    'Express': 'express',
                    'Next.js': 'next',
                    'NestJS': '@nestjs/core',
                    'Jest': 'jest',
                    'Webpack': 'webpack'
                }

                for framework, package in framework_indicators.items():
                    if package in dependencies:
                        patterns.append(framework)
            except:
                pass

            # Check for Python frameworks in requirements.txt
            try:
                requirements = self.repo.get_contents("requirements.txt")
                req_content = requirements.decoded_content.decode('utf-8').lower()

                framework_indicators = {
                    'Django': 'django',
                    'Flask': 'flask',
                    'FastAPI': 'fastapi',
                    'Pytest': 'pytest',
                    'NumPy': 'numpy',
                    'Pandas': 'pandas',
                    'TensorFlow': 'tensorflow',
                    'PyTorch': 'torch'
                }

                for framework, package in framework_indicators.items():
                    if package in req_content:
                        patterns.append(framework)
            except:
                pass

        except Exception as e:
            print(f"⚠️  Error detecting code patterns: {e}")

        return list(set(patterns))  # Remove duplicates

    def _get_config_files(self) -> List[str]:
        """Get list of important configuration files present in the repository"""
        config_files = []

        important_configs = [
            '.gitignore', '.dockerignore', 'Makefile',
            'README.md', 'LICENSE', 'CONTRIBUTING.md',
            'CODE_OF_CONDUCT.md', 'SECURITY.md',
            '.env.example', 'config.yaml', 'config.json'
        ]

        try:
            contents = self.repo.get_contents("")
            file_names = [c.name for c in contents]

            for config in important_configs:
                if config in file_names:
                    config_files.append(config)
        except Exception as e:
            print(f"⚠️  Error getting config files: {e}")

        return config_files

    def _build_prompt(self, needed: int, readme: str, commit_messages: str, open_issues: List, project_context: Dict = None) -> str:
        """Build the prompt for Claude with enhanced project context"""

        # Format project context if available
        context_section = ""
        if project_context:
            # Directory structure
            if project_context.get('directory_structure'):
                dir_info = project_context['directory_structure']
                root_dirs = dir_info.get('_root_dirs', [])
                context_section += f"\nProject Structure:\n"
                context_section += f"Root directories: {', '.join(root_dirs[:15])}\n"

                # Show subdirectories for key folders
                for key in ['src', 'tests', 'docs', 'scripts', '.github']:
                    if key in dir_info and dir_info[key]:
                        context_section += f"  {key}/: {', '.join(dir_info[key])}\n"

            # File types distribution
            if project_context.get('file_types'):
                file_types = project_context['file_types']
                context_section += f"\nFile Types Distribution:\n"
                for ext, count in list(file_types.items())[:10]:
                    context_section += f"  {ext}: {count} files\n"

            # Code patterns and frameworks
            if project_context.get('code_patterns'):
                patterns = project_context['code_patterns']
                context_section += f"\nDetected Technologies & Frameworks:\n"
                context_section += f"  {', '.join(patterns)}\n"

            # Configuration files
            if project_context.get('config_files'):
                config_files = project_context['config_files']
                context_section += f"\nKey Configuration Files:\n"
                context_section += f"  {', '.join(config_files)}\n"

        return f"""Analyze this GitHub repository and suggest {needed} new issue(s).

Repository: {self.repo.full_name}

README excerpt:
{readme}

Recent commits:
{commit_messages}
{context_section}
Current open issues:
{chr(10).join([f"- #{i.number}: {i.title}" for i in open_issues[:10]])}

Based on the full project analysis above (directory structure, file types, technologies used, and configuration),
generate {needed} realistic, actionable issue(s) that are contextually appropriate for this project.

Consider:
- The project's tech stack and frameworks
- Missing tests for existing code
- Documentation gaps
- CI/CD improvements
- Code quality and refactoring opportunities
- Missing configuration or setup files
- Security best practices
- Performance optimizations
- Developer experience improvements
- Feature enhancements aligned with the project's purpose

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

Use appropriate labels: feature, bug, documentation, refactor, test, performance, security, ci/cd, enhancement

Keep descriptions brief and output ONLY the JSON, nothing else."""
    
    def _call_claude(self, prompt: str) -> Optional[str]:
        """Call Claude AI (CLI or API)"""
        try:
            if USE_CLAUDE_CLI:
                print("🤖 Using Claude CLI...")
                agent = ClaudeAgent(
                    output_format="text",
                    verbose=True
                )
                
                result = agent.query(
                    prompt,
                    system_prompt=SystemPrompts.ISSUE_GENERATOR
                )
                
                # Extract response
                if isinstance(result, dict) and "result" in result:
                    return result["result"]
                else:
                    return str(result)
            else:
                print("🤖 Using Anthropic API...")
                client = Anthropic(api_key=self.anthropic_api_key)
                
                message = client.messages.create(
                    model=CLAUDE_MODELS.ISSUE_GENERATION,
                    max_tokens=CLAUDE_MODELS.DEFAULT_MAX_TOKENS,
                    system=SystemPrompts.ISSUE_GENERATOR,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                return message.content[0].text
            
        except Exception as e:
            print(f"❌ Error calling Claude: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_and_create_issues(self, response_text: str, needed: int) -> None:
        """Parse Claude response and create GitHub issues"""
        try:
            print("🔍 Parsing Claude response...")
            
            # Clean up response - remove markdown code blocks if present
            cleaned_response = response_text.strip()
            if "```json" in cleaned_response:
                cleaned_response = cleaned_response.split("```json")[1].split("```")[0].strip()
                print("📝 Removed ```json``` markers")
            elif "```" in cleaned_response:
                cleaned_response = cleaned_response.split("```")[1].split("```")[0].strip()
                print("📝 Removed ``` markers")
            
            # Find JSON object in response
            start_idx = cleaned_response.find('{')
            end_idx = cleaned_response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = cleaned_response[start_idx:end_idx]
            print(f"📊 Extracted JSON: {len(json_str)} chars")
            
            data = json.loads(json_str)
            issues_to_create = data.get('issues', [])[:needed]
            
            if not issues_to_create:
                print("⚠️  No issues generated by Claude")
                return
            
            # Create issues
            for issue_data in issues_to_create:
                title = issue_data.get('title', 'Untitled Issue')[:80]  # Limit title length
                body = issue_data.get('body', '')
                labels = issue_data.get('labels', [])
                
                full_body = f"{body}\n\n---\n*Generated by Issue Generator Agent*"
                
                new_issue = self.repo.create_issue(
                    title=title,
                    body=full_body,
                    labels=labels
                )
                
                print(f"✅ Created issue #{new_issue.number}: {title}")
            
            print(f"🎉 Successfully generated {len(issues_to_create)} issue(s)")
            
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
