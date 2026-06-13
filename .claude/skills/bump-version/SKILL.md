---
name: bump-version
description: Bump the ManulEngine version atomically across all 18 files using bump_version.py (the single source of truth is pyproject.toml). Invoke when the user says "bump to X.Y.Z", "онови версію", "cut a release", or any phrasing that implies a version change. Refuses to run if the working tree is on an inconsistent version base.
---

# bump-version

The canonical source of truth is `pyproject.toml → version`. The repository ships a `bump_version.py` helper that rewrites every other location (READMEs, Dockerfiles, GitHub workflows, contracts, copilot/cursor instruction files, custom-instructions). **Always go through this script — never edit version strings by hand.**

## When to invoke

- User says "bump to 0.0.X", "онови версію", "release X.Y.Z", "cut a new version".
- The current branch contains shipped behavior change and the user is preparing a PR.

Do NOT invoke when the user only updated docs and didn't change behavior — versions are bumped on real change.

## Inputs

- `args` form: `<new-version>` (e.g. `/bump-version 0.0.9.30`).
- If `args` is missing or malformed: ask the user for the target version. Never invent one.
- Version must match `^0\.\d+\.\d+(\.\d+)?$` (the regex used inside `bump_version.py`).

## Execution order

1. **Read current state.** Run `python bump_version.py --show` and `git status --porcelain` from the repo root. Confirm the displayed version matches the expectation (no half-applied previous bump). If `git status` shows uncommitted version-related drift, surface it and pause.
2. **Dry-run first.** `python bump_version.py <new> --dry-run` and inspect the per-file replacement count. Expect 35 replacements across 18 files for a clean bump. If the count is wildly off, stop — the regex set in `bump_version.py:TARGETS` may have rotted; investigate before applying.
3. **Apply.** `python bump_version.py <new>`.
4. **Verify.** `python bump_version.py --show` again, then `git diff --stat` so the user can see exactly which files moved.
5. **Sync mirrored files.** `.github/copilot-instructions.md` and `custom-instructions/repo/.github/copilot-instructions.md` are expected to stay byte-identical to their template. If a contract was updated alongside the bump, run a `diff` and surface any mismatch.
6. **Do NOT commit or tag automatically.** End by reporting `git diff --stat` and pasting the suggested follow-up command from `bump_version.py` output (`git add -A && git commit … ; git tag v<new>`). The user runs the commit.

## Common mistakes to avoid

- Editing the version in `pyproject.toml` only — `bump_version.py` covers 16 *other* locations including all 8 contract files in `contracts/`.
- Running the bump while contracts still describe the previous behavior. Bump after contracts are updated, never before.
- Bumping when no behavioral change shipped — a version bump on no-op churn is noise.
- Forgetting `custom-instructions/repo/.github/copilot-instructions.md` — it carries the version twice. The script handles both, but a hand-edit will miss the second occurrence.

## Reference

- Script: `bump_version.py` (project root).
- Source of truth: `pyproject.toml → [project] version`.
- Files updated: see `TARGETS` in `bump_version.py` — currently 18 unique files, 35 substitutions.
