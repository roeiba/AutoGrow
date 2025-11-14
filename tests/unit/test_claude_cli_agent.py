#!/usr/bin/env python3
"""
Unit tests for ClaudeAgent class
Tests the Python wrapper for Claude Code CLI headless mode
"""

import pytest
import json
import os
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "claude-agent"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from claude_cli_agent import ClaudeAgent
from utils.exceptions import (
    AgentError,
    AgentResponseError,
    JSONParseError,
    FileNotFoundError as CustomFileNotFoundError,
    FileOperationError,
)


class TestClaudeAgentInitialization:
    """Test ClaudeAgent initialization"""

    def test_init_default(self):
        """Test initialization with default parameters"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent()
            assert agent.output_format == "json"
            assert agent.verbose is False
            assert agent.allowed_tools is None
            assert agent.disallowed_tools is None
            assert agent.permission_mode is None

    def test_init_custom_output_format(self):
        """Test initialization with custom output format"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(output_format="text")
            assert agent.output_format == "text"

    def test_init_verbose(self):
        """Test initialization with verbose mode"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(verbose=True)
            assert agent.verbose is True

    def test_init_with_tools(self):
        """Test initialization with tool restrictions"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(
                allowed_tools=["Read", "Write"], disallowed_tools=["Bash"]
            )
            assert agent.allowed_tools == ["Read", "Write"]
            assert agent.disallowed_tools == ["Bash"]

    def test_init_with_permission_mode(self):
        """Test initialization with permission mode"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(permission_mode="acceptEdits")
            assert agent.permission_mode == "acceptEdits"

    def test_init_claude_not_installed(self):
        """Test initialization fails when claude CLI not installed"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=False):
            with pytest.raises(AgentError, match="Claude Code CLI is not installed"):
                ClaudeAgent()


class TestClaudeAgentInstallationCheck:
    """Test claude CLI installation check"""

    @patch("subprocess.run")
    def test_is_claude_installed_true(self, mock_run):
        """Test detection when claude CLI is installed"""
        mock_run.return_value = Mock(returncode=0)

        agent = ClaudeAgent.__new__(ClaudeAgent)
        assert agent._is_claude_installed() is True

    @patch("subprocess.run")
    def test_is_claude_installed_false_not_found(self, mock_run):
        """Test detection when claude CLI is not found"""
        mock_run.side_effect = FileNotFoundError()

        agent = ClaudeAgent.__new__(ClaudeAgent)
        assert agent._is_claude_installed() is False

    @patch("subprocess.run")
    def test_is_claude_installed_false_error(self, mock_run):
        """Test detection when claude CLI returns error"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "claude")

        agent = ClaudeAgent.__new__(ClaudeAgent)
        assert agent._is_claude_installed() is False


class TestClaudeAgentBuildCommand:
    """Test command building"""

    @pytest.fixture
    def agent(self):
        """Create a ClaudeAgent instance for testing"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            return ClaudeAgent()

    def test_build_command_basic(self, agent):
        """Test basic command building"""
        cmd = agent._build_command("Test prompt")

        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "Test prompt" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd

    def test_build_command_with_verbose(self):
        """Test command building with verbose mode"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(verbose=True)

        cmd = agent._build_command("Test prompt")
        assert "--verbose" in cmd

    def test_build_command_with_allowed_tools(self):
        """Test command building with allowed tools"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(allowed_tools=["Read", "Write"])

        cmd = agent._build_command("Test prompt")
        assert "--allowedTools" in cmd
        assert "Read,Write" in cmd

    def test_build_command_with_disallowed_tools(self):
        """Test command building with disallowed tools"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(disallowed_tools=["Bash"])

        cmd = agent._build_command("Test prompt")
        assert "--disallowedTools" in cmd
        assert "Bash" in cmd

    def test_build_command_with_permission_mode(self):
        """Test command building with permission mode"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(permission_mode="acceptEdits")

        cmd = agent._build_command("Test prompt")
        assert "--permission-mode" in cmd
        assert "acceptEdits" in cmd

    def test_build_command_with_additional_args(self, agent):
        """Test command building with additional arguments"""
        cmd = agent._build_command("Test prompt", ["--extra", "arg"])
        assert "--extra" in cmd
        assert "arg" in cmd


