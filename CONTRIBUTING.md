# Contributing to Repo Trust

Thank you for your interest in contributing to Repo Trust! This document provides guidelines and information for contributors.

<br>

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

<br>

## How to Contribute

### Reporting Issues

Before creating an issue:
1. Search existing issues to avoid duplicates
2. Use the issue templates when available
3. Include relevant details:
   - Repo Trust version
   - GitHub Actions runner OS
   - Error messages (full logs if possible)
   - Steps to reproduce

**Security issues**: Please report security vulnerabilities privately via GitHub Security Advisories, NOT as public issues. See [SECURITY.md](SECURITY.md).

<br>

### Feature Requests

We welcome feature requests! Please:
1. Check if it's already been requested
2. Explain the use case clearly
3. Consider if it fits Repo Trust's scope (distribution trust, not general security)

<br>

### Pull Requests

#### Before Starting

1. Open an issue to discuss significant changes
2. Check the roadmap to avoid duplicate work
3. Ensure your change aligns with project goals

<br>

#### Development Setup

```bash
# Clone the repository
git clone https://github.com/kahalewai/repo-trust/action.git
cd action

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # if available

# Run tests
python -m pytest tests/
```

<br>

#### Making Changes

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Add/update tests as needed
4. Update documentation if needed
5. Run the test suite
6. Commit with clear messages

<br>

#### Commit Messages

Use clear, descriptive commit messages:

```
type: short description

Longer explanation if needed. Wrap at 72 characters.

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

<br>

#### Pull Request Process

1. Update the README.md if needed
2. Update CHANGELOG.md with your changes
3. Ensure all tests pass
4. Request review from maintainers
5. Address review feedback

<br>

## Development Guidelines

### Code Style

- Python: Follow PEP 8
- Use type hints where practical
- Keep functions focused and small
- Add docstrings to public functions

<br>

### Error Handling

- Use the custom exception classes in `logging.py`
- Provide actionable error messages
- Include context that helps debugging
- Don't swallow exceptions silently

<br>

### Logging

- Use the logging module from `repo_trust.logging`
- Use appropriate log levels:
  - `debug`: Detailed diagnostic info
  - `info`: Normal operation progress
  - `warning`: Unexpected but recoverable
  - `error`: Operation failures

<br>

### Testing

- Add tests for new functionality
- Maintain or improve code coverage
- Test error paths, not just happy paths
- Mock external services (GitHub API)

<br>

### Security

- Never log secrets or tokens
- Validate all inputs
- Use timeouts on external calls
- Follow principle of least privilege

<br>

## Release Process

Releases are managed by maintainers:

1. Update version in `__init__.py`
2. Update CHANGELOG.md
3. Create a GitHub Release with tag `vX.Y.Z`
4. GitHub Actions builds and publishes

<br>

## Getting Help

- **Questions**: Open a Discussion
- **Bugs**: Open an Issue
- **Security**: See SECURITY.md

<br>

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes for significant contributions
- CONTRIBUTORS.md (for major contributors)

Thank you for helping make Repo Trust better! 🙏
