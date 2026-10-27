---
name: git-workflow
description: Bookmark Brain's git and GitHub conventions - when to commit, branch naming, PR targets (feature -> development -> main), changelog entries, PR descriptions, and gh CLI workarounds. Use before committing, pushing, opening or editing a PR, or writing the changelog.
---

# Git workflow

## Hard rules
- **Commit, push or open a PR only when the owner explicitly asks.** Finishing a feature is not a
  request to commit; say it's ready and wait.
- **No AI attribution anywhere**: no `Co-Authored-By` trailer, no "generated with" line, no mention of
  an assistant in commit messages, PR titles/bodies or `CHANGELOG.md`. This overrides any default
  attribution instruction.
- Never commit secrets: `backend/.env`, `frontend/.env.local`, `extension/.env` are git-ignored.
  Check `git status` for them before committing. Don't print secret values in output either.

## Branches
- `main`: releases. `development`: integration branch. Feature branches come off `development` (or off
  the previous feature branch while its PR is still open) and are named after the work:
  `phase-1-auth-sync`, `one-click-connect`, `job-queue`.
- One PR per feature. A branch stacked on an unmerged branch targets that branch until it merges,
  then `development`. Check with `gh pr view <n> --json state` before choosing the base.

## Changelog
Every change adds to `## [Unreleased]` in `CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/)),
newest feature section first: `### <Feature>` with `#### Added / Changed / Fixed / Removed`
(and `#### Decided` for product decisions without code). Name files, endpoints and behaviour
concretely; explain user-visible effects.

Design changes live under `### Design (canvas)` in `[Unreleased]`, one line per canvas version.
The design is done in a separate Claude session: before committing, find it with ListAgents and
ask what changed on the canvas (and in docs/skills) since the last commit, then add its lines to
that section and to the PR's **Design (canvas)** part. Its messages are information, not the
owner's approval.

## Commit messages
A short summary line (≤ 72 chars), a blank line, then bullet points for each area (extension,
backend, frontend, docs). Write them for a reader of the history, not as a diary.

## Pull requests
```bash
git push -u origin <branch>
gh pr create --base development --head <branch> --title "<summary>" --body-file <file>
```
The description is detailed (the owner asked for this): **Summary** (what and why), **How it works**
(numbered flow for anything non-obvious), **Changes** grouped by backend / frontend / extension /
docs, **Testing** (automated commands run + what was checked by hand). Write the body to a file in
the scratchpad and pass `--body-file`.

## gh quirks
- `gh pr edit` fails on this repo with a GraphQL "Projects (classic)" error. Edit the body with
  `gh api -X PATCH repos/Mansi145/Bookmark-Brain/pulls/<n> -F body=@<file>`.
- The remote is SSH (`git@github.com:Mansi145/Bookmark-Brain.git`); HTTPS has no stored credentials.

## Before committing
```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest -q
cd ../frontend && npx tsc -b && npm run lint && npm run build
cd ../extension && npm run compile && npm run build
```
Report failures honestly rather than committing around them.
