"""
Custom exception hierarchy for AutoGrow project.

Provides specific exception types for better error handling and debugging.
All exceptions inherit from a base AutoGrowException for easy catching.
"""


class AutoGrowException(Exception):
    """Base exception for all AutoGrow errors."""

    def __init__(self, message: str, details: dict = None):
        """
        Initialize exception with message and optional details.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# ============================================================================
# Configuration and Setup Errors
# ============================================================================

class ConfigurationError(AutoGrowException):
    """Raised when configuration is invalid or missing."""
    pass


class MissingEnvironmentVariableError(ConfigurationError):
    """Raised when required environment variable is not set."""

    def __init__(self, var_name: str):
        super().__init__(
            f"Required environment variable '{var_name}' is not set",
            details={"variable": var_name}
        )


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values are invalid."""
    pass


# ============================================================================
# API and External Service Errors
# ============================================================================

class APIError(AutoGrowException):
    """Base class for API-related errors."""
    pass


class GitHubAPIError(APIError):
    """Raised when GitHub API calls fail."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message, details={
            "status_code": status_code,
            "response": response
        })
        self.status_code = status_code
        self.response = response


class AnthropicAPIError(APIError):
    """Raised when Anthropic API calls fail."""

    def __init__(self, message: str, status_code: int = None, error_type: str = None):
        super().__init__(message, details={
            "status_code": status_code,
            "error_type": error_type
        })
        self.status_code = status_code
        self.error_type = error_type


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, service: str, retry_after: int = None):
        super().__init__(
            f"{service} API rate limit exceeded",
            details={
                "service": service,
                "retry_after": retry_after
            }
        )
        self.service = service
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Raised when API authentication fails."""
    pass


# ============================================================================
# Git and Repository Errors
# ============================================================================

class GitError(AutoGrowException):
    """Base class for Git-related errors."""
    pass


class BranchError(GitError):
    """Raised when branch operations fail."""
    pass


class CommitError(GitError):
    """Raised when commit operations fail."""
    pass


class PushError(GitError):
    """Raised when push operations fail."""
    pass


class MergeConflictError(GitError):
    """Raised when merge conflicts are detected."""

    def __init__(self, files: list = None):
        super().__init__(
            "Merge conflict detected",
            details={"conflicting_files": files}
        )
        self.files = files or []


class DirtyWorkingTreeError(GitError):
    """Raised when working tree has uncommitted changes."""
    pass


# ============================================================================
# Issue and PR Management Errors
# ============================================================================

class IssueError(AutoGrowException):
    """Base class for issue-related errors."""
    pass


class IssueNotFoundError(IssueError):
    """Raised when specified issue doesn't exist."""

    def __init__(self, issue_number: int):
        super().__init__(
            f"Issue #{issue_number} not found",
            details={"issue_number": issue_number}
        )
        self.issue_number = issue_number


class InvalidIssueFormatError(IssueError):
    """Raised when issue format is invalid."""
    pass


class DuplicateIssueError(IssueError):
    """Raised when attempting to create duplicate issue."""

    def __init__(self, title: str, existing_issue_number: int = None):
        super().__init__(
            f"Duplicate issue detected: '{title}'",
            details={
                "title": title,
                "existing_issue": existing_issue_number
            }
        )
        self.title = title
        self.existing_issue_number = existing_issue_number


class PullRequestError(AutoGrowException):
    """Base class for pull request errors."""
    pass


class PRCreationError(PullRequestError):
    """Raised when PR creation fails."""
    pass


class PRUpdateError(PullRequestError):
    """Raised when PR update fails."""
    pass


# ============================================================================
# AI Agent Errors
# ============================================================================

class AgentError(AutoGrowException):
    """Base class for AI agent errors."""
    pass


class AgentResponseError(AgentError):
    """Raised when AI agent response is invalid or unparseable."""
    pass


class AgentTimeoutError(AgentError):
    """Raised when AI agent operation times out."""

    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            f"Agent operation '{operation}' timed out after {timeout_seconds}s",
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds
            }
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class JSONParseError(AgentError):
    """Raised when JSON response from agent cannot be parsed."""

    def __init__(self, response_text: str, parse_error: str):
        super().__init__(
            f"Failed to parse JSON response: {parse_error}",
            details={
                "response_preview": response_text[:200],
                "parse_error": parse_error
            }
        )
        self.response_text = response_text
        self.parse_error = parse_error


