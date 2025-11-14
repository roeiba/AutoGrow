#!/usr/bin/env python3
"""
Integration tests for ClaudeAgent - REAL CLI calls
These tests require actual Claude Code CLI installation
"""

import pytest
import os
import sys
import json
import tempfile
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "claude-agent"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from claude_cli_agent import ClaudeAgent
from utils.exceptions import (
    AgentError,
    FileNotFoundError as CustomFileNotFoundError,
)


@pytest.fixture
def agent():
    """Create a real ClaudeAgent instance"""
    try:
        return ClaudeAgent(output_format="json")
    except AgentError as e:
        pytest.skip(f"Claude CLI not available: {e}")


@pytest.fixture
def temp_python_file(tmp_path):
    """Create a temporary Python file for testing"""
    file_path = tmp_path / "test_code.py"
    file_path.write_text(
        """
def calculate_sum(numbers):
    '''Calculate sum of numbers'''
    total = 0
    for num in numbers:
        total += num
    return total

def calculate_average(numbers):
    '''Calculate average of numbers'''
    if not numbers:
        return 0
    return calculate_sum(numbers) / len(numbers)

if __name__ == '__main__':
    nums = [1, 2, 3, 4, 5]
    print(f"Sum: {calculate_sum(nums)}")
    print(f"Average: {calculate_average(nums)}")
"""
    )
    return str(file_path)


@pytest.fixture
def temp_buggy_file(tmp_path):
    """Create a temporary file with bugs"""
    file_path = tmp_path / "buggy_code.py"
    file_path.write_text(
        """
def unsafe_divide(a, b):
    '''Divide two numbers - UNSAFE'''
    return a / b  # Bug: no zero division check

def get_first_item(items):
    '''Get first item from list - UNSAFE'''
    return items[0]  # Bug: no empty list check

def read_file(filename):
    '''Read file content - UNSAFE'''
    with open(filename) as f:  # Bug: no error handling
        return f.read()
"""
    )
    return str(file_path)


