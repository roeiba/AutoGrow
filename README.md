# 🌱 AutoGrow

> **The world's first FULLY AUTONOMOUS, SELF-GROWING software project.**  
> Fork it. Set your keys. Commit. **Watch it grow forever.**

[![GitHub stars](https://img.shields.io/github/stars/roeiba/autoGrow?style=social)](https://github.com/roeiba/autoGrow)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

## 🚀 What Makes AutoGrow Revolutionary?

**AutoGrow** is not a template you fill out once. It's a **LIVING, SELF-GROWING PROJECT** that:

- 🤖 **Generates its own issues** every 10 minutes
- 🔧 **Fixes those issues automatically** with AI
- 📝 **Creates pull requests** with production-ready code
- ✅ **Runs tests** and validates changes
- 🔄 **Repeats forever** - continuously improving itself

### The Magic: 3 Steps to Autonomous Growth

```
Step 1: Fork & Setup          Step 2: Commit                Step 3: Watch It Grow
─────────────────────         ──────────────                ─────────────────────
1. Fork this repo             git add .                     Every 10 minutes:
2. Edit PROJECT_BRIEF.md      git commit -m "init"          → AI generates issues
3. Add your API keys          git push                      → AI writes code
                                                            → AI creates PRs
                                                            → AI improves itself
                                                            
                              That's it!                    Forever. Autonomously.
```

## 🎯 What Is AutoGrow?

**AutoGrow** is a self-growing software project powered by AI agents:

1. **You** describe what you want in `PROJECT_BRIEF.md`
2. **AI agents** autonomously generate issues, write code, and create PRs
3. **Your project** grows and improves itself 24/7 without human intervention

Think of it as **hiring an AI development team that never sleeps.**

### How It Actually Works

```
┌─────────────────────────────────────────────────────────────┐
│  Every 10 Minutes (Automated GitHub Actions)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Issue Generator Agent                                   │
│     ├─ Analyzes current project state                       │
│     ├─ Generates 3 new improvement issues                   │
│     └─ Labels them (feature/bug/docs/etc)                   │
│                                                              │
│  2. Issue Resolver Agent                                    │
│     ├─ Picks an open issue                                  │
│     ├─ Reads relevant code with Claude AI                   │
│     ├─ Writes production-ready solution                     │
│     ├─ Creates tests and documentation                      │
│     ├─ Commits to new branch                                │
│     └─ Opens pull request                                   │
│                                                              │
│  3. You (Optional)                                          │
│     ├─ Review the PR                                        │
│     ├─ Merge if good                                        │
│     └─ Or let it accumulate for batch review                │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Result: Your project writes itself, continuously, forever.
```

## 📁 What You Get

```
autoGrow/
│
├── PROJECT_BRIEF.md              ⭐ Fill this with your requirements
├── .agents/                      🤖 AI guidelines (for AI agents)
├── src/                          💻 Your applications (AI generates)
├── project-docs/                 📚 Documentation (AI generates)
├── tasks/                        ✅ Task tracking
├── deployment/                   🚀 Infrastructure configs
└── scripts/                      🛠️ Automation scripts
```


## 🚀 Getting Started - Launch Your Self-Growing Project

### The Only 4 Steps You'll Ever Need

#### **Step 1: Fork This Repository**
```bash
# Click "Fork" on GitHub, then:
git clone https://github.com/YOUR_USERNAME/autogrow.git my-autogrow-project
cd my-autogrow-project
```

#### **Step 2: Describe Your Vision**

Edit `PROJECT_BRIEF.md` with what you want to build:
```markdown
# My Autonomous E-Commerce Platform

## Vision
Build a fully automated online store that manages itself...

## Core Requirements
- User authentication and profiles
- Product catalog with search
- Shopping cart and checkout
- Payment processing
- Order management
```

#### **Step 3: Add Your API Keys**

Create repository secrets (Settings → Secrets and variables → Actions):

```bash
# Required secrets:
ANTHROPIC_API_KEY=sk-ant-...     # Get from: https://console.anthropic.com
PAT_TOKEN=ghp_...                # GitHub Personal Access Token with repo access
```

Or use GitHub CLI:
```bash
gh secret set ANTHROPIC_API_KEY --body "sk-ant-your-key-here"
gh secret set PAT_TOKEN --body "ghp_your-token-here"
```

#### **Step 4: Commit & Push - Then Watch the Magic**

```bash
git add .
git commit -m "Initialize my self-growing project"
git push
```

**That's it!** 🎉

### What Happens Next (Automatically)

Within 10 minutes, your project will:
1. ✅ Generate its first 3 issues
2. ✅ Start solving them with AI
3. ✅ Create pull requests with code
4. ✅ Continue growing forever

Check:
- **Issues tab** - New issues appear every 10 minutes
- **Pull Requests tab** - AI-generated code ready for review
- **Actions tab** - Watch the agents work in real-time

## 💡 Why This Changes Everything

### Traditional Development
```
You write code → You fix bugs → You add features → You maintain it
                    ↓
            Endless manual work
```

### Self-Growing Development
```
You describe vision → AI generates issues → AI writes code → AI creates PRs
                                ↓
                    Autonomous growth forever
```

### Real Impact

- **⏰ Time**: Instead of months, your project starts growing in minutes
- **💰 Cost**: One-time setup, continuous autonomous development
- **🎯 Focus**: You review and guide, AI does the heavy lifting
- **📈 Scale**: Project improves 24/7, even while you sleep
- **🔄 Evolution**: Adapts to new requirements automatically

## ✨ Key Features

### 🤖 Autonomous Agents
- **Issue Generator** - Creates improvement tasks every 10 minutes
- **Issue Resolver** - Writes production code automatically
- **Smart Validation** - Ensures quality before committing
- **PR Creation** - Submits code for your review

### 🏗️ Enterprise-Grade
- **Clean Architecture** - Modular, scalable, maintainable
- **Full Testing** - Unit tests, integration tests, CI/CD
- **Documentation** - Auto-generated and always up-to-date
- **Security** - Best practices and validation built-in

### 🔧 Developer-Friendly
- **Technology Agnostic** - Works with any stack
- **Customizable** - Adjust agent behavior via configuration
- **Transparent** - See exactly what AI is doing
- **Controllable** - You approve all changes via PR review

## 🛠️ Supported Technologies

The template is **technology-agnostic**. AI can generate projects using:

- **Backend**: Node.js, Python, Go, Java, Ruby, .NET
- **Frontend**: React, Vue, Angular, Svelte
- **Mobile**: React Native, Flutter, Native (iOS/Android)
- **Infrastructure**: Docker, Kubernetes, Terraform, CI/CD pipelines
- **Databases**: PostgreSQL, MongoDB, Redis, and more

Just specify your preferences in `PROJECT_BRIEF.md`.

## 🤖 AI Agents

This template includes ready-to-use AI agents for automation:

### Claude Agent
- **Location**: `src/claude-agent/`
- **Purpose**: Complex code generation and issue resolution
- **Features**: GitHub integration, automated PR creation, multi-role workflow

### Gemini Agent (NEW!)
- **Location**: `src/gemini-agent/`
- **Purpose**: Headless automation, code review, documentation generation
- **Features**: CLI-based, scriptable, batch processing, Python integration
- **Quick Start**: See [src/gemini-agent/QUICKSTART.md](src/gemini-agent/QUICKSTART.md)

**Use Cases:**
- Automated code reviews
- Documentation generation
- Log analysis
- Batch file processing
- CI/CD integration

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[PROJECT_BRIEF.md](PROJECT_BRIEF.md)** - Template to fill out
- **[.agents/](.agents/)** - AI guidelines and maintenance docs
- **[src/gemini-agent/](src/gemini-agent/)** - Gemini CLI agent setup and examples

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

For template maintenance, see [.agents/MAINTENANCE.md](.agents/MAINTENANCE.md).


## 📝 License

MIT License - use freely in your projects. See [LICENSE](LICENSE) for details.

## 💬 Support

- **Questions?** Check [QUICKSTART.md](QUICKSTART.md) or open a [Discussion](https://github.com/roeiba/autoGrow/discussions)
- **Bug Reports:** Open an [Issue](https://github.com/roeiba/autoGrow/issues)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)

## 🙏 Acknowledgments

Built on best practices from Clean Architecture, Domain-Driven Design, and The Twelve-Factor App.

---

<div align="center">

**Version 2.0.1** • Production Ready • November 2025

*Where human creativity meets AI capability*

[⭐ Star](https://github.com/roeiba/autoGrow) · [Report Issue](https://github.com/roeiba/autoGrow/issues) · [Discussions](https://github.com/roeiba/autoGrow/discussions)

</div>
