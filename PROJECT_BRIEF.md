## 🎯 Project Overview

**Project Name**: SeedGPT

**Goal**: Build a profitable online business that grows autonomously.

**Brief Description**: 
An autonomous project that self-evolves using AI. SeedGPT independently drives development, manages operations, and scales sustainably, ensuring continuous growth and profitability.

**Problem Statement**:
People want solutions without hassle. Most desire a ready app, product, or business to meet their needs, while a few prefer to build it themselves.

**Target Users**:
Anyone seeking effortless solutions through technology.

**Proposed Solution**:
SeedGPT employs AI agents to autonomously generate tasks, write code, submit pull requests, and maintain quality. It oversees all business functions—deployment, analytics, marketing, and sales—via a self-sustaining task cycle. This includes creating marketing content, creatives, social media posts, blogs, games, and other relevant materials customized for each business.

Once mature, SeedGPT acts as a foundational seed for any venture, adaptable to diverse projects.

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
