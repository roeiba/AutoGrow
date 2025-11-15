# 🌱 SeedGPT

> **Your project that codes itself.**  
> Describe what you want. AI builds it. Forever.

[![GitHub stars](https://img.shields.io/github/stars/roeiba/seedGPT?style=social)](https://github.com/roeiba/seedGPT)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

## What is this?

SeedGPT is a project that grows itself using AI. You describe what you want, and AI agents automatically:

- Generate tasks (as GitHub issues)
- Write the code to solve them
- Create pull requests for you to review
- Keep improving the project 24/7

Think of it as having a development team that never stops working.

## See it in action

**[View Live Examples →](https://roeiba.github.io/SeedGPT/)**

Browse real projects built with SeedGPT. See what others are building and get inspired.

## Why use this?

**Before:** You write every line of code yourself.

**After:** You describe what you want. AI writes the code. You review and approve.

The result? Your project grows while you sleep.

## Works with any tech

SeedGPT supports whatever you want to build:
- **Backend:** Node.js, Python, Go, Java, etc.
- **Frontend:** React, Vue, Angular, etc.
- **Mobile:** React Native, Flutter, etc.
- **Databases:** PostgreSQL, MongoDB, etc.

Just mention it in `PROJECT_BRIEF.md`.

## How to start

**1. Fork this repo**
```bash
git clone https://github.com/YOUR_USERNAME/seedgpt.git
cd seedgpt
```

**2. Tell it what to build**

Edit `PROJECT_BRIEF.md` with your idea:
```markdown
# My Project

I want to build an online store with:
- User login
- Product catalog
- Shopping cart
- Payment processing
```

**3. Add your API key**

Go to Settings → Secrets → Actions and add:
- `ANTHROPIC_API_KEY` - Get from [console.anthropic.com](https://console.anthropic.com)
- `PAT_TOKEN` - GitHub token with repo access

**4. Push and watch**
```bash
git add .
git commit -m "Let's grow"
git push
```

That's it! In 10 minutes, check your Issues and Pull Requests tabs.

## What happens next?

Every 10 minutes:
1. AI looks at your project
2. Creates 3 new tasks (issues)
3. Picks a task and writes code
4. Opens a pull request
5. Repeats forever

You just review and merge the PRs you like.

## You're in control

SeedGPT is autonomous, but **you're the gardener**. You control how your project grows:

### 🎛️ Tune agent frequencies
Adjust how often each agent runs by modifying the cron schedules in `.github/workflows/`:
- **Product Agent** - Generates new features and improvements
- **Marketing Agent** - Creates content and campaigns
- **Bug Fix Agent** - Resolves issues automatically

Want more features? Speed up the product agent. Need to slow down? Adjust the schedule.

### 💰 Control the budget
Set spending limits to manage AI API costs:
- Configure budget caps in your workflow files
- Monitor usage through GitHub Actions logs
- Pause agents anytime by disabling workflows

### ✋ Manage the backlog
You decide what gets built:
- **Add issues** - Create custom tasks for the AI to tackle
- **Remove issues** - Close or delete tasks you don't want
- **Prioritize** - Label issues to guide what gets picked next

### 👍 Approve or decline
Every change needs your approval:
- **Review PRs** - Check the code before it merges
- **Request changes** - AI will iterate based on your feedback
- **Merge what you like** - Only approved code goes live
- **Close what you don't** - Reject PRs that miss the mark

### 🌱 Each seed is unique
Your SeedGPT instance is yours to customize:
- Tune frequencies to match your pace
- Set budgets that fit your resources
- Guide development with your own issues
- Approve only what meets your standards

**You plant the seed. You guide its growth. AI does the heavy lifting.**

## Need help?

- **Questions?** Open a [Discussion](https://github.com/roeiba/seedGPT/discussions)
- **Found a bug?** Open an [Issue](https://github.com/roeiba/seedGPT/issues)
- **Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT - use it however you want.

---

**Built something cool?** Star the repo and share your project!

[⭐ Star](https://github.com/roeiba/seedGPT) · [Report Issue](https://github.com/roeiba/seedGPT/issues) · [Discussions](https://github.com/roeiba/seedGPT/discussions)
