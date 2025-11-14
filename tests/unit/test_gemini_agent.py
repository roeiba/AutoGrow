#!/usr/bin/env python3
"""
Unit tests for GeminiAgent class
Tests the Python wrapper for gemini-cli headless mode
"""

import pytest
import json
import os
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "gemini-agent"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from gemini_agent import GeminiAgent
from utils.exceptions import (
    AgentError,
    AgentResponseError,
    JSONParseError,
    MissingEnvironmentVariableError,
    ConfigurationError,
    FileOperationError,
)


class TestGeminiAgentInitialization:
    """Test GeminiAgent initialization"""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            agent = GeminiAgent(api_key="test-key-123")
            assert agent.api_key == "test-key-123"
            assert agent.model == "gemini-pro"
            assert agent.output_format == "json"
            assert agent.debug is False

    def test_init_with_env_var(self):
        """Test initialization with API key from environment"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key-456"}):
            with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
                agent = GeminiAgent()
                assert agent.api_key == "env-key-456"

    def test_init_without_api_key_raises_error(self):
        """Test initialization fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
                with pytest.raises(MissingEnvironmentVariableError):
                    GeminiAgent()

    def test_init_custom_model(self):
        """Test initialization with custom model"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            agent = GeminiAgent(api_key="test-key", model="gemini-2.5-flash")
            assert agent.model == "gemini-2.5-flash"

    def test_init_custom_output_format(self):
        """Test initialization with custom output format"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            agent = GeminiAgent(api_key="test-key", output_format="text")
            assert agent.output_format == "text"

    def test_init_debug_mode(self):
        """Test initialization with debug mode"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            agent = GeminiAgent(api_key="test-key", debug=True)
            assert agent.debug is True

    def test_init_gemini_not_installed(self):
        """Test initialization fails when gemini-cli not installed"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=False):
            with pytest.raises(ConfigurationError, match="Gemini CLI is not installed"):
                GeminiAgent(api_key="test-key")


