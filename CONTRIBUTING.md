# Contributing to Teach Me Mailer

Thank you for your interest in contributing to the Teach Me Mailer project! This document provides guidelines and information for contributors.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Branch Management & Workflow

**⚠️ Important**: This repository follows a protected main branch strategy:

- **`main` branch**: Protected, production-ready code only
- **`develop` branch**: Default for development and feature integration
- **Development Flow**: Push all changes to `develop` → open PR to `main` after successful pipeline

```bash
# Correct workflow:
git checkout develop
git pull origin develop
# Make your changes
git add .
git commit -m "✨ Add new feature"
git push origin develop
# Then: Open PR from develop → main
```

### Reporting Issues

- Use the GitHub issue tracker to report bugs
- Include detailed information about the issue
- Provide steps to reproduce the problem
- Include relevant logs and error messages

### Development Setup

1. Fork the repository
2. Clone your fork locally
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   make dev
   ```
5. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Making Changes

1. Create a feature branch from `develop`:
   ```bash
   git checkout -b feature/your-feature-name develop
   ```
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass:
   ```bash
   make test
   ```
5. Ensure code quality:
   ```bash
   make lint
   ```
6. Commit your changes with descriptive messages
7. Push to your fork and submit a pull request

### Pull Request Guidelines

- Target the `develop` branch for new features
- Target the `main` branch for hotfixes
- Include a clear description of changes
- Reference related issues
- Ensure CI/CD checks pass
- Update documentation if necessary
- Add entries to CHANGELOG.md

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run `make lint` to check code style and `make format` to auto-format.

### Testing

- Write tests for new functionality
- Maintain test coverage above 90%
- Use pytest for testing
- Include both unit and integration tests

### Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions and classes
- Update API documentation for endpoint changes

## Development Workflow

1. **Issues**: Use GitHub issues to track bugs and feature requests
2. **Branches**:
   - `main`: Production-ready code
   - `develop`: Integration branch for features
   - `feature/*`: Individual features
   - `hotfix/*`: Critical fixes
3. **Pull Requests**: All changes must go through PR review
4. **Releases**: Tagged releases from `main` branch

## Release Process

1. Merge features to `develop`
2. Create release branch from `develop`
3. Update version numbers and changelog
4. Merge to `main` with tag
5. Deploy to production

## Questions?

Feel free to open an issue for questions or reach out to the maintainers.

Thank you for contributing! 🚀
