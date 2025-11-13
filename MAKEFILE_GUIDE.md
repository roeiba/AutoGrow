# Makefile Guide

Complete guide for using Makefiles to manage AI agent testing and CI/CD.

## 📋 Overview

The project includes OS-specific Makefiles that automate:
- Installing dependencies (Claude CLI, Gemini CLI, Python packages)
- Running tests (unit, integration, coverage)
- Code quality checks (linting, formatting)
- CI/CD workflows

## 📁 Makefile Structure

```
Makefile              # Auto-detects OS and delegates
Makefile.macos        # macOS-specific commands
Makefile.linux        # Linux-specific commands
```

## 🚀 Quick Start

### Show Available Commands

```bash
make help
```

### Install Everything

```bash
# Install all dependencies
make install
```

This will:
1. Install Claude Code CLI
2. Install Gemini CLI
3. Install Python test dependencies

### Run Tests

```bash
# Run unit tests (fast, no API calls)
make test

# Run integration tests (requires API keys)
make test-integration

# Run all tests
make test-all

# Run with coverage
make test-coverage
```

## 🎯 Available Targets

### Installation

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make install-claude` | Install Claude Code CLI |
| `make install-gemini` | Install Gemini CLI |
| `make install-test-deps` | Install Python test dependencies |

### Testing

| Command | Description |
|---------|-------------|
| `make test` | Run unit tests only |
| `make test-unit` | Run unit tests |
| `make test-integration` | Run integration tests (requires API keys) |
| `make test-all` | Run all tests |
| `make test-coverage` | Run tests with coverage report |
| `make quick-test` | Run fast tests only |

### Code Quality

| Command | Description |
|---------|-------------|
| `make lint` | Run code linters |
| `make format` | Format code with black |

### Utilities

| Command | Description |
|---------|-------------|
| `make verify` | Verify installation |
| `make clean` | Clean temporary files |
| `make show-os` | Show detected OS |
| `make ci` | CI target (install deps + unit tests) |

## 💻 Platform-Specific Details

### macOS (Makefile.macos)

**Claude CLI Installation**:
```bash
brew install --cask claude-code
```

**Gemini CLI Installation**:
```bash
npm install -g @google/generative-ai-cli
```

**Requirements**:
- Homebrew
- Node.js/npm
- Python 3

### Linux (Makefile.linux)

**Claude CLI Installation**:
```bash
# Downloads and installs to ~/.local/bin/
curl -fsSL <url> | tar -xz -C ~/.local/bin
```

**Gemini CLI Installation**:
```bash
npm install -g @google/generative-ai-cli
```

**Requirements**:
- curl
- Node.js/npm
- Python 3

**Install System Dependencies** (Ubuntu/Debian):
```bash
make install-system-deps
```

## 🔑 Environment Variables

### Required for Integration Tests

```bash
# Gemini API Key (required for Gemini integration tests)
export GEMINI_API_KEY="your-gemini-api-key"

# Anthropic API Key (optional, for Claude API tests)
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### Add to Shell Profile

**bash** (`~/.bashrc`):
```bash
export GEMINI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

**zsh** (`~/.zshrc`):
```bash
export GEMINI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

Then reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

## 📊 Usage Examples

### Complete Setup

```bash
# 1. Install all dependencies
make install

# 2. Verify installation
make verify

# 3. Run unit tests
make test

# 4. Set API keys
export GEMINI_API_KEY="your-key"

# 5. Run integration tests
make test-integration
```

### Development Workflow

```bash
# Make code changes
vim src/gemini-agent/gemini_agent.py

# Format code
make format

# Run linters
make lint

# Run quick tests
make quick-test

# Run full test suite
make test-all
```

### CI/CD Workflow

```bash
# Install dependencies
make install-test-deps

# Run unit tests
make test-unit

# Generate coverage
make test-coverage
```

## 🎯 Test Markers

Tests use pytest markers to categorize:

```python
@pytest.mark.integration  # Integration test (real API calls)
@pytest.mark.slow         # Slow test (takes time)
```

### Filter Tests

```bash
# Run only unit tests (exclude integration)
make test-unit

# Run only integration tests
make test-integration

# Run quick tests (exclude slow)
make quick-test
```

