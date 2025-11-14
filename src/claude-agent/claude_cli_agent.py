#!/usr/bin/env python3
"""
Claude CLI Agent - Python wrapper for Claude Code CLI headless mode
Provides a Python interface to interact with Claude CLI in headless mode
"""

import json
import os
import subprocess
from typing import Dict, List, Optional, Any

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_config import get_logger
from utils.exceptions import (
    AgentError,
    AgentResponseError,
    AgentTimeoutError,
    JSONParseError,
    FileNotFoundError as CustomFileNotFoundError,
    FileOperationError,
    AutoGrowException,
)

logger = get_logger(__name__)


class ClaudeAgent:
    """
    Python wrapper for Claude Code CLI in headless mode.
    Enables programmatic access to Claude's capabilities.
    """

    def __init__(
        self,
        output_format: str = "json",
        verbose: bool = False,
        allowed_tools: Optional[List[str]] = None,
        disallowed_tools: Optional[List[str]] = None,
        permission_mode: Optional[str] = None,
        require_cli: bool = True,
    ):
        """
        Initialize the Claude CLI Agent.

        Args:
            output_format: Output format (text, json, stream-json)
            verbose: Enable verbose output
            allowed_tools: List of allowed tools
            disallowed_tools: List of disallowed tools
            permission_mode: Permission mode (acceptEdits, etc.)
            require_cli: If True, raise error if CLI is not available. If False, just set availability flag.
        """
        self.output_format = output_format
        self.verbose = verbose
        self.allowed_tools = allowed_tools
        self.disallowed_tools = disallowed_tools
        self.permission_mode = permission_mode

        # Check if claude CLI is installed
        self.cli_available = self._is_claude_installed()
        if require_cli and not self.cli_available:
            error_msg = "Claude Code CLI is not installed. Install it from: https://code.claude.com/"
            logger.error(error_msg)
            raise AgentError(error_msg)

        if self.cli_available:
            logger.info("Claude CLI Agent initialized successfully")
        else:
            logger.warning("Claude CLI not available, but not required")

    def _is_claude_installed(self) -> bool:
        """Check if claude CLI is installed."""
        try:
            subprocess.run(["claude", "--version"], capture_output=True, check=True)
            logger.debug("Claude CLI is installed and available")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.debug(f"Claude CLI not found: {e}")
            return False

    def _build_command(
        self, prompt: str, additional_args: Optional[List[str]] = None
    ) -> List[str]:
        """
        Build the claude CLI command for headless mode.

        Args:
            prompt: The prompt to send
            additional_args: Additional command line arguments

        Returns:
            List of command arguments
        """
        # Use -p (--print) for headless mode
        cmd = ["claude", "-p", prompt]

        # Add output format
        if self.output_format:
            cmd.extend(["--output-format", self.output_format])

        # Add verbose flag
        if self.verbose:
            cmd.append("--verbose")

        # Add allowed tools
        if self.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self.allowed_tools)])

        # Add disallowed tools
        if self.disallowed_tools:
            cmd.extend(["--disallowedTools", ",".join(self.disallowed_tools)])

        # Add permission mode (acceptEdits for automated workflows)
        if self.permission_mode:
            cmd.extend(["--permission-mode", self.permission_mode])

        # Add any additional arguments
        if additional_args:
            cmd.extend(additional_args)

        logger.debug(f"Built command with {len(cmd)} arguments")
        return cmd

    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        mcp_config: Optional[str] = None,
        stream_output: bool = False,
    ) -> Dict[str, Any]:
        """
        Send a query to Claude in headless mode.

        Args:
            prompt: The prompt to send
            system_prompt: Additional system prompt
            mcp_config: Path to MCP configuration file
            stream_output: If True, print output in real-time

        Returns:
            Dict containing response and metadata
        """
        additional_args = []

        if system_prompt:
            additional_args.extend(["--append-system-prompt", system_prompt])

        if mcp_config:
            additional_args.extend(["--mcp-config", mcp_config])

        cmd = self._build_command(prompt, additional_args)

        logger.info("Executing Claude CLI query")
        logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            if stream_output:
                logger.debug("Using streaming output mode")
                # Stream output in real-time
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )

                stdout_lines = []
                stderr_lines = []

                # Read stdout in real-time
                for line in process.stdout:
                    logger.debug(f"Stream output: {line.strip()}")
                    stdout_lines.append(line)

                # Wait for completion and get stderr
                process.wait()
                stderr_output = process.stderr.read()

                stdout_text = "".join(stdout_lines)

                # Handle stderr - distinguish between warnings and errors
                if stderr_output:
                    stderr_lower = stderr_output.lower()
                    is_warning_only = (
                        "warn:" in stderr_lower or "warning:" in stderr_lower
                    ) and stdout_text.strip()  # Has actual output

                    if is_warning_only:
                        logger.warning(f"Claude CLI warning: {stderr_output.strip()}")
                    else:
                        logger.error(f"Claude CLI error: {stderr_output}")
                        stderr_lines.append(stderr_output)

                # Only raise error if returncode is non-zero AND it's not just a warning
                if process.returncode != 0:
                    stderr_lower = stderr_output.lower() if stderr_output else ""
                    is_warning_only = (
                        "warn:" in stderr_lower or "warning:" in stderr_lower
                    ) and stdout_text.strip()

                    if not is_warning_only:
                        error_msg = f"Claude CLI error: {stderr_output}"
                        logger.error(error_msg)
                        raise AgentError(error_msg, details={"returncode": process.returncode})

                if self.output_format == "json":
                    try:
                        result = json.loads(stdout_text)
                        logger.info("Successfully parsed JSON response")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        raise JSONParseError(stdout_text, str(e))
                else:
                    logger.info("Query completed successfully")
                    return {"result": stdout_text}
            else:
                logger.debug("Using non-streaming output mode")
                # Capture all output at once
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,  # Don't raise on non-zero exit, we'll check manually
                )

                # Check if there's actual output despite warnings in stderr
                # Bun/AVX warnings shouldn't be treated as fatal errors
                if result.returncode != 0:
                    # Check if stderr contains only warnings (not actual errors)
                    stderr_lower = result.stderr.lower() if result.stderr else ""
                    is_warning_only = (
                        "warn:" in stderr_lower or "warning:" in stderr_lower
                    ) and result.stdout.strip()  # Has actual output

                    if not is_warning_only:
                        # Provide more context in error message
                        error_msg = f"Claude CLI error (exit code {result.returncode})"
                        error_details = {"returncode": result.returncode}

                        if result.stderr:
                            error_msg += f": {result.stderr}"
                            error_details["stderr"] = result.stderr
                        else:
                            error_msg += ": No error message provided"
                        if result.stdout:
                            error_msg += f"\nStdout: {result.stdout[:200]}"
                            error_details["stdout_preview"] = result.stdout[:200]

                        logger.error(error_msg)
                        raise AgentError(error_msg, details=error_details)
                    else:
                        # Log warning but continue
                        if result.stderr:
                            logger.warning(f"Claude CLI warning: {result.stderr.strip()}")

                # Check if we have any output
                if not result.stdout or not result.stdout.strip():
                    error_msg = "Claude CLI returned no output"
                    error_details = {}
                    if result.stderr:
                        error_msg += f"\nStderr: {result.stderr}"
                        error_details["stderr"] = result.stderr
                    logger.error(error_msg)
                    raise AgentResponseError(error_msg, details=error_details)

                if self.output_format == "json":
                    try:
                        result_data = json.loads(result.stdout)
                        logger.info("Successfully parsed JSON response")
                        return result_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        raise JSONParseError(result.stdout, str(e))
                else:
                    logger.info("Query completed successfully")
                    return {"result": result.stdout}

        except subprocess.CalledProcessError as e:
            error_msg = f"Claude CLI subprocess error: {e.stderr}"
            logger.error(error_msg)
            raise AgentError(error_msg, details={"stderr": e.stderr})
        except JSONParseError:
            # Re-raise our custom exception
            raise
        except AgentError:
            # Re-raise our custom exceptions
            raise
        except AgentResponseError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Catch any other unexpected errors
            error_msg = f"Unexpected error during query execution: {str(e)}"
            logger.exception(error_msg)
            raise AgentError(error_msg, details={"original_error": str(e)})

    def query_with_stdin(
        self, prompt: str, stdin_content: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a query with stdin input.

        Args:
            prompt: The prompt to send
            stdin_content: Content to send via stdin
            system_prompt: Additional system prompt

        Returns:
            Dict containing response and metadata
        """
        additional_args = []

        if system_prompt:
            additional_args.extend(["--append-system-prompt", system_prompt])

        cmd = self._build_command(prompt, additional_args)

        logger.info("Executing Claude CLI query with stdin")
        logger.debug(f"Stdin content length: {len(stdin_content)} characters")

        try:
            result = subprocess.run(
                cmd, input=stdin_content, capture_output=True, text=True, check=True
            )

            if self.output_format == "json":
                try:
                    result_data = json.loads(result.stdout)
                    logger.info("Successfully parsed JSON response from stdin query")
                    return result_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise JSONParseError(result.stdout, str(e))
            else:
                logger.info("Stdin query completed successfully")
                return {"result": result.stdout}

        except subprocess.CalledProcessError as e:
            error_msg = f"Claude CLI error: {e.stderr}"
            logger.error(error_msg)
            raise AgentError(error_msg, details={"stderr": e.stderr, "returncode": e.returncode})
        except JSONParseError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during stdin query: {str(e)}"
            logger.exception(error_msg)
            raise AgentError(error_msg, details={"original_error": str(e)})

    def continue_conversation(
        self, prompt: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Continue a previous conversation.

        Args:
            prompt: The prompt to send
            session_id: Session ID to resume (None for most recent)

        Returns:
            Dict containing response and metadata
        """
        if session_id:
            cmd = ["claude", "--resume", session_id, prompt]
            logger.info(f"Resuming conversation with session ID: {session_id}")
        else:
            cmd = ["claude", "--continue", prompt]
            logger.info("Continuing most recent conversation")

        # Add output format
        if self.output_format:
            cmd.extend(["--output-format", self.output_format])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if self.output_format == "json":
                try:
                    result_data = json.loads(result.stdout)
                    logger.info("Successfully parsed JSON response from continued conversation")
                    return result_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise JSONParseError(result.stdout, str(e))
            else:
                logger.info("Conversation continued successfully")
                return {"result": result.stdout}

        except subprocess.CalledProcessError as e:
            error_msg = f"Claude CLI error: {e.stderr}"
            logger.error(error_msg)
            raise AgentError(error_msg, details={"stderr": e.stderr, "returncode": e.returncode})
        except JSONParseError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during conversation continuation: {str(e)}"
            logger.exception(error_msg)
            raise AgentError(error_msg, details={"original_error": str(e)})

    def code_review(self, file_path: str) -> Dict[str, Any]:
        """
        Perform a code review on a file.

        Args:
            file_path: Path to the file to review

        Returns:
            Dict containing review results
        """
        logger.info(f"Starting code review for file: {file_path}")

        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise CustomFileNotFoundError(file_path)

        try:
            with open(file_path, "r") as f:
                file_content = f.read()
            logger.debug(f"Successfully read file: {file_path} ({len(file_content)} characters)")
        except IOError as e:
            error_msg = f"Failed to read file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise FileOperationError(error_msg, details={"file_path": file_path, "error": str(e)})

        prompt = f"""Review this code for:
        1. Security vulnerabilities
        2. Performance issues
        3. Code quality and best practices
        4. Potential bugs
        5. Suggestions for improvement

        File: {file_path}

        Provide a structured analysis with severity levels."""

        result = self.query_with_stdin(prompt, file_content)
        logger.info(f"Code review completed for file: {file_path}")
        return result

    def generate_docs(self, file_path: str) -> Dict[str, Any]:
        """
        Generate documentation for a file.

        Args:
            file_path: Path to the file to document

        Returns:
            Dict containing generated documentation
        """
        logger.info(f"Generating documentation for file: {file_path}")

        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise CustomFileNotFoundError(file_path)

        try:
            with open(file_path, "r") as f:
                file_content = f.read()
            logger.debug(f"Successfully read file: {file_path} ({len(file_content)} characters)")
        except IOError as e:
            error_msg = f"Failed to read file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise FileOperationError(error_msg, details={"file_path": file_path, "error": str(e)})

        prompt = f"""Generate comprehensive documentation for this code including:
        1. Overview and purpose
        2. Function/class descriptions
        3. Parameters and return values
        4. Usage examples
        5. Dependencies

        File: {file_path}

        Format as Markdown."""

        result = self.query_with_stdin(prompt, file_content)
        logger.info(f"Documentation generation completed for file: {file_path}")
        return result

    def fix_code(self, file_path: str, issue_description: str) -> Dict[str, Any]:
        """
        Fix code issues.

        Args:
            file_path: Path to the file to fix
            issue_description: Description of the issue to fix

        Returns:
            Dict containing fix results
        """
        logger.info(f"Fixing code in file: {file_path}")
        logger.debug(f"Issue description: {issue_description}")

        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise CustomFileNotFoundError(file_path)

        try:
            with open(file_path, "r") as f:
                file_content = f.read()
            logger.debug(f"Successfully read file: {file_path} ({len(file_content)} characters)")
        except IOError as e:
            error_msg = f"Failed to read file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise FileOperationError(error_msg, details={"file_path": file_path, "error": str(e)})

        prompt = f"""Fix the following issue in this code:

        Issue: {issue_description}

        File: {file_path}

        Provide the fixed code and explanation of changes."""

        result = self.query_with_stdin(prompt, file_content)
        logger.info(f"Code fix completed for file: {file_path}")
        return result

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
        logger.info(f"Starting batch processing in directory: {directory}")
        logger.debug(f"File pattern: {file_pattern}, Prompt: {prompt[:100]}...")

        results = []
        path = Path(directory)

        if not path.exists():
            error_msg = f"Directory not found: {directory}"
            logger.error(error_msg)
            raise CustomFileNotFoundError(directory)

        if not path.is_dir():
            error_msg = f"Path is not a directory: {directory}"
            logger.error(error_msg)
            raise FileOperationError(error_msg, details={"path": directory})

        files_to_process = list(path.rglob(file_pattern))
        logger.info(f"Found {len(files_to_process)} files to process")

        for file_path in files_to_process:
            if file_path.is_file():
                try:
                    logger.debug(f"Processing file: {file_path}")
                    with open(file_path, "r") as f:
                        content = f.read()

                    result = self.query_with_stdin(
                        f"{prompt}\n\nFile: {file_path}", content
                    )
                    results.append(
                        {"file": str(file_path), "result": result, "success": True}
                    )
                    logger.info(f"Successfully processed file: {file_path}")
                except AutoGrowException as e:
                    logger.warning(f"Failed to process file {file_path}: {e.message}")
                    results.append(
                        {"file": str(file_path), "error": e.message, "success": False}
                    )
                except Exception as e:
                    logger.warning(f"Unexpected error processing file {file_path}: {str(e)}")
                    results.append(
                        {"file": str(file_path), "error": str(e), "success": False}
                    )

        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        logger.info(f"Batch processing completed: {successful} succeeded, {failed} failed")

        return results


def main():
    """Example usage of ClaudeAgent."""
    import sys

    try:
        logger.info("Starting ClaudeAgent example usage")
        agent = ClaudeAgent(verbose=True)

        logger.info("Claude CLI Agent - Python Interface")
        logger.info("=" * 50)

        # Example 1: Simple query
        logger.info("Running Example 1: Simple Query")
        result = agent.query("What are the best practices for Python error handling?")
        if "result" in result:
            logger.info(f"Query result: {result['result'][:200]}...")
        else:
            logger.info(f"Query result: {json.dumps(result, indent=2)[:200]}...")

        # Example 2: Code review (if file provided)
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            logger.info(f"Running Example 2: Code Review for {file_path}")
            result = agent.code_review(file_path)
            if "result" in result:
                logger.info(f"Review result: {result['result'][:200]}...")
            else:
                logger.info(f"Review result: {json.dumps(result, indent=2)[:200]}...")

        logger.info("Examples completed successfully")

    except AutoGrowException as e:
        logger.error(f"AutoGrow error occurred: {e.message}")
        if e.details:
            logger.error(f"Error details: {e.details}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
