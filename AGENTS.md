## Development Commands

This project uses `uv` for package management. Install dev dependencies with:

```bash
uv sync --all-extras
```

### Linting & Formatting (ruff)

```bash
uv run ruff check .           # Lint
uv run ruff check --fix .     # Lint with auto-fix
uv run ruff format .          # Format code
uv run ruff format --check .  # Check formatting
```

### Type Checking (mypy)

```bash
uv run mypy src/
```

### Testing (pytest)

```bash
uv run pytest                      # All tests
uv run pytest tests/unit           # Fast unit tests only
uv run pytest -m integration       # Integration tests
uv run pytest -m e2e               # End-to-end CLI tests
uv run pytest --cov=agent_zero     # With coverage
```

### Full CI Check (run locally)

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy src/ && uv run pytest
```

---

## Before Opening a PR

**IMPORTANT**: All PRs must pass CI checks before merge. Branch protection enforces this.

### Required Steps (humans and agents)

1. **Run the full CI check locally** before pushing:
   ```bash
   uv run ruff format --check . && uv run ruff check . && uv run mypy src/ && uv run pytest
   ```

2. **Fix any issues** before opening the PR:
   - Formatting: `uv run ruff format .`
   - Lint auto-fix: `uv run ruff check --fix .`
   - Type errors: Fix manually based on mypy output
   - Test failures: Fix the code or update tests

3. **Create PR against `main`** - direct pushes are blocked

### If You Cannot Run Checks Locally

If running in a restricted environment without full tooling:
- Still open the PR - CI will run all checks
- Monitor the CI results and push fixes as needed
- PR cannot merge until all checks pass

### Quick Feedback (faster iteration)

For faster feedback during development, run checks incrementally:
```bash
uv run ruff format . && uv run ruff check --fix .  # Format + lint (fast)
uv run mypy src/                                    # Type check
uv run pytest tests/unit -x                         # Unit tests, stop on first failure
```

---

## Branching Workflow (humans and agents)

- **Start all work from a new branch, not `main`:**
  ```bash
  git checkout main
  git pull origin main
  git checkout -b <branch-name>
  ```
- **All changes must go through a PR into `main`** — no direct pushes, even for small fixes.
- **`main` is only updated by merging PRs after CI passes** and the branch is up-to-date with `main`.

---

## Branch Protection

This repository uses branch protection on `main`:

- ✅ PRs required (no direct pushes)
- ✅ CI checks must pass before merge
- ✅ Branch must be up-to-date before merge

### Setting Up Branch Protection (maintainers)

1. Go to **Settings → Branches → Add branch protection rule**
2. Branch name pattern: `main`
3. Enable:
   - ☑️ Require a pull request before merging
   - ☑️ Require status checks to pass before merging
     - Add required checks: `Lint & Format`, `Type Check`, `Test (Python 3.10)`, `Test (Python 3.11)`, `Test (Python 3.12)`
   - ☑️ Require branches to be up to date before merging
   - ☑️ Do not allow bypassing the above settings

---

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**
```bash
bd ready --json
```

**Create new issues:**
```bash
bd create "Issue title" -t bug|feature|task -p 0-4 --json
bd create "Issue title" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**
```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**
```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`
6. **Commit together**: Always commit the `.beads/issues.jsonl` file together with the code changes so issue state stays in sync with code state

### Auto-Sync

bd automatically syncs with git:
- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### GitHub Copilot Integration

If using GitHub Copilot, also create `.github/copilot-instructions.md` for automatic instruction loading.
Run `bd onboard` to get the content, or see step 2 of the onboard instructions.

### MCP Server (Recommended)

If using Claude or MCP-compatible clients, install the beads MCP server:

```bash
pip install beads-mcp
```

Add to MCP config (e.g., `~/.config/claude/config.json`):
```json
{
  "beads": {
    "command": "beads-mcp",
    "args": []
  }
}
```

Then use `mcp__beads__*` functions instead of CLI commands.

### Managing AI-Generated Planning Documents

AI assistants often create planning and design documents during development:
- PLAN.md, IMPLEMENTATION.md, ARCHITECTURE.md
- DESIGN.md, CODEBASE_SUMMARY.md, INTEGRATION_PLAN.md
- TESTING_GUIDE.md, TECHNICAL_DESIGN.md, and similar files

**Best Practice: Use a dedicated directory for these ephemeral files**

**Recommended approach:**
- Create a `history/` directory in the project root
- Store ALL AI-generated planning/design docs in `history/`
- Keep the repository root clean and focused on permanent project files
- Only access `history/` when explicitly asked to review past planning

**Example .gitignore entry (optional):**
```
# AI planning documents (ephemeral)
history/
```

**Benefits:**
- ✅ Clean repository root
- ✅ Clear separation between ephemeral and permanent documentation
- ✅ Easy to exclude from version control if desired
- ✅ Preserves planning history for archeological research
- ✅ Reduces noise when browsing the project

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ✅ Store AI planning docs in `history/` directory
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems
- ❌ Do NOT clutter repo root with planning documents

For more details, see README.md and QUICKSTART.md.

## GitHub CLI (gh)

The `gh` CLI is available for GitHub operations:

```bash
# Issues and PRs
gh issue list
gh issue create --title "Title" --body "Description"
gh pr create --title "Title" --body "Description"
gh pr list
gh pr merge <number>

# Repository info
gh repo view
gh api /repos/{owner}/{repo}/...
```

Use `gh` for GitHub-specific operations (issues, PRs, releases, API calls).
