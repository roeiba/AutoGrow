#!/usr/bin/env python3
"""
Issue Resolver Agent
Takes an open issue, analyzes it with Claude AI, implements a fix, and creates a PR
"""

import os
import sys
import json
import time
from datetime import datetime
from github import Github, Auth
from anthropic import Anthropic
import git

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
REPO_NAME = os.getenv('REPO_NAME')
SPECIFIC_ISSUE = os.getenv('SPECIFIC_ISSUE')
LABELS_TO_HANDLE = os.getenv('ISSUE_LABELS_TO_HANDLE', 'bug,enhancement').split(',')
LABELS_TO_SKIP = os.getenv('ISSUE_LABELS_TO_SKIP', 'wontfix,duplicate,in-progress').split(',')
MAX_TIME = int(os.getenv('MAX_EXECUTION_TIME', '8')) * 60

start_time = time.time()

print("🤖 Issue Resolver Agent Starting")
print(f"📋 Config: labels_to_handle={LABELS_TO_HANDLE}, labels_to_skip={LABELS_TO_SKIP}")

# Initialize clients
auth = Auth.Token(GITHUB_TOKEN)
gh = Github(auth=auth)
repo = gh.get_repo(REPO_NAME)
print(f"✅ Connected to repository: {REPO_NAME}")
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
git_repo = git.Repo('.')

# Select issue
selected_issue = None

if SPECIFIC_ISSUE:
    print(f"🎯 Working on specific issue #{SPECIFIC_ISSUE}")
    selected_issue = repo.get_issue(int(SPECIFIC_ISSUE))
else:
    print("🔍 Searching for issue to resolve...")
    open_issues = repo.get_issues(state='open', sort='created', direction='asc')
    
    for issue in open_issues:
        if issue.pull_request:
            continue
        
        issue_labels = [label.name for label in issue.labels]
        if any(skip_label in issue_labels for skip_label in LABELS_TO_SKIP):
            continue
        
        if LABELS_TO_HANDLE and not any(handle_label in issue_labels for handle_label in LABELS_TO_HANDLE):
            continue
        
        comments = list(issue.get_comments())
        if any('Issue Resolver Agent' in c.body and 'claimed' in c.body.lower() for c in comments):
            continue
        
        selected_issue = issue
        break

if not selected_issue:
    print("ℹ️  No suitable issues found")
    sys.exit(0)

print(f"✅ Selected issue #{selected_issue.number}: {selected_issue.title}")

# Claim the issue
claim_message = f"""🤖 **Issue Resolver Agent**

I'm working on this issue now.

**Started at:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Status:** In Progress

---
*Automated by GitHub Actions*"""

selected_issue.create_comment(claim_message)
selected_issue.add_to_labels('in-progress')
print("📝 Claimed issue")

# Get context
try:
    readme = repo.get_readme().decoded_content.decode('utf-8')[:2000]
except:
    readme = "No README found"

issue_body = selected_issue.body or "No description provided"
issue_labels = [label.name for label in selected_issue.labels]

# Build prompt
prompt = f"""You are an expert software engineer fixing a GitHub issue.

Repository: {REPO_NAME}
Issue #{selected_issue.number}: {selected_issue.title}

Description:
{issue_body}

Labels: {', '.join(issue_labels)}

Context:
{readme}

Provide a fix in JSON format. Keep file content concise.
{{
  "analysis": "Brief analysis (max 200 chars)",
  "files_to_modify": [
    {{
      "path": "relative/path/to/file",
      "action": "create|modify|delete",
      "content": "Complete file content",
      "explanation": "Brief explanation (max 100 chars)"
    }}
  ],
  "pr_title": "Concise PR title (max 80 chars)",
  "pr_body": "Brief PR description (max 300 chars)"
}}

IMPORTANT: Output ONLY the JSON object, no markdown. Keep all text fields brief."""

print(f"📝 Prompt length: {len(prompt)} chars")

