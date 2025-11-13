# Retry Logic and Exponential Backoff

## Overview

AutoGrow now includes comprehensive retry logic with exponential backoff and jitter for all API calls to Anthropic and GitHub. This prevents cascading failures from network issues, rate limiting, and temporary service disruptions.

## Features

### 1. Exponential Backoff
- Delays between retries increase exponentially (1s → 2s → 4s → 8s...)
- Prevents overwhelming the API with rapid retry attempts
- Configurable base delay, multiplier, and maximum delay

### 2. Jitter
- Adds randomness to retry delays (±10-20% depending on service)
- Prevents "thundering herd" problem when multiple agents retry simultaneously
- Distributes retry load more evenly across time

### 3. Rate Limit Handling
- Automatically detects rate limit errors
- Uses longer delays for rate-limited requests
- Allows services time to recover before retry

### 4. Service-Specific Configuration
- **Anthropic API**: 5 retries, 1s base delay, 60s max delay
- **GitHub API**: 5 retries, 2s base delay, 120s max delay
- **Network calls**: 3 retries, 0.5s base delay, 30s max delay

## Implementation

### Module Location
```
src/utils/retry_handler.py
```

### Key Components

#### 1. Decorators
```python
from utils.retry_handler import retry_anthropic_api, retry_github_api

@retry_anthropic_api
def call_claude_api(prompt):
    # Your Anthropic API call
    pass

@retry_github_api
def get_issues():
    # Your GitHub API call
    pass
```

#### 2. Context Manager
```python
from utils.retry_handler import RetryableAPICall

with RetryableAPICall(max_retries=3, base_delay=1.0) as retry:
    result = retry.execute(lambda: some_api_call())
```

#### 3. Custom Configuration
```python
from utils.retry_handler import retry_with_backoff

@retry_with_backoff(
    max_retries=5,
    base_delay=2.0,
    max_delay=120.0,
    multiplier=2.0,
    jitter_range=0.15,
    exceptions=(ConnectionError, TimeoutError),
    rate_limit_exceptions=(RateLimitError,)
)
def custom_api_call():
    pass
```

## Retry Behavior

### Example Timeline

For a failed Anthropic API call:

```
Attempt 1: ⚠️ Failed
  ⏳ Wait 1.0s (±10% jitter)

Attempt 2: ⚠️ Failed
  ⏳ Wait 2.0s (±10% jitter)

Attempt 3: ⚠️ Failed
  ⏳ Wait 4.0s (±10% jitter)

Attempt 4: ⚠️ Failed
  ⏳ Wait 8.0s (±10% jitter)

Attempt 5: ⚠️ Failed
  ⏳ Wait 16.0s (±10% jitter)

Attempt 6: ❌ Max retries exceeded - raise exception
```

### Rate Limit Example

For a rate-limited GitHub API call:

```
Attempt 1: ⚠️ Rate Limited (429)
  ⏳ Wait 4.0s (longer delay for rate limits)

Attempt 2: ✅ Success
```

## Agent Integration

### Issue Generator Agent
All GitHub and Anthropic API calls are wrapped with retry logic:
- ✅ `repo.get_issues()` - Get open issues
- ✅ `repo.get_readme()` - Get README content
- ✅ `repo.get_commits()` - Get recent commits
- ✅ `client.messages.create()` - Anthropic API calls
- ✅ `repo.create_issue()` - Create new issues

### QA Agent
All GitHub and Anthropic API calls are wrapped with retry logic:
- ✅ `repo.get_issues()` - Get issues for review
- ✅ `repo.get_pulls()` - Get pull requests
- ✅ `repo.get_commits()` - Get commits
- ✅ `client.messages.create()` - Anthropic API calls
- ✅ `repo.create_issue()` - Create QA reports