class TestGeminiAgentInstallationCheck:
    """Test gemini-cli installation check"""

    @patch("subprocess.run")
    def test_is_gemini_installed_true(self, mock_run):
        """Test detection when gemini-cli is installed"""
        mock_run.return_value = Mock(returncode=0)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            agent = GeminiAgent()
            assert agent._is_gemini_installed() is True

    @patch("subprocess.run")
    def test_is_gemini_installed_false_not_found(self, mock_run):
        """Test detection when gemini-cli is not found"""
        mock_run.side_effect = FileNotFoundError()

        agent = GeminiAgent.__new__(GeminiAgent)
        assert agent._is_gemini_installed() is False

    @patch("subprocess.run")
    def test_is_gemini_installed_false_error(self, mock_run):
        """Test detection when gemini-cli returns error"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gemini")

        agent = GeminiAgent.__new__(GeminiAgent)
        assert agent._is_gemini_installed() is False


class TestGeminiAgentQuery:
    """Test GeminiAgent query method"""

    @pytest.fixture
    def agent(self):
        """Create a GeminiAgent instance for testing"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            return GeminiAgent(api_key="test-key-123")

    @patch("subprocess.run")
    def test_query_basic(self, mock_run, agent):
        """Test basic query"""
        mock_response = {"response": "This is a test response", "stats": {"models": {}}}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query("Test prompt")

        assert result["response"] == "This is a test response"
        mock_run.assert_called_once()

        # Verify command structure
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "gemini"
        assert "-p" in cmd
        assert "Test prompt" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd

    @patch("subprocess.run")
    def test_query_with_include_directories(self, mock_run, agent):
        """Test query with include directories"""
        mock_response = {"response": "Response with context"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query("Test prompt", include_directories=["src", "docs"])

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--include-directories" in cmd
        assert "src,docs" in cmd

    @patch("subprocess.run")
    def test_query_with_yolo_mode(self, mock_run, agent):
        """Test query with YOLO mode"""
        mock_response = {"response": "Auto-approved response"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query("Test prompt", yolo=True)

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--yolo" in cmd

    @patch("subprocess.run")
    def test_query_with_custom_model(self, mock_run, agent):
        """Test query with custom model"""
        mock_response = {"response": "Flash model response"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query("Test prompt", model="gemini-2.5-flash")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "-m" in cmd
        assert "gemini-2.5-flash" in cmd

    @patch("subprocess.run")
    def test_query_with_debug(self, mock_run):
        """Test query with debug mode"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            agent = GeminiAgent(api_key="test-key", debug=True)

        mock_response = {"response": "Debug response"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query("Test prompt")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--debug" in cmd

    @patch("subprocess.run")
    def test_query_text_format(self, mock_run):
        """Test query with text output format"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            agent = GeminiAgent(api_key="test-key", output_format="text")

        mock_run.return_value = Mock(stdout="Plain text response", returncode=0)

        result = agent.query("Test prompt")

        assert result["response"] == "Plain text response"

    @patch("subprocess.run")
    def test_query_subprocess_error(self, mock_run, agent):
        """Test query handles subprocess errors"""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "gemini", stderr="API error"
        )

        with pytest.raises(AgentError, match="Gemini CLI"):
            agent.query("Test prompt")

    @patch("subprocess.run")
    def test_query_json_decode_error(self, mock_run, agent):
        """Test query handles JSON decode errors"""
        mock_run.return_value = Mock(stdout="Invalid JSON {", returncode=0)

        with pytest.raises(JSONParseError, match="Failed to parse JSON"):
            agent.query("Test prompt")

    @patch("subprocess.run")
    def test_query_api_key_in_env(self, mock_run, agent):
        """Test that API key is passed in environment"""
        mock_response = {"response": "Success"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        agent.query("Test prompt")

        call_args = mock_run.call_args
        env = call_args[1]["env"]
        assert env["GEMINI_API_KEY"] == "test-key-123"


class TestGeminiAgentQueryWithFile:
    """Test GeminiAgent query_with_file method"""

    @pytest.fixture
    def agent(self):
        """Create a GeminiAgent instance for testing"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            return GeminiAgent(api_key="test-key-123")

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary file for testing"""
        file_path = tmp_path / "test_file.py"
        file_path.write_text("def test():\n    pass\n")
        return str(file_path)

    @patch("subprocess.run")
    def test_query_with_file_basic(self, mock_run, agent, temp_file):
        """Test query with file input"""
        mock_response = {"response": "File analysis"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query_with_file("Analyze this code", temp_file)

        assert result["response"] == "File analysis"

        # Verify file content was passed as input
        call_args = mock_run.call_args
        assert call_args[1]["input"] == "def test():\n    pass\n"

    def test_query_with_file_not_found(self, agent):
        """Test query with non-existent file"""
        with pytest.raises(FileOperationError):
            agent.query_with_file("Analyze", "/nonexistent/file.py")

    @patch("subprocess.run")
    def test_query_with_file_custom_model(self, mock_run, agent, temp_file):
        """Test query with file and custom model"""
        mock_response = {"response": "Analysis"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.query_with_file("Analyze", temp_file, model="gemini-2.5-flash")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "gemini-2.5-flash" in cmd


class TestGeminiAgentCodeReview:
    """Test GeminiAgent code_review method"""

    @pytest.fixture
    def agent(self):
        """Create a GeminiAgent instance for testing"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            return GeminiAgent(api_key="test-key-123")

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary Python file for testing"""
        file_path = tmp_path / "code.py"
        file_path.write_text("def vulnerable_function():\n    eval(input())\n")
        return str(file_path)

    @patch("subprocess.run")
    def test_code_review(self, mock_run, agent, temp_file):
        """Test code review functionality"""
        mock_response = {"response": "Security issue found: eval() usage"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.code_review(temp_file)

        assert "Security issue" in result["response"]

        # Verify prompt includes review criteria
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        prompt_index = cmd.index("-p") + 1
        prompt = cmd[prompt_index]
        assert "Security vulnerabilities" in prompt
        assert "Performance issues" in prompt
        assert "Code quality" in prompt


class TestGeminiAgentGenerateDocs:
    """Test GeminiAgent generate_docs method"""

    @pytest.fixture
    def agent(self):
        """Create a GeminiAgent instance for testing"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            return GeminiAgent(api_key="test-key-123")

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
            "response": "# Module Documentation\n\n## Functions\n\n### add(a, b)"
        }
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.generate_docs(temp_file)

        assert "Module Documentation" in result["response"]

        # Verify uses pro model
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "gemini-2.5-pro" in cmd


class TestGeminiAgentAnalyzeLogs:
    """Test GeminiAgent analyze_logs method"""

    @pytest.fixture
    def agent(self):
        """Create a GeminiAgent instance for testing"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            return GeminiAgent(api_key="test-key-123")

    @pytest.fixture
    def temp_log(self, tmp_path):
        """Create a temporary log file for testing"""
        log_path = tmp_path / "app.log"
        log_path.write_text(
            "ERROR: Connection failed\n"
            "ERROR: Database timeout\n"
            "WARNING: High memory usage\n"
        )
        return str(log_path)

    @patch("subprocess.run")
    def test_analyze_logs_default(self, mock_run, agent, temp_log):
        """Test log analysis with default focus"""
        mock_response = {"response": "Found 2 errors: Connection and database issues"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.analyze_logs(temp_log)

        assert "errors" in result["response"]

        # Verify prompt mentions errors
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        prompt_index = cmd.index("-p") + 1
        prompt = cmd[prompt_index]
        assert "errors" in prompt.lower()

    @patch("subprocess.run")
    def test_analyze_logs_custom_focus(self, mock_run, agent, temp_log):
        """Test log analysis with custom focus"""
        mock_response = {"response": "Pattern analysis"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        result = agent.analyze_logs(temp_log, focus="patterns")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        prompt_index = cmd.index("-p") + 1
        prompt = cmd[prompt_index]
        assert "patterns" in prompt.lower()


class TestGeminiAgentBatchProcess:
    """Test GeminiAgent batch_process method"""

    @pytest.fixture
    def agent(self):
        """Create a GeminiAgent instance for testing"""
        with patch.object(GeminiAgent, "_is_gemini_installed", return_value=True):
            return GeminiAgent(api_key="test-key-123")

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
        mock_response = {"response": "Analysis complete"}
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
            Mock(stdout=json.dumps({"response": "OK"}), returncode=0),
            subprocess.CalledProcessError(1, "gemini", stderr="Error"),
            Mock(stdout=json.dumps({"response": "OK"}), returncode=0),
        ]

        results = agent.batch_process(temp_dir, "Analyze")

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "error" in results[1]
        assert results[2]["success"] is True

    @patch("subprocess.run")
    def test_batch_process_custom_pattern(self, mock_run, agent, temp_dir):
        """Test batch processing with custom file pattern"""
        # Create a JS file
        Path(temp_dir) / "test.js" / "test.js"

        mock_response = {"response": "Analysis"}
        mock_run.return_value = Mock(stdout=json.dumps(mock_response), returncode=0)

        results = agent.batch_process(temp_dir, "Analyze", file_pattern="*.js")

        # Should only process JS files
        assert all(".js" in r["file"] for r in results if r["success"])


class TestGeminiAgentIntegration:
    """Integration tests (require actual gemini-cli installation)"""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set"
    )
    def test_real_query(self):
        """Test with real gemini-cli (requires API key and installation)"""
        try:
            agent = GeminiAgent()
            result = agent.query("Say 'test successful' and nothing else")
            assert "response" in result
            assert len(result["response"]) > 0
        except RuntimeError as e:
            pytest.skip(f"gemini-cli not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