# Call Claude
print("🤖 Calling Claude AI...")
try:
    message = anthropic.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response_text = message.content[0].text
    print(f"✅ Received solution ({len(response_text)} chars)")
    print(f"📊 Token usage - Input: {message.usage.input_tokens}, Output: {message.usage.output_tokens}")
except Exception as e:
    print(f"❌ Claude API error: {e}")
    selected_issue.create_comment(f"❌ Failed to call Claude API: {e}")
    selected_issue.remove_from_labels('in-progress')
    sys.exit(1)

# Parse response
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
    
    solution = json.loads(json_str)
    print("✅ Successfully parsed JSON")
    
except json.JSONDecodeError as e:
    print(f"❌ Failed to parse response: {e}")
    print(f"📄 Response (first 1000 chars): {response_text[:1000]}")
    print(f"📄 Response (last 500 chars): {response_text[-500:]}")
    selected_issue.create_comment(f"❌ Failed to parse AI response. JSON error: {e}\n\nWill retry later.")
    selected_issue.remove_from_labels('in-progress')
    sys.exit(1)
except ValueError as e:
    print(f"❌ Value error: {e}")
    print(f"📄 Response: {response_text[:1000]}")
    selected_issue.create_comment(f"❌ Invalid response format: {e}")
    selected_issue.remove_from_labels('in-progress')
    sys.exit(1)

# Create branch
branch_name = f"fix/issue-{selected_issue.number}-{int(time.time())}"
print(f"🌿 Creating branch: {branch_name}")
try:
    git_repo.git.checkout('-b', branch_name)
    print(f"✅ Branch created: {branch_name}")
except Exception as e:
    print(f"❌ Failed to create branch: {e}")
    selected_issue.create_comment(f"❌ Failed to create branch: {e}")
    selected_issue.remove_from_labels('in-progress')
    sys.exit(1)

# Apply changes
print(f"📝 Applying {len(solution.get('files_to_modify', []))} file changes...")
files_modified = []
for file_change in solution.get('files_to_modify', []):
    file_path = file_change.get('path')
    action = file_change.get('action', 'modify')
    content = file_change.get('content', '')
    
    if not file_path:
        continue
    
    full_path = os.path.join('.', file_path)
    
    if action == 'delete':
        if os.path.exists(full_path):
            os.remove(full_path)
            files_modified.append(f"Deleted: {file_path}")
            print(f"  🗑️  Deleted: {file_path}")
    else:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        files_modified.append(f"{action.capitalize()}: {file_path}")
        print(f"  ✏️  {action.capitalize()}: {file_path} ({len(content)} chars)")

if not files_modified:
    print("⚠️  No files modified")
    selected_issue.create_comment("⚠️ No changes generated.")
    selected_issue.remove_from_labels('in-progress')
    sys.exit(0)

# Commit
git_repo.git.add('-A')
commit_message = f"""Fix: {solution.get('pr_title', f'Resolve issue #{selected_issue.number}')}

Closes #{selected_issue.number}

---
Generated by Issue Resolver Agent"""

git_repo.index.commit(commit_message)
print("✅ Committed")

# Push
origin = git_repo.remote('origin')
origin.push(branch_name)
print(f"✅ Pushed branch")

# Create PR
pr_title = solution.get('pr_title', f"Fix: Resolve issue #{selected_issue.number}")
pr_body = f"""{solution.get('pr_body', '')}

## Changes
{chr(10).join(['- ' + f for f in files_modified])}

Closes #{selected_issue.number}

---
*Generated by Issue Resolver Agent*"""

pr = repo.create_pull(
    title=pr_title,
    body=pr_body,
    head=branch_name,
    base='main'
)

print(f"✅ Created PR #{pr.number}")

# Update issue
selected_issue.create_comment(f"""✅ **Solution Ready**

Pull Request: #{pr.number}

**Changes:**
{chr(10).join(['- ' + f for f in files_modified])}

---
*Completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*""")

selected_issue.remove_from_labels('in-progress')

print("🎉 Complete!")
