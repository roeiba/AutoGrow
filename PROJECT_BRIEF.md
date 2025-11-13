# Project Brief

> **This is the ONLY file you need to edit as a human user.**  
> Fill in your project requirements below, then let AI agents generate everything else.

---

## 🎯 Project Overview

**Project Name**: AutoGrow

**Brief Description**: 
The world's first fully autonomous, self-growing software project. AutoGrow uses AI agents to continuously generate issues, write code, create pull requests, and monitor quality - all automatically. Fork it, set your keys, commit, and watch your project grow forever without human intervention.

**Problem Statement**:
Software project setup is time-consuming and error-prone, requiring developers to repeatedly create boilerplate code, documentation structures, CI/CD pipelines, and architectural decisions. AI coding assistants lack structured guidance to generate consistent, high-quality project foundations. Teams waste weeks setting up projects instead of building features.

**Target Users**:
Software development teams, AI coding assistants, project managers, startup founders, and enterprise development teams who need to rapidly bootstrap new projects with professional standards and comprehensive documentation.

---

## 📋 Core Requirements

### Functional Requirements

1. **Template Structure & Organization**
   - Comprehensive directory structure with clear separation of concerns
   - Context-aware .agents/ folders with AI-specific guidelines
   - Structured documentation hierarchy (technical, business, architecture)
   - Task management system with clear workflows

2. **AI Agent Integration**
   - Detailed project rules and guidelines for AI assistants
   - Session logging system for AI work tracking
   - Prompt templates and examples for common tasks
   - Clear decision frameworks for architectural choices

3. **Project Generation Capabilities**
   - Support for multiple technology stacks (Node.js, Python, Go, etc.)
   - Configurable application types (backend, frontend, mobile, etc.)
   - Infrastructure as Code templates (Docker, Kubernetes, Terraform)
   - CI/CD pipeline configurations for major platforms

4. **Documentation Framework**
   - Living documentation that stays synchronized with code
   - Architecture Decision Records (ADR) templates
   - Knowledge base for business context and domain expertise
   - User guides and technical documentation templates

### Non-Functional Requirements

- **Usability**: Simple one-file setup (PROJECT_BRIEF.md), clear documentation, intuitive structure
- **Maintainability**: Modular design, version-controlled guidelines, clear separation of concerns
- **Extensibility**: Support for new technology stacks, customizable templates, pluggable components
- **Reliability**: Consistent AI agent behavior, reproducible project generation, comprehensive testing frameworks
- **Portability**: Platform-agnostic design, containerized deployments, cloud-provider neutral

---

## 🏗️ Technical Preferences

### Technology Stack

**Template System**:
- [x] Markdown documentation
- [x] YAML configuration files
- [x] Shell scripts for automation
- [x] Git for version control

**Supported Backend Technologies**:
- [x] Node.js (Express/NestJS/Fastify)
- [x] Python (FastAPI/Django/Flask)
- [x] Go (Gin/Echo/Fiber)
- [x] Java (Spring Boot)

**Supported Frontend Technologies**:
- [x] React (Next.js, CRA, Remix)
- [x] Vue.js (Nuxt.js)
- [x] Angular
- [x] Svelte (SvelteKit)

**Infrastructure Templates**:
- [x] Docker containerization
- [x] Kubernetes orchestration
- [x] Terraform (AWS/GCP/Azure)
- [x] CI/CD (GitHub Actions, GitLab CI)
- [x] Monitoring (Prometheus, Grafana)

---

## 👥 User Roles & Permissions

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| Project Lead | Human who defines requirements | Fill PROJECT_BRIEF.md, approve AI-generated code, make architectural decisions |
| AI Agent | Coding assistant that generates project | Read requirements, generate code/docs, follow guidelines, create session logs |
| Developer | Human who extends generated project | Modify code, add features, update documentation, create tasks |
| DevOps Engineer | Manages infrastructure and deployment | Configure CI/CD, manage infrastructure, monitor systems |

---

## 🔄 Key User Flows

### Flow 1: Initial Project Setup
1. Human clones autoGrow repository
2. Human fills out PROJECT_BRIEF.md with project requirements
3. Human provides brief to AI agent with generation prompt
4. AI agent reads PROJECT_BRIEF.md and .agents/project-rules.md
5. AI agent creates session log and generates complete project structure
6. Human reviews generated code and approves for development

### Flow 2: Ongoing Development
1. Developer/AI selects task from tasks/active/ directory
2. Agent reads relevant .agents/ guidelines for the component
3. Agent implements feature following established patterns
4. Agent writes tests and updates documentation
5. Agent updates task status and moves to completed
6. Code is reviewed and merged into main branch

### Flow 3: Template Customization
1. Team identifies need for new technology stack or pattern
2. Developer creates new template in appropriate directory
3. Developer updates .agents/ guidelines with new patterns
4. Developer documents decision in architecture/decisions/
5. Template is tested with AI agent generation
6. New template becomes available for future projects

