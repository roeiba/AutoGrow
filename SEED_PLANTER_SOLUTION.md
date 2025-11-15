# Seed Planter Solution for Issue #69

## Overview

This document describes the professional implementation of the **Seed Planter** platform for SeedGPT, addressing [Issue #69](https://github.com/roeiba/SeedGPT/issues/69).

## Concept: From Sandbox to Seed Planter

Instead of temporary "sandbox" environments, we've built a **Seed Planter** - a platform where users "plant" project seeds that grow into permanent, autonomous AI-driven projects.

### The Metaphor
- **Seed**: User's project idea (name + description)
- **Pot**: Permanent infrastructure (GitHub org, GCP project)
- **Growth**: Autonomous AI-driven development
- **Harvest**: Deployed, running application

## Architecture

### Two Modes (Phased Approach)

#### Phase 1: SaaS Freemium Mode ✅ (Current Implementation)
- Everything runs on SeedGPT's accounts
- GitHub organizations created under SeedGPT account
- GCP projects under SeedGPT's GCP account
- Users get public projects they can later claim ownership of
- Simple, fast onboarding - no authentication needed

#### Phase 2: User Environment Mode (Future)
- Users connect their own GitHub account
- Users connect their own GCloud account
- OAuth authentication flow
- Projects run in user's infrastructure
- Full ownership from the start

## How It Works

### 1. User Plants a Seed
User provides:
- **Project Name**: Will become the GitHub organization name
- **Project Description**: Detailed prompt of what they want to build

### 2. Seed Planter Creates Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│                    SEED PLANTING PROCESS                     │
└─────────────────────────────────────────────────────────────┘

Step 1: Create GitHub Organization (10%)
  ├─ Sanitize project name → org name
  ├─ Create org under SeedGPT account
  └─ Add "seedgpt-project" label

Step 2: Fork SeedGPT Template (25%)
  ├─ Clone roeiba/SeedGPT repository
  ├─ Create new repo in organization
  └─ Push template code

Step 3: Customize Project (40%)
  ├─ Delete /apps folder (clean slate)
  ├─ AI generates custom PROJECT_BRIEF.md
  ├─ AI generates custom README.md
  └─ Commit and push changes

Step 4: Create GCP Project (60%)
  ├─ Generate unique GCP project ID
  ├─ Create project in SeedGPT's GCP account
  └─ Configure basic settings

Step 5: Deploy (75%)
  ├─ Analyze project type
  ├─ If simple page → Deploy to GitHub Pages
  ├─ If complex app → Deploy to GCP Cloud Run
  │   ├─ Build Docker images
  │   ├─ Push to GCR (Google Container Registry)
  │   └─ Deploy with min_instances=0 (cost-effective)
  └─ Return deployment URL

Step 6: Create Initial Issues (90%)
  ├─ AI generates relevant development tasks
  ├─ Create issues in GitHub
  └─ Ready for autonomous agents to work

Step 7: Complete (100%)
  └─ Project is planted and growing! 🌱
```

### 3. Project Grows Autonomously

Once planted, the project uses SeedGPT's autonomous workflow:
- AI agents pick up issues
- Code is written and reviewed
- PRs are created and merged
- Continuous deployment
- Self-evolving based on requirements

### 4. User Can Claim Ownership

At any time, users can:
- Transfer GitHub organization to their account
- Take over GCP project
- Continue development independently
- Or keep it running on SeedGPT infrastructure

## Technical Implementation

### Backend (Seed Planter API)

**Location**: `/apps/seed-planter-api/`

**Core Files**:
- `src/seed_planter.py` - Main planting logic
- `src/main.py` - FastAPI application
- `src/models.py` - Data models
- `src/config.py` - Configuration

**Key Features**:
- GitHub organization creation
- SeedGPT template forking
- AI-powered project customization
- GCP project setup
- Smart deployment (GitHub Pages vs Docker)
- Real-time WebSocket progress updates

**Tech Stack**:
- FastAPI 0.115.0
- Anthropic Claude API (project customization)
- PyGithub (GitHub operations)
- Google Cloud SDK (GCP operations)
- GitPython (Git operations)
- WebSockets (real-time updates)

### Frontend (Seed Planter UI)

**Location**: `/apps/seed-planter-frontend/`

**Core Files**:
- `src/App.jsx` - Main UI component
- `src/hooks/useSeedPlanter.js` - Planting logic hook

**Key Features**:
- Project name and description input
- Real-time planting progress
- WebSocket-based live updates
- Links to created resources
- Modern, responsive design

**Tech Stack**:
- React 18.3.1
- Vite 5.4.10
- TailwindCSS 3.4.14
- Lucide React (icons)

## API Endpoints

### POST /api/v1/projects
Plant a new project seed.

**Request**:
```json
{
  "project_name": "TaskMaster",
  "project_description": "A task management app for remote teams with real-time collaboration",
  "mode": "saas",
  "user_email": "user@example.com"
}
```

**Response**:
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "initializing",
  "created_at": "2025-11-15T17:00:00Z",
  "websocket_url": "ws://localhost:8000/api/v1/projects/{id}/ws",
  "estimated_completion_time": 120
}
```

### WS /api/v1/projects/{project_id}/ws
Real-time progress updates.

**Progress Messages**:
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "creating_org",
  "message": "Creating GitHub organization 'taskmaster-251115'...",
  "progress_percent": 10,
  "timestamp": "2025-11-15T17:00:10Z",
  "org_url": "https://github.com/taskmaster-251115",
  "repo_url": null,
  "deployment_url": null,
  "gcp_project_id": null
}
```

### GET /api/v1/projects/{project_id}
Get project details.

### GET /api/v1/projects
List all planted projects.

### POST /api/v1/projects/{project_id}/transfer
Transfer project ownership to user.

## Deployment Strategy

### Simple Page Apps → GitHub Pages
- Static HTML/CSS/JS sites
- React/Vue/Angular SPAs
- Documentation sites
- Landing pages

**Benefits**:
- Free hosting
- Automatic HTTPS
- Fast CDN
- Zero maintenance

### Complex Apps → GCP Cloud Run + Docker
- Backend APIs
- Full-stack applications
- Microservices
- Database-backed apps

**Benefits**:
- Scales to zero (min_instances=0)
- Pay only for actual usage
- Auto-scaling
- Managed infrastructure

**Cost Optimization**:
- Minimum instances: 0
- Maximum instances: 10
- Only charged when requests come in
- Extremely cost-effective for demos

## Configuration

### Backend Environment Variables

```bash
# GitHub (SeedGPT's account)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
GITHUB_USERNAME=roeiba
SEEDGPT_TEMPLATE_REPO=roeiba/SeedGPT

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Google Cloud (SeedGPT's account)
GCP_PROJECT_ID=seedgpt
GCP_CREDENTIALS_PATH=/path/to/service-account.json
GCP_REGION=us-central1

# Deployment
DOCKER_REGISTRY=gcr.io
MIN_INSTANCES=0
MAX_INSTANCES=10
```

## Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+
- GitHub account with PAT
- Anthropic API key
- Google Cloud account (for Phase 1)

### Quick Start

1. **Configure Backend**:
   ```bash
   cd apps/seed-planter-api
   cp .env.example .env
   # Edit .env with your credentials
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cd src && python main.py
   ```

2. **Configure Frontend**:
   ```bash
   cd apps/seed-planter-frontend
   cp .env.example .env
   npm install
   npm run dev
   ```

3. **Access**:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## User Flow Example

1. **User visits** http://localhost:3000
2. **Enters project details**:
   - Name: "TaskMaster"
   - Description: "A task management app for remote teams"
3. **Clicks "Plant Seed"**
4. **Watches real-time progress**:
   - ✓ Creating organization "taskmaster-251115"
   - ✓ Forking SeedGPT template
   - ✓ Customizing with AI
   - ✓ Setting up GCP project
   - ✓ Deploying to Cloud Run
   - ✓ Creating initial issues
5. **Receives links**:
   - GitHub Org: https://github.com/taskmaster-251115
   - Repository: https://github.com/taskmaster-251115/taskmaster-251115-main
   - Live App: https://taskmaster-251115.run.app
6. **Project grows autonomously**
7. **User can transfer ownership** when ready

## Key Differences from Original Sandbox Concept

| Aspect | Original Sandbox | Seed Planter |
|--------|-----------------|--------------|
| **Purpose** | Temporary demo | Permanent project |
| **Lifetime** | 1 hour TTL | Permanent |
| **Infrastructure** | Temporary repos | Real GitHub orgs |
| **Deployment** | None | GitHub Pages or GCP |
| **Ownership** | Demo only | Transferable to user |
| **Cost** | Free (temporary) | Minimal (pay-per-use) |
| **Value** | See capabilities | Get real project |

## Business Model

### SaaS Freemium (Phase 1)
- **Free Tier**: 
  - Plant up to 3 projects
  - Public repositories
  - Basic deployment
  - Community support

- **Pro Tier** ($15/month):
  - Unlimited projects
  - Private repositories option
  - Priority deployment
  - Email support

- **Enterprise** (Custom):
  - User environment mode
  - Custom infrastructure
  - Dedicated support
  - SLA guarantees

### Revenue Streams
1. **Subscription fees** (Pro/Enterprise tiers)
2. **Infrastructure markup** (costs + 15%)
3. **Project transfer fees** (one-time)
4. **Premium features** (advanced AI, custom templates)

## Future Enhancements

1. **Phase 2: User Environment Mode**
   - OAuth for GitHub/GCloud
   - Run in user's accounts
   - Full ownership from start

2. **Project Templates**
   - Pre-built templates for common use cases
   - E-commerce, SaaS, Blog, etc.
   - One-click deployment

3. **Collaboration Features**
   - Team projects
   - Shared ownership
   - Role-based access

4. **Advanced AI**
   - Custom AI models
   - Fine-tuned for specific domains
   - Learning from project evolution

5. **Marketplace**
   - Share project templates
   - Sell successful projects
   - Community contributions

## Success Metrics

- **Planting Rate**: Projects planted per day
- **Growth Rate**: Active autonomous development
- **Transfer Rate**: % of projects transferred to users
- **Deployment Success**: % successfully deployed
- **User Retention**: Returning users
- **Revenue**: Subscription + infrastructure fees

## Conclusion

The Seed Planter transforms the original sandbox concept into a **permanent, value-generating platform**. Instead of temporary demos, users get real, growing projects that can become their next business.

**Key Value Propositions**:
✅ Instant project creation (< 2 minutes)  
✅ Permanent infrastructure (not temporary)  
✅ Autonomous growth (AI-driven development)  
✅ Smart deployment (GitHub Pages or Docker)  
✅ Transferable ownership (take it when ready)  
✅ Cost-effective (pay only for usage)  

The platform reduces friction in the conversion funnel while providing immediate, tangible value - a real project that users can own, grow, and potentially monetize.

---

**Related Files**:
- Backend: `/apps/seed-planter-api/`
- Frontend: `/apps/seed-planter-frontend/`
- Issue: [#69](https://github.com/roeiba/SeedGPT/issues/69)