## 🔧 Customization

### Override Variables

```bash
# Use different Python version
PYTHON=python3.11 make test

# Use different pytest options
PYTEST_OPTS="-vv --tb=short" make test
```

### Add Custom Targets

Edit `Makefile.macos` or `Makefile.linux`:

```makefile
.PHONY: my-custom-target
my-custom-target:
	@echo "Running custom target"
	# Your commands here
```

## 🐛 Troubleshooting

### "make: command not found"

**Solution**: Install make
```bash
# macOS
xcode-select --install

# Linux (Ubuntu/Debian)
sudo apt-get install build-essential
```

### "claude: command not found"

**Solution**: Install Claude CLI
```bash
make install-claude
```

### "gemini: command not found"

**Solution**: Install Gemini CLI
```bash
make install-gemini
```

### "No module named 'pytest'"

**Solution**: Install test dependencies
```bash
make install-test-deps
```

### Tests Skipped

**Solution**: Set API keys
```bash
export GEMINI_API_KEY="your-key"
make test-integration
```

### Permission Denied

**Solution**: Make scripts executable
```bash
chmod +x src/*/scripts/*.sh
```

## 🔄 CI/CD Integration

### GitHub Actions

The project includes `.github/workflows/test-agents.yml`:

```yaml
- name: Install dependencies
  run: make install-test-deps

- name: Run tests
  run: make test-unit
  
- name: Run integration tests
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  run: make test-integration
```

### Local CI Simulation

```bash
# Run the same commands as CI
make ci
```

## 📈 Coverage Reports

### Generate HTML Coverage Report

```bash
make test-coverage
```

Report location: `tests/htmlcov/index.html`

### View Coverage

```bash
# macOS
open tests/htmlcov/index.html

# Linux
xdg-open tests/htmlcov/index.html
```

## 🎓 Best Practices

### 1. Always Run Unit Tests First

```bash
make test-unit
```

Unit tests are fast and don't require API keys.

### 2. Use Integration Tests Sparingly

```bash
make test-integration
```

Integration tests make real API calls (costs money).

### 3. Clean Before Committing

```bash
make clean
make format
make lint
```

### 4. Verify Installation

```bash
make verify
```

Check that all tools are installed correctly.

### 5. Use Coverage for Quality

```bash
make test-coverage
```

Ensure code is well-tested.

## 📝 Makefile Targets Reference

### Installation Targets

```bash
make install              # Install everything
make install-claude       # Install Claude CLI
make install-gemini       # Install Gemini CLI
make install-test-deps    # Install Python test deps
make install-system-deps  # Install system deps (Linux only)
```

### Test Targets

```bash
make test                 # Unit tests only
make test-unit            # Unit tests
make test-integration     # Integration tests
make test-all             # All tests
make test-coverage        # Tests with coverage
make quick-test           # Fast tests only
make ci                   # CI target
```

### Quality Targets

```bash
make lint                 # Run linters
make format               # Format code
make clean                # Clean temp files
make verify               # Verify installation
```

### Utility Targets

```bash
make help                 # Show help
make show-os              # Show detected OS
```

## 🌟 Examples

### New Developer Setup

```bash
# 1. Clone repo
git clone <repo-url>
cd autoGrow

# 2. Install dependencies
make install

# 3. Verify
make verify

# 4. Run tests
make test
```

### Pre-Commit Checks

```bash
# Format and lint
make format
make lint

# Run tests
make test

# Check coverage
make test-coverage
```

### CI/CD Pipeline

```bash
# Install
make install-test-deps

# Test
make test-unit

# Coverage
make test-coverage

# Lint
make lint
```

## 📚 Additional Resources

- **Integration Tests**: See `tests/INTEGRATION_TESTS.md`
- **Test Guide**: See `tests/TESTING_GUIDE.md`
- **Unit Tests**: See `tests/README.md`
- **GitHub Workflow**: See `.github/workflows/test-agents.yml`

---

**Quick Reference**:
```bash
make help                 # Show all commands
make install              # Install everything
make test                 # Run unit tests
make test-integration     # Run integration tests
make verify               # Verify setup
make clean                # Clean up
```
