## 🎯 Project Overview

**Project Name**: SeedGPT

**Goal**: Build a profitable online business that grows autonomously.

**Brief Description**: 
An autonomous project that self-evolves using AI. SeedGPT independently drives development, manages operations, and scales sustainably, ensuring continuous growth and profitability.

**Problem Statement**:
People want solutions without hassle. Most desire a ready app, product, business, or automated workflow to meet their needs, while a few prefer to build it themselves.

**Target Users**:
Anyone seeking effortless solutions through technology—from entrepreneurs building businesses to developers creating automated workflows and processes.

**Proposed Solution**:
SeedGPT employs AI agents to autonomously generate tasks, write code, submit pull requests, and maintain quality. It can build and manage various types of projects:

- **Applications & Businesses:** Oversees deployment, analytics, marketing, and sales via a self-sustaining task cycle. Creates marketing content, creatives, social media posts, blogs, games, and other relevant materials.

- **Workflows & Automation:** Develops data pipelines, scheduled tasks, API integrations, CI/CD pipelines, monitoring systems, and any automated process that runs in the background.

- **Developer Tools:** Creates CLI tools, build systems, testing frameworks, and DevOps scripts.

Once mature, SeedGPT acts as a foundational seed for any venture or automation, adaptable to diverse projects and use cases.

Start with a B2C and B2B platform allowing users to initiate and manage projects. Users input a project idea, and SeedGPT establishes the framework, nurturing it to grow independently.

Users can choose to manage projects with their own credentials or use our SaaS model in our managed environment, billed at "costs + 15%" for operational expenses.

**Human-in-the-Loop Control**:
While SeedGPT operates autonomously, humans remain in full control as the "gardeners" of their seeds:

- **Frequency Tuning**: Each seed owner adjusts agent execution frequencies via GitHub Actions cron schedules. Speed up product development, slow down marketing, or pause any agent as needed.

- **Budget Management**: Owners set and monitor AI API spending limits through workflow configurations. Track costs via GitHub Actions logs and disable workflows to control expenses.

- **Backlog Curation**: Humans actively shape the development roadmap by creating custom issues, closing unwanted tasks, and using labels to prioritize what agents tackle next.

- **PR Approval Gate**: Every code change requires human review. Owners approve PRs that meet standards, request modifications for iteration, or reject changes that miss the mark. No code merges without explicit approval.

- **Customization Freedom**: Each seed instance is uniquely tuned by its owner. Different projects can have different agent frequencies, budget allocations, and development priorities based on individual needs and resources.

This hybrid model ensures AI handles the heavy lifting while humans maintain strategic control, quality standards, and final decision-making authority.

**Business Model**:
A SaaS framework charging "costs + 15%" on operational expenses.

**Technical Details**:
SeedGPT integrates with key services for business management, including e-commerce, advertising, marketing, content, and social media. It leverages Cloudflare for DNS and CDN, GitHub for version control and CI/CD, and Google Cloud for infrastructure.
It intelligently uses libraries and frameworks, semantically caches requests, and applies boilerplates for efficiency. The project root remains organized and uncluttered.
The `.agents` folder in each directory houses AI and agent data. Subfolders represent individual apps, with `README.md` files detailing specific app information.

## 🎯 Core Requirements

**Autonomous Operation**:
- AI agents independently generate tasks, write code, and submit PRs
- Self-sustaining task cycle for continuous development
- Automated quality checks and testing

**Multi-Project Support**:
- Applications & businesses with deployment and analytics
- Workflows & automation (data pipelines, CI/CD, monitoring)
- Developer tools (CLI, build systems, testing frameworks)

**Platform Capabilities**:
- B2C/B2B platform for project initiation and management
- User credential integration or managed SaaS environment
- Cost-transparent billing at "costs + 15%"

**Human Control Mechanisms**:
- Frequency tuning via GitHub Actions cron schedules
- Budget management and spending limits
- Backlog curation through issue management
- PR approval gate for all code changes

## ⚙️ Technical Preferences

**Infrastructure**:
- Google Cloud Platform for compute and storage
- Cloudflare for DNS, CDN, and edge services
- GitHub for version control, CI/CD, and automation

**Development Stack**:
- Python for AI agents and backend services
- React with modern UI frameworks (TailwindCSS, shadcn/ui) for frontend
- Docker for containerization and deployment

**AI & Automation**:
- Claude AI for code generation and task execution
- Semantic caching for efficiency
- Boilerplate templates for rapid development

**Architecture Principles**:
- Organized project structure with `.agents` folders
- Modular app architecture in subfolders
- Clean root directory with minimal clutter

## 👥 User Roles & Permissions

**Seed Owner (Primary User)**:
- Full control over their seed projects
- Configure agent frequencies and budgets
- Approve/reject PRs and manage backlog
- Access to all project settings and credentials

**SaaS Platform User**:
- Create and manage multiple seed projects
- Choose between self-hosted (own credentials) or managed environment
- View costs and usage analytics
- Configure billing and payment methods

**AI Agents (System)**:
- Read repository code and issues
- Generate code and submit PRs
- Create tasks and manage workflows
- Execute within defined budget and frequency limits
- No merge permissions (requires human approval)

## 🔄 Key User Flows

**Project Initialization**:
1. User inputs project idea and requirements
2. SeedGPT creates repository structure and initial setup
3. User configures agent frequencies and budget limits
4. System activates AI agents based on configuration

**Development Cycle**:
1. AI agents analyze backlog and generate tasks
2. Agents write code and submit PRs
3. User reviews PR and provides feedback
4. User approves PR or requests changes
5. Approved code merges and triggers deployment

**Human Oversight**:
1. User monitors GitHub Actions logs for activity
2. User adjusts agent frequencies via cron schedules
3. User creates custom issues to guide development
4. User labels issues to prioritize agent work
5. User pauses/resumes agents as needed

**Budget Management**:
1. User sets spending limits in workflow configurations
2. System tracks AI API costs in real-time
3. User receives notifications on budget thresholds
4. User adjusts budgets or disables workflows to control costs
