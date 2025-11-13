#!/usr/bin/env python3
"""
Issue Resolver Agent
Takes an open issue, analyzes it with Claude AI using Agent SDK, implements a fix, and creates a PR
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from github import Github, Auth
import git

# Try to import Claude Agent SDK, fallback to anthropic
try:
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock
    USE_AGENT_SDK = True
except ImportError:
    print("⚠️  claude_agent_sdk not available, using anthropic SDK")
    from anthropic import Anthropic
    USE_AGENT_SDK = False

# Try to import anyio for async support
try:
    import anyio
    HAS_ANYIO = True
except ImportError:
    print("⚠️  anyio not available, using synchronous execution")
    HAS_ANYIO = False

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
print(f"📋 Config:")
print(f"   - Labels to handle: {LABELS_TO_HANDLE}")
print(f"   - Labels to skip: {LABELS_TO_SKIP}")
print(f"   - Supports: features, bugs, documentation, refactoring, tests, performance, security, CI/CD")

# Initialize clients
auth = Auth.Token(GITHUB_TOKEN)
gh = Github(auth=auth)
repo = gh.get_repo(REPO_NAME)
print(f"✅ Connected to repository: {REPO_NAME}")

git_repo = git.Repo('.')


async def resolve_issue():
    """Use Claude Agent SDK to resolve an issue"""
    
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
        return
    
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
    
    # Build prompt for Claude
    prompt = f"""You are an expert software engineer. Fix this GitHub issue by modifying the necessary files.

Repository: {REPO_NAME}
Issue #{selected_issue.number}: {selected_issue.title}

Description:
{issue_body}

Labels: {', '.join(issue_labels)}

Context from README:
{readme}

Instructions:
1. Analyze the issue carefully
2. Use the Read tool to examine relevant files
3. Use the Write tool to create or modify files with your fixes
4. Make complete, working changes
5. After making changes, summarize what you did

You have access to Read and Write tools to modify files in the current directory."""

    print(f"📝 Prompt length: {len(prompt)} chars")
    
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
        return
    
    # Configure Claude Agent SDK with Read/Write tools
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful software engineer. Use Read and Write tools to fix issues. Always make complete, working changes.",
        allowed_tools=["Read", "Write"],
        permission_mode='acceptEdits',  # Auto-accept file edits
        cwd=str(Path.cwd()),  # Work in current directory
        max_turns=10,
        api_key=ANTHROPIC_API_KEY
    )
    
    print("🤖 Starting Claude Agent with Read/Write tools...")
    
    files_modified = []
    summary = ""
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            # Send the query
            await client.query(prompt)
            
            # Receive and process responses
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            summary += block.text + "\n"
                            print(f"Claude: {block.text[:200]}...")
        
        print(f"✅ Claude completed work")
        print(f"📊 Summary length: {len(summary)} chars")
        
    except Exception as e:
        print(f"❌ Claude Agent error: {e}")
        import traceback
        traceback.print_exc()
        selected_issue.create_comment(f"❌ Failed to generate fix: {e}")
        selected_issue.remove_from_labels('in-progress')
        return
    
    # Check if any files were modified
    if git_repo.is_dirty(untracked_files=True):
        # Get list of changed files
        changed_files = [item.a_path for item in git_repo.index.diff(None)]
        untracked_files = git_repo.untracked_files
        files_modified = changed_files + untracked_files
        
        print(f"📝 Files modified: {len(files_modified)}")
        for f in files_modified:
            print(f"  ✏️  {f}")
        
        # Commit changes
        git_repo.git.add('-A')
        commit_message = f"""Fix: Resolve issue #{selected_issue.number}

{selected_issue.title}

Closes #{selected_issue.number}

---
Generated by Issue Resolver Agent using Claude Agent SDK"""
        
        git_repo.index.commit(commit_message)
        print("✅ Committed changes")
        
        # Push
        origin = git_repo.remote('origin')
        origin.push(branch_name)
        print(f"✅ Pushed branch: {branch_name}")
        
        # Create PR
        pr_title = f"Fix: {selected_issue.title}"
        pr_body = f"""{summary[:500]}

## Changes
{chr(10).join(['- ' + f for f in files_modified[:20]])}

Closes #{selected_issue.number}

---
*Generated by Issue Resolver Agent using Claude Agent SDK*"""
        
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
{chr(10).join(['- ' + f for f in files_modified[:10]])}

---
*Completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*""")
        
        selected_issue.remove_from_labels('in-progress')
        
        print("🎉 Complete!")
        
    else:
        print("⚠️  No files were modified")
        selected_issue.create_comment("⚠️ No changes were made. The issue may need manual review.")
        selected_issue.remove_from_labels('in-progress')


# Run the async function
if HAS_ANYIO:
    anyio.run(resolve_issue)
else:
    print("❌ Error: anyio is required for async execution")
    print("Install with: pip install anyio")
    sys.exit(1)