class TestClaudeAgentQuery:
    """Test ClaudeAgent query method"""

    @pytest.fixture
    def agent(self):
        """Create a ClaudeAgent instance for testing"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            return ClaudeAgent()

    @patch("subprocess.run")
    def test_query_basic(self, mock_run, agent):
        """Test basic query"""
        mock_response = {
            "type": "result",
            "result": "This is a test response",
            "session_id": "abc123",
        }
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query("Test prompt")

        assert result["result"] == "This is a test response"
        assert result["session_id"] == "abc123"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_query_with_system_prompt(self, mock_run, agent):
        """Test query with system prompt"""
        mock_response = {"result": "Response with system prompt"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query("Test prompt", system_prompt="Custom instruction")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--append-system-prompt" in cmd
        assert "Custom instruction" in cmd

    @patch("subprocess.run")
    def test_query_with_mcp_config(self, mock_run, agent):
        """Test query with MCP configuration"""
        mock_response = {"result": "Response with MCP"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query("Test prompt", mcp_config="servers.json")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--mcp-config" in cmd
        assert "servers.json" in cmd

    @patch("subprocess.run")
    def test_query_text_format(self, mock_run):
        """Test query with text output format"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            agent = ClaudeAgent(output_format="text")

        mock_run.return_value = Mock(stdout="Plain text response", returncode=0)

        result = agent.query("Test prompt")

        assert result["result"] == "Plain text response"

    @patch("subprocess.run")
    def test_query_subprocess_error(self, mock_run, agent):
        """Test query handles subprocess errors"""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "claude", stderr="API error"
        )

        with pytest.raises(AgentError, match="Claude CLI"):
            agent.query("Test prompt")

    @patch("subprocess.run")
    def test_query_json_decode_error(self, mock_run, agent):
        """Test query handles JSON decode errors"""
        mock_run.return_value = Mock(stdout="Invalid JSON {", returncode=0)

        with pytest.raises(JSONParseError, match="Failed to parse JSON"):
            agent.query("Test prompt")


