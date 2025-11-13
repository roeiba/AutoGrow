#!/usr/bin/env python3
"""
Claude CLI Agent - Python wrapper for Claude Code CLI headless mode
Provides a Python interface to interact with Claude CLI in headless mode
"""

import json
import os
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path


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
        permission_mode: Optional[str] = None
    ):
        """
        Initialize the Claude CLI Agent.
        
        Args:
            output_format: Output format (text, json, stream-json)
            verbose: Enable verbose output
            allowed_tools: List of allowed tools
            disallowed_tools: List of disallowed tools
            permission_mode: Permission mode (acceptEdits, etc.)
        """
        self.output_format = output_format
        self.verbose = verbose
        self.allowed_tools = allowed_tools
        self.disallowed_tools = disallowed_tools
        self.permission_mode = permission_mode
        
        # Check if claude CLI is installed
        if not self._is_claude_installed():
            raise RuntimeError(
                "Claude Code CLI is not installed. Install it from:\n"
                "  https://code.claude.com/"
            )
    
    def _is_claude_installed(self) -> bool:
        """Check if claude CLI is installed."""
        try:
            subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _build_command(
        self,
        prompt: str,
        additional_args: Optional[List[str]] = None
    ) -> List[str]:
        """
        Build the claude CLI command.
        
        Args:
            prompt: The prompt to send
            additional_args: Additional command line arguments
            
        Returns:
            List of command arguments
        """
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
        
        # Add permission mode
        if self.permission_mode:
            cmd.extend(["--permission-mode", self.permission_mode])
        
        # Add any additional arguments
        if additional_args:
            cmd.extend(additional_args)
        
        return cmd
    
    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        mcp_config: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a query to Claude in headless mode.
        
        Args:
            prompt: The prompt to send
            system_prompt: Additional system prompt
            mcp_config: Path to MCP configuration file
            
        Returns:
            Dict containing response and metadata
        """
        additional_args = []
        
        if system_prompt:
            additional_args.extend(["--append-system-prompt", system_prompt])
        
        if mcp_config:
            additional_args.extend(["--mcp-config", mcp_config])
        
        cmd = self._build_command(prompt, additional_args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if self.output_format == "json":
                return json.loads(result.stdout)
            else:
                return {"result": result.stdout}
                
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Claude CLI error: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON response: {e}")
    
    def query_with_stdin(
        self,
        prompt: str,
        stdin_content: str,
        system_prompt: Optional[str] = None
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
        
        try:
            result = subprocess.run(
                cmd,
                input=stdin_content,
                capture_output=True,
                text=True,
                check=True
            )
            
            if self.output_format == "json":
                return json.loads(result.stdout)
            else:
                return {"result": result.stdout}
                
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Claude CLI error: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON response: {e}")
    
    def continue_conversation(
        self,
        prompt: str,
        session_id: Optional[str] = None
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
        else:
            cmd = ["claude", "--continue", prompt]
        
        # Add output format
        if self.output_format:
            cmd.extend(["--output-format", self.output_format])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if self.output_format == "json":
                return json.loads(result.stdout)
            else:
                return {"result": result.stdout}
                
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Claude CLI error: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON response: {e}")
    
    def code_review(self, file_path: str) -> Dict[str, Any]:
        """
        Perform a code review on a file.
        
        Args:
            file_path: Path to the file to review
            
        Returns:
            Dict containing review results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r') as f:
            file_content = f.read()
        
        prompt = f"""Review this code for:
        1. Security vulnerabilities
        2. Performance issues
        3. Code quality and best practices
        4. Potential bugs
        5. Suggestions for improvement
        
        File: {file_path}
        
        Provide a structured analysis with severity levels."""
        
        return self.query_with_stdin(prompt, file_content)
    
    def generate_docs(self, file_path: str) -> Dict[str, Any]:
        """
        Generate documentation for a file.
        
        Args:
            file_path: Path to the file to document
            
        Returns:
            Dict containing generated documentation
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r') as f:
            file_content = f.read()
        
        prompt = f"""Generate comprehensive documentation for this code including:
        1. Overview and purpose
        2. Function/class descriptions
        3. Parameters and return values
        4. Usage examples
        5. Dependencies
        
        File: {file_path}
        
        Format as Markdown."""
        
        return self.query_with_stdin(prompt, file_content)
    
    def fix_code(self, file_path: str, issue_description: str) -> Dict[str, Any]:
        """
        Fix code issues.
        
        Args:
            file_path: Path to the file to fix
            issue_description: Description of the issue to fix
            
        Returns:
            Dict containing fix results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r') as f:
            file_content = f.read()
        
        prompt = f"""Fix the following issue in this code:

        Issue: {issue_description}
        
        File: {file_path}
        
        Provide the fixed code and explanation of changes."""
        
        return self.query_with_stdin(prompt, file_content)
    
    def batch_process(
        self,
        directory: str,
        prompt: str,
        file_pattern: str = "*.py"
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
        results = []
        path = Path(directory)
        
        for file_path in path.rglob(file_pattern):
            if file_path.is_file():
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    result = self.query_with_stdin(
                        f"{prompt}\n\nFile: {file_path}",
                        content
                    )
                    results.append({
                        "file": str(file_path),
                        "result": result,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "file": str(file_path),
                        "error": str(e),
                        "success": False
                    })
        
        return results


def main():
    """Example usage of ClaudeAgent."""
    import sys
    
    try:
        agent = ClaudeAgent(verbose=True)
        
        print("🤖 Claude CLI Agent - Python Interface")
        print("=" * 50)
        
        # Example 1: Simple query
        print("\n1. Simple Query:")
        result = agent.query("What are the best practices for Python error handling?")
        if "result" in result:
            print(result["result"])
        else:
            print(json.dumps(result, indent=2))
        
        # Example 2: Code review (if file provided)
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            print(f"\n2. Code Review: {file_path}")
            result = agent.code_review(file_path)
            if "result" in result:
                print(result["result"])
            else:
                print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
