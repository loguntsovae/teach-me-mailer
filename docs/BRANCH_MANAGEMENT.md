# Repository Branch Management

This document outlines the branch protection rules and development workflow for this repository.

## Branch Protection Rules

### Main Branch (`main`)
- **Status**: Protected branch 🔒
- **Direct Pushes**: ❌ Disabled
- **Required Reviews**: ✅ At least 1 reviewer required
- **Required Status Checks**: ✅ All CI checks must pass
  - Linting (`lint` job)
  - Tests (`test` job)
  - Security checks (`security` job)
  - Build verification (`build` job)
- **Dismiss Stale Reviews**: ✅ Enabled
- **Up-to-date Branch**: ✅ Required before merge

### Develop Branch (`develop`)
- **Status**: Default development branch 🚀
- **Direct Pushes**: ✅ Allowed for collaborators
- **CI Triggers**: ✅ Runs on every push
- **Purpose**: Integration and testing before main

## Development Workflow

```mermaid
gitgraph:
    options:
    {
        "mainBranchName": "main",
        "theme": "forest"
    }
    commit id: "Initial"
    branch develop
    checkout develop
    commit id: "Feature A"
    commit id: "Feature B"
    commit id: "Fix C"
    checkout main
    merge develop
    commit id: "Release v1.0"
    checkout develop
    commit id: "Feature D"
```

### 📋 Step-by-Step Process

1. **Feature Development**
   ```bash
   git checkout develop
   git pull origin develop
   # Make your changes
   git add .
   git commit -m "✨ Add new feature"
   git push origin develop
   ```

2. **Create Pull Request**
   - Open PR: `develop` → `main`
   - Wait for CI checks to pass ✅
   - Request code review 👀
   - Address feedback if needed 🔄

3. **Merge to Main**
   - CI checks pass ✅
   - Code reviewed and approved ✅
   - Squash and merge to main 🚀

### 🛡️ Safety Measures

- **Pre-push Hook**: Prevents direct pushes to main
- **CI Validation**: All code must pass automated tests
- **Code Review**: Human review required for main branch
- **Status Checks**: Build, lint, test, security scans

## GitHub Actions Triggers

### Push Events
- ✅ `develop` branch: Runs full CI pipeline
- ❌ `main` branch: No push triggers (PR only)

### Pull Request Events
- ✅ PRs targeting `main`: Full CI + additional checks
- ✅ PRs targeting `develop`: Standard CI pipeline

### Release Events
- ✅ Published releases: Deploy to production

## Setting Up Branch Protection (Repository Admin)

To configure these rules in GitHub repository settings:

1. Go to **Settings** → **Branches**
2. Add rule for `main` branch:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators
   - ✅ Restrict pushes that create files larger than 100MB
3. Set `develop` as default branch

## Troubleshooting

### "Push to main blocked"
```bash
# If you accidentally try to push to main:
git checkout develop
git cherry-pick main  # If you have commits on main
git push origin develop
# Then create PR: develop → main
```

### "Status checks failing"
```bash
# Run checks locally first:
make lint     # Code quality
make test     # Test suite
make format   # Auto-fix formatting
```

### "Branch not up to date"
```bash
git checkout develop
git pull origin main      # Get latest main
git push origin develop   # Update PR branch
```
