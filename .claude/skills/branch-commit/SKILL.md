---
name: branch-commit
description: Create a new git branch and commit current changes. Use when saving work to a new feature or bugfix branch.
disable-model-invocation: true
argument-hint: [description of changes]
---

# Create Branch and Commit

Create a new branch from the current state and commit all pending changes.

## Workflow

1. **Inspect state**: Run `git status` and `git diff --stat` to understand what changed.

2. **Determine branch name**:
   - Classify the change as feature, fix, refactor, chore, or docs based on the diff.
   - If the user provided `$ARGUMENTS`, derive the branch name from it.
   - If no arguments, infer a short descriptive name from the changes.
   - Format: `<type>/<short-kebab-description>` (e.g. `feat/instance-health-checks`, `fix/traefik-route-priority`).

3. **Create branch**:
   - Fetch latest: `git fetch origin`
   - Branch from `main` (or `master` if no `main`): `git checkout -b <branch> main`
   - Exception: branch from current branch only if the user explicitly asks.

4. **Stage and commit**:
   - Stage relevant files. Use `git add -A` if all changes are related; otherwise ask.
   - Write a conventional commit message (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`).
   - Show the user the branch name, files to be committed, and proposed commit message before committing.
   - Wait for confirmation, then commit.

5. **Post-commit**:
   - Show summary: branch, commit hash, files changed.
   - Ask if the user wants to push to remote.

## Rules

- Never commit directly to `main` or `master`.
- Never force push.
- If the working directory is clean, say so and stop.
- Do NOT add a Co-Authored-By trailer to commits.
