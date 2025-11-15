# SeedGPT Sandbox API

FastAPI-based REST API for managing isolated preview environments where users can test AutoGrow functionality in real-time.

## Overview

The Sandbox API creates temporary GitHub repositories with AI-generated project structures, issues, and pull requests, allowing users to experience AutoGrow's capabilities before committing resources.

## Features

- **Isolated Environments**: Each sandbox runs in its own temporary GitHub repository
- **Real-time Updates**: WebSocket support for live progress streaming
- **AI-Powered Generation**: Uses Claude AI to generate project structures
- **Automatic Cleanup**: Sandboxes expire after configurable TTL
- **Rate Limiting**: Prevents abuse with IP-based rate limiting
- **Security**: Input validation, CORS protection, and secure credential handling

## Architecture

```
sandbox-api/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   └── sandbox_manager.py   # Core sandbox orchestration
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```

## Setup

### Prerequisites

- Python 3.11+
- GitHub Personal Access Token
- Anthropic API Key
- Redis (optional, for production)

### Installation

1. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Run the API**:
   ```bash
   cd src
   python main.py
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /
```
Returns API status and version.

### Create Sandbox
```
POST /api/v1/sandboxes
Content-Type: application/json

{
  "project_idea": "A task management app for remote teams",
  "user_email": "user@example.com"  // optional
}
```

Returns:
```json
{
  "sandbox_id": "uuid",
  "status": "initializing",
  "created_at": "2025-11-15T17:00:00Z",
  "expires_at": "2025-11-15T18:00:00Z",
  "websocket_url": "ws://localhost:8000/api/v1/sandboxes/{id}/ws"
}
```

### Get Sandbox Details
```
GET /api/v1/sandboxes/{sandbox_id}
```

### List Active Sandboxes
```
GET /api/v1/sandboxes
```

### WebSocket Connection
```
WS /api/v1/sandboxes/{sandbox_id}/ws
```

Receives real-time progress updates:
```json
{
  "sandbox_id": "uuid",
  "status": "creating_repo",
  "message": "Creating temporary GitHub repository...",
  "progress_percent": 10,
  "timestamp": "2025-11-15T17:00:10Z",
  "repo_url": "https://github.com/org/demo-abc123"
}
```

### Delete Sandbox
```
DELETE /api/v1/sandboxes/{sandbox_id}
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | API host | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `GITHUB_TOKEN` | GitHub PAT | Required |
| `ANTHROPIC_API_KEY` | Claude API key | Required |
| `SANDBOX_TTL` | Sandbox lifetime (seconds) | `3600` |
| `MAX_SANDBOXES_PER_IP` | Max concurrent sandboxes per IP | `3` |

## Development

### Running Tests
```bash
pytest tests/
```

### API Documentation
Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Debugging
Enable debug mode in `.env`:
```
API_DEBUG=true
```

## Deployment

### Docker
```bash
docker build -t seedgpt-sandbox-api .
docker run -p 8000:8000 --env-file .env seedgpt-sandbox-api
```

### Production Considerations

1. **Use Redis**: Configure Redis for session management
2. **HTTPS**: Deploy behind reverse proxy with SSL
3. **Rate Limiting**: Adjust limits based on usage
4. **Monitoring**: Add logging and metrics collection
5. **Cleanup Jobs**: Schedule periodic cleanup of expired sandboxes

## Security

- All inputs are validated using Pydantic models
- CORS is configured with explicit origins
- GitHub tokens are never exposed to clients
- Sandboxes are isolated and temporary
- Rate limiting prevents abuse

## Troubleshooting

### Common Issues

**API won't start**:
- Check `.env` file exists and has valid credentials
- Verify Python version is 3.11+
- Ensure port 8000 is available

**WebSocket connection fails**:
- Check CORS configuration
- Verify sandbox_id is valid
- Check browser console for errors

**GitHub API errors**:
- Verify GitHub token has repo creation permissions
- Check rate limits on GitHub API
- Ensure organization (if used) allows repo creation

## License

Part of the SeedGPT project.
