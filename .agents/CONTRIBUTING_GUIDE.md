# Detailed Contributing Guide

> **For contributors to the AI Project Template repository**

This guide provides detailed instructions for contributing to the template itself. For using the template, see the main README.

## Types of Contributions

### 1. Bug Fixes
- Fix broken links
- Correct typos
- Fix structural issues
- Resolve configuration problems

### 2. Documentation Improvements
- Clarify existing documentation
- Add missing examples
- Improve organization
- Fix formatting issues

### 3. Feature Additions
- New template structures
- Additional examples
- Enhanced AI guidelines
- New automation scripts

### 4. Technology Updates
- Update framework examples
- Add new tech stack options
- Modernize best practices
- Update dependencies

## Contribution Workflow

### Step 1: Setup
```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/autoGrow.git
cd autoGrow

# Add upstream remote
git remote add upstream https://github.com/roeiba/autoGrow.git

# Create a branch
git checkout -b feature/your-feature-name
```

### Step 2: Make Changes
- Follow existing patterns and style
- Update relevant documentation
- Test your changes thoroughly
- Ensure no breaking changes (or document them)

### Step 3: Commit
```bash
# Stage your changes
git add .

# Commit with conventional commit format
git commit -m "feat(scope): brief description"

# Examples:
# git commit -m "docs(readme): clarify installation steps"
# git commit -m "feat(templates): add FastAPI backend example"
# git commit -m "fix(structure): correct deployment folder path"
```

### Step 4: Push and PR
```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# - Use clear title and description
# - Reference any related issues
# - Explain what changed and why
```

## Contribution Guidelines

### Code Style
- Follow existing formatting
- Use consistent naming conventions
- Keep files organized
- Comment complex logic

### Documentation Style
- Use clear, concise language
- Include examples where helpful
- Use proper Markdown formatting
- Check spelling and grammar

### Commit Messages
Follow conventional commits:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting changes
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Pull Request Guidelines
- One feature/fix per PR
- Clear title and description
- Link related issues
- Update CHANGELOG.md
- Ensure all checks pass

## What to Contribute

### High Priority
- Bug fixes
- Documentation clarity improvements
- Broken link fixes
- Missing examples

### Medium Priority
- New technology examples
- Enhanced AI guidelines
- Additional templates
- Automation improvements

### Low Priority
- Cosmetic changes
- Minor refactoring
- Optional features

## Review Process

### What Reviewers Check
1. **Correctness**: Does it work as intended?
2. **Clarity**: Is documentation clear?
3. **Consistency**: Matches existing patterns?
4. **Completeness**: All necessary files updated?
5. **Breaking Changes**: Any impact on existing users?

### Response Time
- Initial response: Within 48 hours
- Full review: Within 1 week
- Merge or feedback: Within 2 weeks

### Feedback Handling
- Address all review comments
- Ask questions if unclear
- Update PR based on feedback
- Re-request review when ready

## Testing Your Changes

### Manual Testing
1. Clone fresh copy of your branch
2. Follow user documentation
3. Test with AI agents if applicable
4. Verify all links work
5. Check examples are valid

### Documentation Testing
- Read through all changed docs
- Verify examples are accurate
- Check formatting renders correctly
- Test any code snippets

## Common Contribution Scenarios

### Adding a New Technology Example

1. Research the technology
2. Create example in appropriate location
3. Update relevant documentation
4. Add to technology stack list
5. Include setup instructions
6. Test the example

### Improving AI Guidelines

1. Identify unclear or missing guidance
2. Draft improved instructions
3. Test with AI agents
4. Update `.agents/project-rules.md`
5. Document in PR why change helps

### Fixing Documentation

1. Identify the issue
2. Make corrections
3. Verify links and formatting
4. Check related documentation
5. Submit PR with clear description

### Adding Template Structure

1. Propose in issue first
2. Create directory structure
3. Add README with guidelines
4. Update main documentation
5. Add to .gitignore if needed
6. Test with fresh clone

## Getting Help

### Questions About Contributing
- Check this guide first
- Review existing issues and PRs
- Ask in GitHub Discussions
- Create an issue if needed

### Questions About the Template
- See main README.md
- Check QUICKSTART.md
- Review .agents/project-rules.md
- Ask in Discussions

## Recognition

Contributors are recognized through:
- GitHub contributor list
- CHANGELOG.md mentions
- Community acknowledgment
- Maintainer consideration for active contributors

## Code of Conduct

All contributors must follow the CODE_OF_CONDUCT.md:
- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Thank You!

Every contribution, no matter how small, helps make this template better for everyone. Thank you for taking the time to contribute!
