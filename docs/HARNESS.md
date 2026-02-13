# PaperBot Long-Running Harness

This document defines the default harness workflow for multi-session agent work in this repository.

## Goals

- Keep every session incremental and reversible.
- Ensure each session starts with enough context to avoid rework.
- Ship production-ready changes without leaving hidden breakage.

## Session Roles

Use two roles conceptually, even if one person runs both.

1. Initializer
   - Create/update planning artifacts and acceptance contracts.
   - Prepare bootstrap commands and verify baseline health checks.
2. Coding Agent
   - Pick one highest-priority unfinished issue.
   - Implement, validate, commit, and leave clean handoff notes.

## Required Artifacts

- `docs/issue_contract.json`: source of truth for issue acceptance contracts.
- `docs/progress/progress.txt`: append-only progress log for shift handoff.
- `scripts/session_bootstrap.sh`: mandatory context bootstrap script.

## Session Start Checklist (mandatory)

Run this command first:

```bash
./scripts/session_bootstrap.sh
```

Then confirm:

1. Working tree status is understood.
2. Last 10-20 commits reviewed.
3. Current open tasks and contract statuses are known.
4. Core smoke checks pass before starting new work.

## Session Execution Rules

- Work on one issue-sized unit at a time.
- Prefer minimal, local, test-backed changes.
- If regression is found, fix regression before starting new work.
- Do not change issue acceptance criteria ad hoc.

## Session End Checklist (mandatory)

1. Run targeted validation for changed areas.
2. Commit with descriptive message.
3. Update `docs/progress/progress.txt` with:
   - What was changed
   - Validation run
   - Remaining risks
   - Next recommended issue
4. Leave repository in clean working state.

## Contract Editing Policy

`docs/issue_contract.json` is controlled.

- Allowed during normal coding: `status`, `owner`, `updated_at`, and `notes`.
- Disallowed without explicit product decision: issue ids, acceptance criteria, or scope definition.

## Quality Bar

A task is complete only when all are true:

- Acceptance criteria met.
- Regression check passed for impacted critical flow.
- No known blocker left undocumented.
- Handoff note recorded in `docs/progress/progress.txt`.
