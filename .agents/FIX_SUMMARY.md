# Test Failure Fix Summary

## Issue
Three integration tests in `test_claude_cli_agent_integration.py` were failing in CI with:
```
RuntimeError: Claude Code CLI is not installed. Install it from:
  https://code.claude.com/
```

### Failed Tests
1. `TestClaudeAgentIntegrationBasic::test_real_query_text_format` (line 117)
2. `TestClaudeAgentIntegrationToolControl::test_real_with_allowed_tools` (line 295)
3. `TestClaudeAgentIntegrationToolControl::test_real_with_disallowed_tools` (line 306)

## Root Cause
These three tests were instantiating `ClaudeAgent` directly without using the `agent` fixture. The fixture includes proper error handling that calls `pytest.skip()` when Claude CLI is not available, but the direct instantiations did not have this protection.

## Solution
Wrapped the `ClaudeAgent` instantiations in try-except blocks that catch `RuntimeError` and call `pytest.skip()` when the CLI is not available. This matches the pattern used in the `agent` fixture.

### Changes Made
Modified `/tests/integration/test_claude_cli_agent_integration.py`:

1. **test_real_query_text_format** (lines 117-120):
```python
try:
    text_agent = ClaudeAgent(output_format="text")
except RuntimeError as e:
    pytest.skip(f"Claude CLI not available: {e}")
```

2. **test_real_with_allowed_tools** (lines 299-302):
```python
try:
    agent = ClaudeAgent(output_format="json", allowed_tools=["Read"])
except RuntimeError as e:
    pytest.skip(f"Claude CLI not available: {e}")
```

3. **test_real_with_disallowed_tools** (lines 313-316):
```python
try:
    agent = ClaudeAgent(output_format="json", disallowed_tools=["Bash"])
except RuntimeError as e:
    pytest.skip(f"Claude CLI not available: {e}")
```

## Verification
- ✅ Tests pass locally when Claude CLI is installed
- ✅ Tests correctly skip when CLI is not available (verified with mocking)
- ✅ Error handling matches the pattern in the `agent` fixture
- ✅ No changes to test logic or assertions

## Expected CI Behavior
In CI environments where Claude CLI is not installed:
- These 3 tests will now **skip** instead of **fail**
- Test coverage will continue to run successfully
- Other tests will continue to run normally

## Impact
- **Before**: 3 failed tests in CI
- **After**: 3 skipped tests in CI (expected behavior)
- No impact on environments where Claude CLI is installed
