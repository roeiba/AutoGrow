# Claude Agent SDK Migration

## Overview
Migrating from Anthropic Messages API to Claude Agent SDK for better autonomous agent capabilities.

## Changes Made

### 1. GitHub Workflows (✅ Complete)
- **issue-generator.yml**: Added Node.js setup and Claude Code CLI installation
- **issue-resolver.yml**: Added Node.js setup and Claude Code CLI installation
- Updated dependencies from `anthropic` to `claude-agent-sdk`

### 2. Workflow Scripts (✅ Complete)
- **issue_generator.py**: Rewritten to use `query()` function from Agent SDK
  - Uses `ClaudeAgentOptions` for configuration
  - Async/await pattern with `anyio`
  - Simpler API, no manual message construction
  
- **issue_resolver.py**: Rewritten to use `ClaudeSDKClient` with Read/Write tools
  - Uses `allowed_tools=["Read", "Write"]` to give Claude file system access
  - `permission_mode='acceptEdits'` for auto-accepting file changes
  - Claude can now directly read and modify files
  - No need for manual JSON parsing of file changes
  - Agent autonomously decides what files to modify

### 3. Docker Agent (🚧 TODO)
- **src/claude-agent/requirements.txt**: Updated to use `claude-agent-sdk`
- **src/claude-agent/src/agent_workflow.py**: Needs rewrite to use Agent SDK
  - Should use `ClaudeSDKClient` with Read/Write/Bash tools
  - Remove manual file operations - let Claude handle them
  - Simplify prompt construction
  - Use agent loop instead of manual orchestration

## Benefits of Agent SDK

1. **File System Access**: Claude can read/write files directly using built-in tools
2. **Bash Commands**: Can execute commands when needed
3. **Autonomous Operation**: Agent decides what tools to use
4. **Better Error Handling**: SDK handles tool execution and errors
5. **Simpler Code**: No manual JSON parsing or file operations
6. **MCP Support**: Can integrate with Model Context Protocol servers
7. **Hooks**: Can add custom logic at specific points in agent loop

## Key Differences

### Before (Messages API)
```python
from anthropic import Anthropic

anthropic = Anthropic(api_key=api_key)
message = anthropic.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
response = message.content[0].text
# Parse JSON, manually handle file operations
```

### After (Agent SDK)
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode='acceptEdits',
    cwd="/path/to/repo",
    api_key=api_key
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Fix this issue by modifying the files")
    async for msg in client.receive_response():
        # Claude handles file operations automatically
        print(msg)
```

## Prerequisites

- Python 3.10+
- Node.js 20+
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`

## Next Steps

1. ✅ Update GitHub workflow scripts
2. ✅ Update workflow YAML files  
3. 🚧 Rewrite src/claude-agent/src/agent_workflow.py
4. 🚧 Update Docker configuration if needed
5. 🚧 Test workflows end-to-end
6. 🚧 Update documentation

## Testing

Test locally:
```bash
# Install dependencies
pip install claude-agent-sdk PyGithub GitPython anyio
npm install -g @anthropic-ai/claude-code

# Set environment variables
export GITHUB_TOKEN=your_token
export ANTHROPIC_API_KEY=your_key
export REPO_NAME=owner/repo

# Run scripts
python .github/scripts/issue_generator.py
python .github/scripts/issue_resolver.py
```

## References

- [Claude Agent SDK GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Agent SDK Examples](https://github.com/anthropics/claude-agent-sdk-python/tree/main/examples)