# ============================================================================
# Validation and Data Errors
# ============================================================================

class ValidationError(AutoGrowException):
    """Raised when validation fails."""
    pass


class ProjectBriefValidationError(ValidationError):
    """Raised when project brief validation fails."""

    def __init__(self, errors: list):
        super().__init__(
            "Project brief validation failed",
            details={"errors": errors}
        )
        self.errors = errors


class InvalidLabelError(ValidationError):
    """Raised when issue label is invalid."""

    def __init__(self, label: str, valid_labels: list = None):
        super().__init__(
            f"Invalid label: '{label}'",
            details={
                "label": label,
                "valid_labels": valid_labels
            }
        )
        self.label = label
        self.valid_labels = valid_labels


# ============================================================================
# File and I/O Errors
# ============================================================================

class FileOperationError(AutoGrowException):
    """Base class for file operation errors."""
    pass


class FileNotFoundError(FileOperationError):
    """Raised when required file is not found."""

    def __init__(self, file_path: str):
        super().__init__(
            f"File not found: {file_path}",
            details={"file_path": file_path}
        )
        self.file_path = file_path


class FileReadError(FileOperationError):
    """Raised when file read operation fails."""
    pass


class FileWriteError(FileOperationError):
    """Raised when file write operation fails."""
    pass


# ============================================================================
# Retry and Timeout Errors
# ============================================================================

class RetryExhaustedError(AutoGrowException):
    """Raised when retry attempts are exhausted."""

    def __init__(self, operation: str, attempts: int, last_error: Exception = None):
        super().__init__(
            f"Operation '{operation}' failed after {attempts} attempts",
            details={
                "operation": operation,
                "attempts": attempts,
                "last_error": str(last_error) if last_error else None
            }
        )
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error


class TimeoutError(AutoGrowException):
    """Raised when operation times out."""

    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            f"Operation '{operation}' timed out after {timeout_seconds}s",
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds
            }
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


# ============================================================================
# Utility Functions
# ============================================================================

def get_exception_for_github_error(error, default_message: str = None) -> GitHubAPIError:
    """
    Convert GitHub API error to appropriate exception.

    Args:
        error: GitHub API error
        default_message: Default message if none can be extracted

    Returns:
        GitHubAPIError with appropriate details
    """
    message = default_message or str(error)
    status_code = None
    response = None

    if hasattr(error, 'status'):
        status_code = error.status

    if hasattr(error, 'data'):
        response = error.data
        if isinstance(response, dict) and 'message' in response:
            message = response['message']

    # Check for rate limiting
    if status_code == 403 and 'rate limit' in message.lower():
        retry_after = None
        if hasattr(error, 'headers') and 'X-RateLimit-Reset' in error.headers:
            retry_after = int(error.headers['X-RateLimit-Reset'])
        return RateLimitError('GitHub', retry_after)

    # Check for authentication
    if status_code == 401:
        return AuthenticationError(f"GitHub authentication failed: {message}")

    return GitHubAPIError(message, status_code, response)


def get_exception_for_anthropic_error(error, default_message: str = None) -> AnthropicAPIError:
    """
    Convert Anthropic API error to appropriate exception.

    Args:
        error: Anthropic API error
        default_message: Default message if none can be extracted

    Returns:
        AnthropicAPIError with appropriate details
    """
    message = default_message or str(error)
    status_code = None
    error_type = None

    if hasattr(error, 'status_code'):
        status_code = error.status_code

    if hasattr(error, 'error') and isinstance(error.error, dict):
        error_type = error.error.get('type')
        if 'message' in error.error:
            message = error.error['message']

    # Check for rate limiting
    if error_type == 'rate_limit_error' or (status_code == 429):
        return RateLimitError('Anthropic')

    # Check for authentication
    if status_code == 401 or error_type == 'authentication_error':
        return AuthenticationError(f"Anthropic authentication failed: {message}")

    return AnthropicAPIError(message, status_code, error_type)
