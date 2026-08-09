---
description: Load project state and begin work on the current phase
---

Begin a SITS work session. Follow this exactly and do not skip steps.

## 1. Load state — read these, in this order, and nothing else yet

1. `PROGRESS.md` — find the RESUME HERE block. Note the current phase, its status, the next
   action, and any blockers.
2. `MEMORY.md` — Sections A (decisions), B (codebase facts), C (gotchas). Do not relitigate
   anything in Section A.
3. `PROMPTS.md` — **only** the block for the current phase.
4. `.claude/context/` — only the files the current phase's *Context* line names.

**Do not scan the repository.** Do not run `find`, `ls -R`, or grep across the tree to
orient yourself. The files above are the map. If they are wrong or stale, say so — fixing
them is the first task, ahead of any feature work.

## 2. Check for blockers

If `PROGRESS.md` lists an OPEN question that blocks the current phase, ask the user before
writing code. Do not guess at institutional policy.

## 3. Verify the environment

```bash
docker compose ps
```

If nothing is running: `docker compose up -d --build`, then confirm `/healthz/` returns 200.
If Phase 0 is not yet done, this step will fail — that is expected, and Phase 0 is the work.

## 4. State the plan

In five lines or fewer:

```
Phase:   N — <name> (<status>)
Goal:    <one sentence>
Slices:  <3–6 numbered slices you intend to complete this session>
Touches: <apps/files>
Risk:    <migrations? permissions? stock arithmetic? or "none">
```

Then start on slice 1. Do not ask permission to begin — the plan is the notification.

## 5. Work

- One slice at a time. Test after each: `docker compose exec web pytest -q`
- Append to `MEMORY.md` the moment you learn something surprising, not at the end.
- If a slice exceeds ~300 lines of diff, it was two slices — split it.

When the session ends, run `/session-end`.
