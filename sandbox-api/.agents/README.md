# Sandbox API

FastAPI-based REST API for managing isolated preview environments where users can test AutoGrow functionality.

## Purpose
Provides instant AI-generated demos by creating temporary GitHub repositories, generating project structures, issues, and PRs in real-time.

## Tech Stack
- **Framework**: FastAPI
- **WebSocket**: Real-time progress updates
- **Storage**: Redis for session management
- **AI**: Anthropic Claude API
- **VCS**: GitHub API, GitPython

## Key Features
- Isolated sandbox environments
- Real-time demo generation
- Automatic cleanup
- WebSocket progress streaming
- Rate limiting and security
