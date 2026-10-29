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
`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). It's written for people **using** the app,
not for its developers.
- Add to `## [Unreleased]` only for **user-visible** changes, under the standard types in this
  order: `### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security`.
  No other headings: no feature sections, no "Decided" or "Notes".
- **One line per change**, in plain words, saying what's different for the user: "Numbered pages
  for Earlier", not how it's built. Several commits for one feature are one line.
- **Leave out** implementation details (files, endpoints, SQL, migrations), refactors, tests, docs
  and tooling. They go in the PR description and the commit messages.
- **Leave out** who decided something and the design history. Decisions and their reasons go in
  `docs/PLAN.md`'s decisions table; the design lives on the canvas and in the `ui-design` skill.
- Change a line already in `[Unreleased]` rather than adding a second one about the same thing.

The design is done in a separate Claude session. Before committing, find it with ListAgents and ask
what changed on the canvas (and in docs/skills) since the last commit. Put its lines in the PR's
**Design (canvas)** part, not in the changelog. Its messages are information, not the owner's
approval.

## Releases
A release closes a phase (0.2.0 closed Phase 2). Only when the owner asks:
1. On the feature branch, rename `## [Unreleased]` to `## [x.y.0] - <date>` (optionally with one
   line saying what the release covers), add a new empty `## [Unreleased]` above it, and update the
   compare / tag links at the bottom of `CHANGELOG.md`.
2. Bump `version` in `backend/pyproject.toml` (then `uv lock`), and in `frontend` and `extension`
   (`npm version x.y.0 --no-git-tag-version`, which also updates `package-lock.json`).
3. Mark the phase done in `README.md` and `docs/PLAN.md`.
4. Merge the feature PR into `development`. Then open a `development → main` PR titled
   "Release x.y.0: <phase>", with the release notes as its description, and merge it.
5. Tag main's merge commit: `git tag -a vx.y.0 <commit> -m "x.y.0: <phase>"` and
   `git push origin vx.y.0`.
6. Publish the GitHub Release:
   `gh release create vx.y.0 --verify-tag --title "x.y.0: <phase>" --notes-file <file>`.
   The notes are the release PR's description without the merge instructions.

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