### Issue Resolver Agent
All GitHub API calls are wrapped with retry logic:
- ✅ `repo.get_issues()` - Find issues to resolve
- ✅ `repo.get_readme()` - Get context
- ✅ `issue.get_comments()` - Check if issue is claimed
- ✅ `issue.create_comment()` - Post updates
- ✅ `issue.add_to_labels()` - Add labels
- ✅ `issue.remove_from_labels()` - Remove labels
- ✅ `repo.create_pull()` - Create pull requests

## Benefits

### 1. Resilience
- **Network failures**: Automatically retry transient network issues
- **Service disruptions**: Handle temporary API outages gracefully
- **Rate limits**: Respect API rate limits without crashing

### 2. Reliability
- **No cascading failures**: One failed API call doesn't crash the entire workflow
- **Predictable behavior**: Consistent retry strategy across all agents
- **Logging**: All retry attempts are logged for debugging

### 3. Performance
- **Jitter prevents thundering herd**: Multiple agents don't retry simultaneously
- **Exponential backoff**: Gives services time to recover
- **Max retries**: Prevents infinite retry loops

## Configuration

### RetryConfig Class
```python
class RetryConfig:
    # Anthropic API
    ANTHROPIC_MAX_RETRIES = 5
    ANTHROPIC_BASE_DELAY = 1.0
    ANTHROPIC_MAX_DELAY = 60.0
    ANTHROPIC_BACKOFF_MULTIPLIER = 2.0
    ANTHROPIC_JITTER_RANGE = 0.1

    # GitHub API
    GITHUB_MAX_RETRIES = 5
    GITHUB_BASE_DELAY = 2.0
    GITHUB_MAX_DELAY = 120.0
    GITHUB_BACKOFF_MULTIPLIER = 2.0
    GITHUB_JITTER_RANGE = 0.15

    # Network
    NETWORK_MAX_RETRIES = 3
    NETWORK_BASE_DELAY = 0.5
    NETWORK_MAX_DELAY = 30.0
    NETWORK_BACKOFF_MULTIPLIER = 2.0
    NETWORK_JITTER_RANGE = 0.2
```

## Error Handling

### Anthropic API Errors
- `APIConnectionError`: Network connection issues
- `APITimeoutError`: Request timeout
- `InternalServerError`: Server-side errors
- `RateLimitError`: Rate limit exceeded (uses longer delays)

### GitHub API Errors
- `GithubException`: General GitHub API errors
- `RateLimitExceededException`: Rate limit exceeded (uses longer delays)

### Network Errors
- `ConnectionError`: Network connection failed
- `Timeout`: Request timeout
- `RequestException`: General request errors
- `OSError`: Low-level network errors

## Testing

### Unit Tests
```bash
python -m pytest tests/unit/test_retry_handler.py -v
```

### Manual Testing
```python
# Test exponential backoff
from utils.retry_handler import calculate_backoff_delay

for attempt in range(5):
    delay = calculate_backoff_delay(attempt, 1.0, 60.0, 2.0, 0.0)
    print(f"Attempt {attempt}: {delay}s")
```

## Logging

All retry attempts are logged with the following format:
```
⚠️ Error in function_name (attempt 2/5). Retrying in 2.34s... Error: Connection timeout
```

Rate limit retries include additional context:
```
⚠️ Rate limited in function_name (attempt 1/5). Retrying in 4.12s... Error: API rate limit exceeded
```

## Best Practices

1. **Use service-specific decorators**: `@retry_anthropic_api` and `@retry_github_api` are pre-configured
2. **Don't wrap non-idempotent operations**: Only retry safe operations
3. **Monitor logs**: Check for frequent retries indicating systemic issues
4. **Adjust configuration**: Tune retry parameters for your use case
5. **Handle terminal failures**: Catch exceptions after max retries for graceful degradation

## Future Enhancements

- Circuit breaker pattern to prevent retry storms
- Adaptive retry delays based on response headers
- Metrics collection for retry analysis
- Per-endpoint retry configuration
- Retry budget to limit total retry time

## References

- [Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Anthropic API Documentation](https://docs.anthropic.com/claude/reference/errors)
- [GitHub API Rate Limiting](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting)