class TestClaudeAgentQueryWithStdin:
    """Test ClaudeAgent query_with_stdin method"""

    @pytest.fixture
    def agent(self):
        """Create a ClaudeAgent instance for testing"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            return ClaudeAgent()

    @patch("subprocess.run")
    def test_query_with_stdin_basic(self, mock_run, agent):
        """Test query with stdin input"""
        mock_response = {"result": "File analysis"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query_with_stdin("Analyze this code", "def test():\n    pass\n")

        assert result["result"] == "File analysis"

        # Verify stdin content was passed
        call_args = mock_run.call_args
        assert call_args[1]["input"] == "def test():\n    pass\n"

    @patch("subprocess.run")
    def test_query_with_stdin_and_system_prompt(self, mock_run, agent):
        """Test query with stdin and system prompt"""
        mock_response = {"result": "Analysis"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query_with_stdin(
            "Analyze", "code content", system_prompt="You are an expert"
        )

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--append-system-prompt" in cmd


class TestClaudeAgentContinueConversation:
    """Test ClaudeAgent continue_conversation method"""

    @pytest.fixture
    def agent(self):
        """Create a ClaudeAgent instance for testing"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            return ClaudeAgent()

    @patch("subprocess.run")
    def test_continue_conversation_no_session(self, mock_run, agent):
        """Test continuing most recent conversation"""
        mock_response = {"result": "Continued response"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.continue_conversation("Follow up")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--continue" in cmd
        assert "Follow up" in cmd

    @patch("subprocess.run")
    def test_continue_conversation_with_session(self, mock_run, agent):
        """Test resuming specific conversation"""
        mock_response = {"result": "Resumed response"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.continue_conversation("Follow up", session_id="abc123")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--resume" in cmd
        assert "abc123" in cmd
        assert "Follow up" in cmd


class TestClaudeAgentCodeReview:
    """Test ClaudeAgent code_review method"""

    @pytest.fixture
    def agent(self):
        """Create a ClaudeAgent instance for testing"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            return ClaudeAgent()

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary Python file for testing"""
        file_path = tmp_path / "code.py"
        file_path.write_text("def vulnerable_function():\n    eval(input())\n")
        return str(file_path)

    @patch("subprocess.run")
    def test_code_review(self, mock_run, agent, temp_file):
        """Test code review functionality"""
        mock_response = {"result": "Security issue found: eval() usage"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.code_review(temp_file)

        assert "Security issue" in result["result"]

        # Verify prompt includes review criteria
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        prompt_index = cmd.index("-p") + 1
        prompt = cmd[prompt_index]
        assert "Security vulnerabilities" in prompt
        assert "Performance issues" in prompt

    def test_code_review_file_not_found(self, agent):
        """Test code review with non-existent file"""
        with pytest.raises(CustomFileNotFoundError):
            agent.code_review("/nonexistent/file.py")


class TestClaudeAgentGenerateDocs:
    """Test ClaudeAgent generate_docs method"""

    @pytest.fixture
    def agent(self):
        """Create a ClaudeAgent instance for testing"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            return ClaudeAgent()

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary file for testing"""
        file_path = tmp_path / "module.py"
        file_path.write_text("def add(a, b):\n    return a + b\n")
        return str(file_path)

    @patch("subprocess.run")
    def test_generate_docs(self, mock_run, agent, temp_file):
        """Test documentation generation"""
        mock_response = {
            "result": "# Module Documentation\n\n## Functions\n\n### add(a, b)"
        }
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.generate_docs(temp_file)

        assert "Module Documentation" in result["result"]


class TestClaudeAgentFixCode:
    """Test ClaudeAgent fix_code method"""

    @pytest.fixture
    def agent(self):
        """Create a ClaudeAgent instance for testing"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            return ClaudeAgent()

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary file for testing"""
        file_path = tmp_path / "buggy.py"
        file_path.write_text("def buggy():\n    x = 1 / 0\n")
        return str(file_path)

    @patch("subprocess.run")
    def test_fix_code(self, mock_run, agent, temp_file):
        """Test code fixing"""
        mock_response = {"result": "Fixed: Added try-except block"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.fix_code(temp_file, "Fix division by zero")

        assert "Fixed" in result["result"]

        # Verify issue description in prompt
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        prompt_index = cmd.index("-p") + 1
        prompt = cmd[prompt_index]
        assert "Fix division by zero" in prompt


class TestClaudeAgentBatchProcess:
    """Test ClaudeAgent batch_process method"""

    @pytest.fixture
    def agent(self):
        """Create a ClaudeAgent instance for testing"""
        with patch.object(ClaudeAgent, "_is_claude_installed", return_value=True):
            return ClaudeAgent()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory with test files"""
        (tmp_path / "file1.py").write_text("# File 1")
        (tmp_path / "file2.py").write_text("# File 2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.py").write_text("# File 3")
        return str(tmp_path)

    @patch("subprocess.run")
    def test_batch_process_success(self, mock_run, agent, temp_dir):
        """Test successful batch processing"""
        mock_response = {"result": "Analysis complete"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        results = agent.batch_process(temp_dir, "Analyze this file")

        assert len(results) == 3  # 3 Python files
        assert all(r["success"] for r in results)
        assert all("file" in r for r in results)
        assert all("result" in r for r in results)

    @patch("subprocess.run")
    def test_batch_process_with_errors(self, mock_run, agent, temp_dir):
        """Test batch processing with some errors"""
        # First call succeeds, second fails, third succeeds
        mock_run.side_effect = [
            Mock(stdout=json.dumps({"result": "OK"}), returncode=0),
            subprocess.CalledProcessError(1, "claude", stderr="Error"),
            Mock(stdout=json.dumps({"result": "OK"}), returncode=0),
        ]

        results = agent.batch_process(temp_dir, "Analyze")

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "error" in results[1]
        assert results[2]["success"] is True


class TestClaudeAgentIntegration:
    """Integration tests (require actual claude CLI installation)"""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.path.exists("/usr/local/bin/claude")
        and not os.path.exists(os.path.expanduser("~/.local/bin/claude")),
        reason="Claude CLI not installed",
    )
    def test_real_query(self):
        """Test with real claude CLI (requires installation)"""
        try:
            agent = ClaudeAgent()
            result = agent.query("Say 'test successful' and nothing else")
            assert "result" in result
            assert len(result["result"]) > 0
        except RuntimeError as e:
            pytest.skip(f"Claude CLI not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