---

## 🗄️ Data Model (High-Level)

### Project Template
- Name: string, unique identifier for the template
- Description: string, brief explanation of template purpose
- Technology Stack: array, supported technologies and frameworks
- Directory Structure: object, defines folder organization
- Guidelines: object, AI agent instructions and rules
- Version: string, semantic version for template updates

### Task Definition
- ID: string, unique task identifier
- Title: string, descriptive task name
- Description: text, detailed task requirements
- Status: enum (pending, in_progress, review, completed)
- Priority: enum (low, medium, high)
- Dependencies: array, references to other tasks
- Acceptance Criteria: array, specific completion requirements

### Session Log
- Timestamp: datetime, when AI session started
- AI Model: string, which AI assistant was used
- Prompts: array, all prompts received during session
- Files Modified: array, list of files created or changed
- Outcomes: text, summary of work completed
- Lessons Learned: text, insights for future sessions

---

## 🔌 External Integrations

- [x] Git Version Control: GitHub, GitLab, Bitbucket integration
- [x] CI/CD Platforms: GitHub Actions, GitLab CI, Jenkins, CircleCI
- [x] Cloud Providers: AWS, Google Cloud, Azure templates
- [x] Container Registries: Docker Hub, GitHub Container Registry, ECR
- [x] Monitoring Services: Prometheus, Grafana, Datadog, New Relic
- [x] Documentation Platforms: GitHub Pages, GitBook, Confluence
- [ ] AI Coding Assistants: GitHub Copilot, Cursor, Claude, GPT integration

---

## 📅 Timeline & Priorities

**Target Launch Date**: November 2025 (Public Launch)

**Priority Features** (Must Have):
1. Complete PROJECT_BRIEF.md with template details
2. Comprehensive README with clear usage instructions
3. GitHub repository optimization (topics, description, documentation)
4. Launch announcement content for social media and Reddit
5. Example/demo project showcasing template capabilities

**Secondary Features** (Nice to Have):
1. Video tutorial demonstrating template usage
2. Integration with popular AI coding assistants
3. Template marketplace for community contributions
4. Automated template validation and testing

**Future Enhancements**:
1. Web-based template generator interface
2. Template analytics and usage tracking
3. Enterprise features (team collaboration, private templates)
4. Integration with project management tools

---

## 💰 Budget & Resources

**Budget**: Open source project (no budget required)

**Team Size**: 1 maintainer + community contributors + AI agents

**Constraints**: 
- Must remain free and open source
- Documentation must be comprehensive for AI agents
- Template must work with multiple AI coding assistants
- Launch timeline: November 2025

---

## 📝 Additional Context

This template represents a paradigm shift in software development where AI agents become first-class participants in the development process. The template is designed to be:

**Self-Documenting**: Every decision and pattern is documented for future AI agents to understand and follow.

**Evolutionary**: The template improves through use - each project generated provides feedback to enhance the guidelines.

**Community-Driven**: While maintaining consistency, the template should evolve with community contributions and new best practices.

**Production-Ready**: Generated projects should be immediately deployable with professional standards, not just prototypes.

The success metric is simple: Can an AI agent, given only a filled PROJECT_BRIEF.md, generate a complete, production-ready project that a human developer would be proud to deploy?

---

## ✅ Success Criteria

The AutoGrow project will be considered successful when it achieves the following measurable outcomes:

1. **Autonomous Operation**: The system generates issues and creates pull requests automatically every 10 minutes without human intervention for at least 1 week continuously.

2. **Code Quality**: At least 80% of generated pull requests pass automated tests and meet quality standards without requiring manual fixes.

3. **Community Adoption**: The repository achieves 100+ stars and 10+ forks within the first month of public launch, demonstrating genuine interest and adoption.

4. **AI Generation Quality**: AI agents can successfully generate a complete, deployable project structure from a filled PROJECT_BRIEF.md in under 10 minutes with no human intervention.

5. **Documentation Completeness**: All generated code includes comprehensive documentation, architecture decisions are recorded, and the knowledge base remains synchronized with code changes.

6. **Self-Improvement**: The system demonstrates continuous improvement by successfully resolving at least 3 different types of issues (bugs, features, documentation) automatically.

7. **Production Readiness**: Generated projects include working CI/CD pipelines, containerization, and monitoring setup that can be deployed immediately.

8. **Template Versatility**: Successfully supports generation for at least 3 different technology stacks (e.g., Node.js, Python, Go) with consistent quality.

---

## ✅ Completion Checklist

Once you've filled this out:

- [x] All required sections completed
- [x] Technical preferences selected
- [x] User roles defined
- [x] Key flows documented
- [x] Ready for AI agents to start implementation

---

**Next Step**: This PROJECT_BRIEF.md is now complete and ready for launch preparation. The template is ready to be used by AI agents to generate projects based on user requirements.
