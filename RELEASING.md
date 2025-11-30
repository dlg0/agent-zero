# Release Process

This document describes how to release new versions of agent-zero.

## Monorepo Structure

This repository contains multiple deployable artifacts with **independent versioning**:

| Artifact | Location | Version Source | Tag Pattern | Target |
|----------|----------|----------------|-------------|--------|
| CLI | `/` (root) | `pyproject.toml` | `cli-vX.Y.Z` | GitHub Releases |
| Web (future) | `/web/` | `package.json` | `web-vX.Y.Z` | TBD |

Each artifact follows [Semantic Versioning](https://semver.org/) independently.

---

## CLI Releases (GitHub)

### For Users

Install and update via uv directly from GitHub:

```bash
# Install latest release
uv tool install git+https://github.com/dlg0/agent-zero

# Update to latest release
uv tool upgrade agentzero

# Install specific version
uv tool install git+https://github.com/dlg0/agent-zero@cli-v0.1.0
```

### For Maintainers

#### Release Checklist

**⚠️ All steps must be completed in order. Do not skip any step.**

##### 1. Ensure main branch is ready

```bash
# Switch to main and pull latest
git checkout main
git pull origin main
```

##### 2. Run full local CI check

**This must pass before proceeding:**

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy src/ && uv run pytest -v
```

If anything fails, fix it and commit to main first.

##### 3. Verify CI is green on main

- Check [GitHub Actions](https://github.com/dlg0/agent-zero/actions) 
- **All checks must be passing on the main branch**
- If CI is failing, fix issues before releasing

##### 4. Update version in `pyproject.toml`

```toml
version = "X.Y.Z"
```

##### 5. Update the changelog

Edit `CHANGELOG.cli.md`:
- Move items from `[Unreleased]` to new version section
- Add release date in format `YYYY-MM-DD`

##### 6. Commit the release preparation

```bash
git add pyproject.toml CHANGELOG.cli.md
git commit -m "chore(release): prepare cli vX.Y.Z"
git push origin main
```

##### 7. Wait for CI to pass on the release commit

- Check [GitHub Actions](https://github.com/dlg0/agent-zero/actions)
- **Do not proceed until all checks pass**

##### 8. Create and push the tag

```bash
git tag cli-vX.Y.Z
git push origin cli-vX.Y.Z
```

##### 9. Verify the release

- Check [GitHub Actions](https://github.com/dlg0/agent-zero/actions) for the release workflow
- Verify [GitHub Releases](https://github.com/dlg0/agent-zero/releases) shows the new version
- Test installation:
  ```bash
  uv tool install git+https://github.com/dlg0/agent-zero@cli-vX.Y.Z
  agentzero --version
  ```

#### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes to CLI interface or config format
- **MINOR** (0.X.0): New features, backwards compatible
- **PATCH** (0.0.X): Bug fixes, backwards compatible

Pre-release versions: `X.Y.Z-alpha.1`, `X.Y.Z-beta.1`, `X.Y.Z-rc.1`

---

## Web Releases (Future)

When the web frontend is added:

1. **Directory structure**:
   ```
   web/
   ├── package.json      # Contains version
   ├── CHANGELOG.md      # Web-specific changelog
   └── ...
   ```

2. **Tag pattern**: `web-vX.Y.Z`

3. **Workflow**: `.github/workflows/release-web.yml` (to be created)

4. **Deployment target**: TBD (Vercel, Netlify, etc.)

The web frontend will have its own version and release cadence, independent of the CLI.

---

## Changelog Management

### Format

We use [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [Unreleased]

## [X.Y.Z] - YYYY-MM-DD
### Added
- New feature description

### Changed
- Modified behavior description

### Fixed
- Bug fix description

### Removed
- Removed feature description
```

### Workflow

1. **During development**: Add entries to `[Unreleased]` section in PRs
2. **At release time**: Move entries to a new version section with date
3. **Categories**: Added, Changed, Deprecated, Removed, Fixed, Security

---

## Troubleshooting

### Tag/Version Mismatch

If the release fails with "Tag version does not match pyproject.toml version":

```bash
# Delete the incorrect tag
git tag -d cli-vX.Y.Z
git push origin :refs/tags/cli-vX.Y.Z

# Fix version in pyproject.toml, commit, then re-tag
git tag cli-vX.Y.Z
git push origin cli-vX.Y.Z
```

### Release Workflow Fails

1. Check GitHub Actions logs for specific error
2. The workflow validates that:
   - Tag version matches `pyproject.toml` version
   - Tag is on the main branch
   - All tests pass
3. Fix the issue and re-tag if necessary

### Testing a Release Locally

```bash
# Build without releasing
uv build

# Check the built files
ls dist/

# Test install from built wheel
uv pip install dist/agent_zero-*.whl
agentzero --version
```

### Users Can't Update

If `uv tool upgrade agentzero` doesn't pick up a new version:

```bash
# Force reinstall from latest
uv tool uninstall agentzero
uv tool install git+https://github.com/dlg0/agent-zero
```

---

## CI/CD Summary

### On Every Push/PR (ci.yml)

- Lint & format check
- Type checking (mypy)
- Unit, integration, and e2e tests
- Coverage report

### On Release Tag (release-cli.yml)

- Validates tag matches `pyproject.toml`
- Validates tag is on main branch
- Runs full test suite
- Builds distribution (sdist + wheel)
- Creates GitHub Release with artifacts
