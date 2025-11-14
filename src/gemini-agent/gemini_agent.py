#!/usr/bin/env python3
"""
Gemini Agent - Python wrapper for Gemini CLI in headless mode
Provides a Python interface to interact with Gemini CLI in agent mode
"""

import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from logging_config import get_logger, log_performance
from utils.exceptions import (
    AgentError,
    AgentResponseError,
    JSONParseError,
    MissingEnvironmentVariableError,
    ConfigurationError,
    FileOperationError,
)

# Initialize logger
logger = get_logger(__name__)


class GeminiAgent:
    """
    Python wrapper for Gemini CLI in headless mode.
    Enables programmatic access to Gemini's capabilities.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-pro",
        output_format: str = "json",
        debug: bool = False,
    ):
        """
        Initialize the Gemini Agent.

        Args:
            api_key: Gemini API key (if not provided, uses GEMINI_API_KEY env var)
            model: Model to use (default: gemini-pro)
            output_format: Output format (json or text)
            debug: Enable debug mode
        """
        logger.info(
            f"Initializing GeminiAgent with model={model}, output_format={output_format}"
        )

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in environment or constructor")
            raise MissingEnvironmentVariableError("GEMINI_API_KEY")

        self.model = model
        self.output_format = output_format
        self.debug = debug

        logger.debug(f"API key configured (length: {len(self.api_key)})")

        # Check if gemini CLI is installed
        if not self._is_gemini_installed():
            logger.error("Gemini CLI not found in system PATH")
            raise ConfigurationError(
                "Gemini CLI is not installed. Install it with:\n"
                "  npm install -g @google/generative-ai-cli\n"
                "Or visit: https://github.com/google-gemini/gemini-cli"
            )

        logger.info("GeminiAgent initialized successfully")

    def _is_gemini_installed(self) -> bool:
        """Check if gemini-cli is installed."""
        try:
            subprocess.run(["gemini", "--version"], capture_output=True, check=True)
            logger.debug("Gemini CLI found in system PATH")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"Gemini CLI not found: {e}")
            return False

    def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        yolo: bool = False,
        include_directories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a query to Gemini in headless mode.

        Args:
            prompt: The prompt to send
            include_dirs: Additional directories to include in context
            yolo: Auto-approve all actions
            model: Override default model

        Returns:
            Dict containing response and metadata
        """
        logger.info(f"Sending query to Gemini with model={model or self.model}")
        logger.debug(f"Query prompt: {prompt[:100]}...")

        cmd = [
            "gemini",
            "-p",
            prompt,
            "--output-format",
            self.output_format,
            "-m",
            model or self.model,
        ]

        if include_directories:
            cmd.extend(["--include-directories", ",".join(include_directories)])
            logger.debug(f"Including directories: {include_directories}")

        if yolo:
            cmd.append("--yolo")
            logger.debug("Auto-approve mode enabled (yolo)")

        if self.debug:
            cmd.append("--debug")

        env = os.environ.copy()
        env["GEMINI_API_KEY"] = self.api_key

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, env=env
            )

            if self.output_format == "json":
                try:
                    response = json.loads(result.stdout)
                    logger.info("Query completed successfully")
                    return response
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.debug(f"Response text: {result.stdout[:500]}")
                    raise JSONParseError(result.stdout, str(e))
            else:
                logger.info("Query completed successfully")
                return {"response": result.stdout}

        except subprocess.CalledProcessError as e:
            logger.error(f"Gemini CLI process failed: {e.stderr}")
            raise AgentError(
                f"Gemini CLI execution failed: {e.stderr}",
                details={"command": " ".join(cmd), "return_code": e.returncode}
            )

    def query_with_file(
        self, prompt: str, file_path: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a query with file content as input.

        Args:
            prompt: The prompt to send
            file_path: Path to file to include
            model: Override default model

        Returns:
            Dict containing response and metadata
        """
        logger.info(f"Querying Gemini with file: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileOperationError(f"File not found: {file_path}")

        try:
            with open(file_path, "r") as f:
                file_content = f.read()
            logger.debug(f"Read {len(file_content)} characters from {file_path}")
        except IOError as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise FileOperationError(
                f"Failed to read file: {file_path}",
                details={"error": str(e)}
            )

        cmd = [
            "gemini",
            "-p",
            prompt,
            "--output-format",
            self.output_format,
            "-m",
            model or self.model,
        ]

        if self.debug:
            cmd.append("--debug")

        env = os.environ.copy()
        env["GEMINI_API_KEY"] = self.api_key

        try:
            result = subprocess.run(
                cmd,
                input=file_content,
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )

            if self.output_format == "json":
                try:
                    response = json.loads(result.stdout)
                    logger.info("Query with file completed successfully")
                    return response
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.debug(f"Response text: {result.stdout[:500]}")
                    raise JSONParseError(result.stdout, str(e))
            else:
                logger.info("Query with file completed successfully")
                return {"response": result.stdout}

        except subprocess.CalledProcessError as e:
            logger.error(f"Gemini CLI process failed: {e.stderr}")
            raise AgentError(
                f"Gemini CLI execution failed: {e.stderr}",
                details={"command": " ".join(cmd), "return_code": e.returncode}
            )

    def code_review(self, file_path: str) -> Dict[str, Any]:
        """
        Perform a code review on a file.

        Args:
            file_path: Path to the file to review

        Returns:
            Dict containing review results
        """
        logger.info(f"Starting code review for: {file_path}")

        prompt = """Review this code for:
        1. Security vulnerabilities
        2. Performance issues
        3. Code quality and best practices
        4. Potential bugs
        5. Suggestions for improvement

        Provide a structured analysis with severity levels."""

        return self.query_with_file(prompt, file_path)

    def generate_docs(self, file_path: str) -> Dict[str, Any]:
        """
        Generate documentation for a file.

        Args:
            file_path: Path to the file to document

        Returns:
            Dict containing generated documentation
        """
        logger.info(f"Generating documentation for: {file_path}")

        prompt = """Generate comprehensive documentation for this code including:
        1. Overview and purpose
        2. Function/class descriptions
        3. Parameters and return values
        4. Usage examples
        5. Dependencies

        Format as Markdown."""

        return self.query_with_file(prompt, file_path, model="gemini-2.5-pro")

    def analyze_logs(self, log_file: str, focus: str = "errors") -> Dict[str, Any]:
        """
        Analyze log file for issues.

        Args:
            log_file: Path to log file
            focus: What to focus on (errors, warnings, patterns)

        Returns:
            Dict containing analysis results
        """
        logger.info(f"Analyzing log file: {log_file} (focus: {focus})")

        prompt = f"""Analyze these logs focusing on {focus}. Provide:
        1. Root cause analysis
        2. Severity assessment
        3. Recommended fixes
        4. Prevention strategies
        5. Related patterns or issues"""

        return self.query_with_file(prompt, log_file)

    def batch_process(
        self, directory: str, prompt: str, file_pattern: str = "*.py"
    ) -> List[Dict[str, Any]]:
        """
        Process multiple files in a directory.

        Args:
            directory: Directory to process
            prompt: Prompt to apply to each file
            file_pattern: Glob pattern for files to process

        Returns:
            List of results for each file
        """
        logger.info(f"Starting batch process in directory: {directory} with pattern: {file_pattern}")
        results = []
        path = Path(directory)

        if not path.exists():
            logger.error(f"Directory not found: {directory}")
            raise FileOperationError(f"Directory not found: {directory}")

        if not path.is_dir():
            logger.error(f"Path is not a directory: {directory}")
            raise FileOperationError(f"Path is not a directory: {directory}")

        file_count = 0
        for file_path in path.rglob(file_pattern):
            if file_path.is_file():
                file_count += 1
                try:
                    logger.debug(f"Processing file {file_count}: {file_path}")
                    result = self.query_with_file(prompt, str(file_path))
                    results.append(
                        {"file": str(file_path), "result": result, "success": True}
                    )
                except (AgentError, AgentResponseError, JSONParseError, FileOperationError) as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
                    results.append(
                        {"file": str(file_path), "error": str(e), "success": False}
                    )
                except Exception as e:
                    logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
                    results.append(
                        {"file": str(file_path), "error": f"Unexpected error: {str(e)}", "success": False}
                    )

        logger.info(f"Batch process completed: {file_count} files processed, {sum(1 for r in results if r['success'])} successful")
        return results


def main():
    """Example usage of GeminiAgent."""
    import sys

    # Load environment variables from .env if it exists
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        logger.info(f"Loading environment variables from {env_file}")
        try:
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value
        except IOError as e:
            logger.error(f"Failed to read .env file: {e}")

    try:
        logger.info("Starting Gemini Agent example")
        agent = GeminiAgent(debug=True)

        logger.info("=" * 50)
        logger.info("Gemini Agent - Python Interface")
        logger.info("=" * 50)

        # Example 1: Simple query
        logger.info("\n1. Simple Query:")
        result = agent.query("What are the best practices for Python error handling?")
        logger.info(f"Response: {result.get('response', 'No response')}")

        # Example 2: Query with context
        logger.info("\n2. Query with Project Context:")
        result = agent.query("Explain the project structure", include_directories=["../.."])
        logger.info(f"Response: {result.get('response', 'No response')}")

        # Example 3: Code review (if file provided)
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            logger.info(f"\n3. Code Review: {file_path}")
            result = agent.code_review(file_path)
            logger.info(f"Response: {result.get('response', 'No response')}")

    except (MissingEnvironmentVariableError, ConfigurationError) as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except (AgentError, AgentResponseError, JSONParseError) as e:
        logger.error(f"Agent error: {e}")
        sys.exit(1)
    except FileOperationError as e:
        logger.error(f"File operation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