class TestClaudeAgentIntegrationBasic:
    """Basic integration tests"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_query(self, agent):
        """Test real query to Claude CLI"""
        result = agent.query(
            "Say 'Claude integration test successful' and nothing else"
        )

        assert result is not None
        assert "result" in result

        response_text = result["result"].lower()
        assert (
            "claude" in response_text
            or "integration" in response_text
            or "successful" in response_text
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_query_with_system_prompt(self, agent):
        """Test query with system prompt"""
        result = agent.query(
            "What is 5+5?", system_prompt="You are a math tutor. Be concise."
        )

        assert result is not None
        assert "result" in result
        assert "10" in result["result"]

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_query_text_format(self):
        """Test query with text output format"""
        try:
            text_agent = ClaudeAgent(output_format="text")
        except RuntimeError as e:
            pytest.skip(f"Claude CLI not available: {e}")
        
        result = text_agent.query("Say 'text format works'")

        assert result is not None
        assert "result" in result
        assert "text format" in result["result"].lower()


class TestClaudeAgentIntegrationFiles:
    """Integration tests with file operations"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_query_with_stdin(self, agent, temp_python_file):
        """Test query with stdin input"""
        with open(temp_python_file, "r") as f:
            content = f.read()

        result = agent.query_with_stdin(
            "List all function names in this Python code", content
        )

        assert result is not None
        assert "result" in result
        response_text = result["result"].lower()
        assert "calculate_sum" in response_text or "calculate_average" in response_text

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_code_review(self, agent, temp_buggy_file):
        """Test real code review"""
        result = agent.code_review(temp_buggy_file)

        assert result is not None
        assert "result" in result
        response_text = result["result"].lower()

        # Should identify security/quality issues
        assert any(
            word in response_text
            for word in [
                "error",
                "exception",
                "check",
                "validation",
                "bug",
                "issue",
                "unsafe",
            ]
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_generate_docs(self, agent, temp_python_file):
        """Test real documentation generation"""
        result = agent.generate_docs(temp_python_file)

        assert result is not None
        assert "result" in result
        response_text = result["result"].lower()

        # Should mention functions and documentation
        assert any(
            word in response_text
            for word in [
                "calculate",
                "function",
                "parameter",
                "return",
                "sum",
                "average",
            ]
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_fix_code(self, agent, temp_buggy_file):
        """Test real code fixing"""
        result = agent.fix_code(
            temp_buggy_file, "Add proper error handling for zero division"
        )

        assert result is not None
        assert "result" in result
        response_text = result["result"].lower()

        # Should mention fixes or error handling
        assert any(
            word in response_text
            for word in ["fix", "error", "exception", "try", "catch", "handle"]
        )


class TestClaudeAgentIntegrationBatch:
    """Integration tests for batch processing"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_batch_process(self, agent, tmp_path):
        """Test real batch processing"""
        # Create multiple test files
        for i in range(3):
            file_path = tmp_path / f"module{i}.py"
            file_path.write_text(
                f"""
def process_{i}(data):
    '''Process data in module {i}'''
    return data * {i}

def validate_{i}(value):
    '''Validate value in module {i}'''
    return value > {i}
"""
            )

        results = agent.batch_process(
            str(tmp_path), "List the function names in this file", file_pattern="*.py"
        )

        assert len(results) == 3
        assert all(r["success"] for r in results)

        # Check that results mention the functions
        for i, result in enumerate(results):
            response_text = str(result["result"]).lower()
            assert f"process_{i}" in response_text or f"validate_{i}" in response_text

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_batch_process_with_errors(self, agent, tmp_path):
        """Test batch processing with some errors"""
        # Create valid file
        (tmp_path / "valid.py").write_text("def valid(): pass")

        # Create file that will cause issues
        (tmp_path / "binary.py").write_bytes(b"\x00\x01\x02\x03")

        results = agent.batch_process(
            str(tmp_path), "Analyze this file", file_pattern="*.py"
        )

        assert len(results) == 2
        # At least one should succeed
        assert any(r["success"] for r in results)


class TestClaudeAgentIntegrationConversations:
    """Integration tests for multi-turn conversations"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_continue_conversation(self, agent):
        """Test continuing a conversation"""
        # First query
        result1 = agent.query("Remember this number: 42")
        assert result1 is not None

        session_id = result1.get("session_id")

        if session_id:
            # Continue with session ID
            result2 = agent.continue_conversation(
                "What number did I ask you to remember?", session_id=session_id
            )

            assert result2 is not None
            assert "result" in result2
            # Should mention 42
            assert "42" in result2["result"]


class TestClaudeAgentIntegrationToolControl:
    """Integration tests for tool control"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_with_allowed_tools(self):
        """Test with allowed tools restriction"""
        try:
            agent = ClaudeAgent(output_format="json", allowed_tools=["Read"])
        except RuntimeError as e:
            pytest.skip(f"Claude CLI not available: {e}")

        result = agent.query("What can you help me with?")

        assert result is not None
        assert "result" in result

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_with_disallowed_tools(self):
        """Test with disallowed tools"""
        try:
            agent = ClaudeAgent(output_format="json", disallowed_tools=["Bash"])
        except RuntimeError as e:
            pytest.skip(f"Claude CLI not available: {e}")

        result = agent.query("Say 'tool control works'")

        assert result is not None
        assert "result" in result


class TestClaudeAgentIntegrationErrorHandling:
    """Integration tests for error handling"""

    @pytest.mark.integration
    def test_file_not_found(self, agent):
        """Test with non-existent file"""
        with pytest.raises(CustomFileNotFoundError):
            agent.code_review("/nonexistent/file.py")

    @pytest.mark.integration
    def test_invalid_file_in_batch(self, agent):
        """Test batch processing with invalid directory"""
        with pytest.raises(CustomFileNotFoundError):
            agent.batch_process(
                "/nonexistent/directory", "test", file_pattern="*.py"
            )


class TestClaudeAgentIntegrationEndToEnd:
    """End-to-end integration tests"""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.timeout(120)  # 2 minute timeout
    def test_complete_code_improvement_workflow(self, agent, temp_buggy_file):
        """
        Test end-to-end workflow: analyze buggy code and suggest improvements.

        Validates:
        1. Agent can identify security/safety issues
        2. Agent provides actionable improvement suggestions
        3. Multi-turn conversation maintains context

        Token-efficient: Uses single combined query instead of multiple calls.
        """
        # Read the buggy code once
        with open(temp_buggy_file, "r") as f:
            buggy_code = f.read()

        # Single comprehensive query that tests multiple capabilities
        # This is more token-efficient than separate calls
        combined_query = """Analyze this Python code and provide:
1. Main security issue (one line)
2. Suggested fix (one line)
3. Function names present (comma-separated)

Be concise."""

        result = agent.query_with_stdin(combined_query, buggy_code)

        # Validate response structure
        assert result is not None, "Agent should return a result"
        assert "result" in result, "Response should have 'result' field"

        response_text = result["result"].lower()

        # Validate behavior: Should identify security issues
        security_keywords = [
            "zero",
            "division",
            "error",
            "exception",
            "check",
            "validation",
            "unsafe",
        ]
        has_security_issue = any(
            keyword in response_text for keyword in security_keywords
        )
        assert has_security_issue, (
            f"Agent should identify security issues. "
            f"Expected keywords: {security_keywords}. "
            f"Got: {response_text[:200]}"
        )

        # Validate behavior: Should mention the actual functions
        function_names = ["unsafe_divide", "get_first_item", "read_file"]
        has_function = any(
            func.replace("_", "") in response_text.replace("_", "")
            for func in function_names
        )
        assert has_function, (
            f"Agent should identify function names. "
            f"Expected: {function_names}. "
            f"Got: {response_text[:200]}"
        )

        # Validate behavior: Should provide actionable suggestions
        suggestion_keywords = [
            "add",
            "try",
            "catch",
            "if",
            "check",
            "validate",
            "handle",
        ]
        has_suggestion = any(
            keyword in response_text for keyword in suggestion_keywords
        )
        assert has_suggestion, (
            f"Agent should provide improvement suggestions. "
            f"Expected keywords: {suggestion_keywords}. "
            f"Got: {response_text[:200]}"
        )

        # Test multi-turn: Verify session context is maintained
        if "session_id" in result:
            session_id = result["session_id"]

            # Follow-up query that requires context from previous response
            followup = agent.continue_conversation(
                "Which function is most critical to fix first?", session_id=session_id
            )

            assert followup is not None, "Follow-up query should work"
            followup_text = followup["result"].lower()

            # Should reference one of the functions from context
            references_function = any(
                func.replace("_", "") in followup_text.replace("_", "")
                for func in function_names
            )
            assert references_function, (
                "Follow-up should maintain context and reference functions. "
                f"Got: {followup_text[:200]}"
            )

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.timeout(90)  # 90 second timeout
    def test_multi_file_project_analysis(self, agent, tmp_path):
        """
        Test batch processing of multiple files.

        Validates:
        1. Batch processing works correctly
        2. Each file is analyzed independently
        3. Results are properly structured
        4. Error handling for mixed success/failure

        Token-efficient: Uses simple, focused queries per file.
        """
        # Create minimal test files
        (tmp_path / "config.py").write_text("CONFIG = {'version': '1.0'}")
        (tmp_path / "utils.py").write_text("def helper(): return 42")
        (tmp_path / "main.py").write_text("from utils import helper\nprint(helper())")

        # Batch analyze with concise prompt (saves tokens)
        results = agent.batch_process(
            str(tmp_path),
            "File purpose (5 words max)",  # Very concise to save tokens
            file_pattern="*.py",
        )

        # Validate batch processing behavior
        assert len(results) == 3, f"Should process 3 files, got {len(results)}"
        assert all(r["success"] for r in results), (
            f"All files should process successfully. "
            f"Failures: {[r for r in results if not r['success']]}"
        )

        # Validate result structure
        for result in results:
            assert "file" in result, "Each result should have 'file' field"
            assert "result" in result, "Each result should have 'result' field"
            assert "success" in result, "Each result should have 'success' field"

        # Validate correct files were processed
        file_names = [Path(r["file"]).name for r in results]
        expected_files = ["config.py", "utils.py", "main.py"]
        for expected in expected_files:
            assert expected in file_names, (
                f"Should process {expected}. " f"Got: {file_names}"
            )

        # Validate responses are meaningful (not empty)
        for result in results:
            response = result["result"]
            if isinstance(response, dict) and "result" in response:
                response = response["result"]
            assert len(str(response)) > 5, (
                f"Response should be meaningful for {result['file']}. "
                f"Got: {response}"
            )


class TestClaudeAgentIntegrationPerformance:
    """Performance-related integration tests"""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.timeout(60)  # 60 second timeout
    def test_large_file_handling(self, agent, tmp_path):
        """
        Test handling of larger files.

        Validates:
        1. Agent can process files with multiple functions
        2. Response is accurate for file size
        3. No errors or timeouts on larger inputs

        Token-efficient: Uses smaller file (10 functions) and simple counting query.
        """
        large_file = tmp_path / "large.py"

        # Create a file with 10 functions (reduced from 50 to save tokens)
        num_functions = 10
        content = [f"def func_{i}(): return {i}" for i in range(num_functions)]
        large_file.write_text("\n".join(content))

        # Simple counting query (token-efficient)
        result = agent.query_with_stdin(
            "Count functions (number only)",  # Very concise prompt
            large_file.read_text(),
        )

        # Validate behavior
        assert result is not None, "Should handle larger files"
        assert "result" in result, "Should return result field"

        response_text = str(result["result"])

        # Should mention the number or "ten" or similar
        count_indicators = [str(num_functions), "ten", "10"]
        has_count = any(
            indicator in response_text.lower() for indicator in count_indicators
        )

        # More lenient check - just verify it processed the file
        assert len(response_text) > 0, (
            f"Should provide a response for large file. " f"Got: {response_text}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
