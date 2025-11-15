# Seed Planter API

FastAPI-based REST API for planting and growing autonomous AI-driven projects.

## Purpose
Allows users to "plant" project seeds that grow into full-fledged autonomous projects. Creates permanent GitHub organizations, forks SeedGPT template, and deploys to GCP/GitHub Pages.

## Architecture Modes
1. **SaaS Freemium** (Phase 1): Projects run on SeedGPT's accounts
2. **User Environment** (Phase 2): Users connect their own GitHub/GCloud accounts

## Tech Stack
- **Framework**: FastAPI
- **WebSocket**: Real-time progress updates
- **AI**: Anthropic Claude API
- **VCS**: GitHub API, GitPython
- **Cloud**: Google Cloud Platform SDK
- **Deployment**: Docker, GitHub Pages

## Key Features
- Permanent project creation (not temporary)
- GitHub organization per project
- SeedGPT template fork and customization
- Automated GCP project setup
- Smart deployment (GitHub Pages or Docker)
- Real-time progress streaming
- Public projects under SeedGPT account
