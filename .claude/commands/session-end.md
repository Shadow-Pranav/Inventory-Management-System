---
description: Persist session state so the next session resumes without rescanning the codebase
---

Close out this SITS session. **Every step is mandatory.** A session that ends without these
updates forces the next one to re-derive everything from source, which is slow and often
subtly wrong.

## 1. Verify before recording

```bash
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web pytest -q
docker compose exec web ruff check .
```

Record the real results. If something is failing, say so plainly in `PROGRESS.md` and set the
phase to `BLOCKED` with the reason. Never mark a phase `DONE` on a red suite.

## 2. Update `PROGRESS.md`

- **RESUME HERE block** — rewrite completely:
  - `Last session` → today's date + a one-line summary
  - `Current phase` / `Phase status`
  - `Next action` → **one specific, concrete action.** Not "continue Phase 3" but
    "add `require_role` to `apps/procurement/views.py`, then write the auditor-403 test".
  - `Blockers`
- **Phase board** — update the status row; fill Started/Done dates.
- **Task checklist** — tick what landed. If the phase just started, expand its checklist now.
- **Files created so far** — add any new apps, models or significant modules. This tree is how
  the next session knows the layout without scanning.
- **Test status table** — real numbers from the run above.
- **Open questions** — add any new ones; fill in answers received this session.
- **Session log** — prepend a three-line entry.

## 3. Append to `MEMORY.md`

Only genuinely durable things. Not a diary.

- **Section A** — any architectural decision made. Include the *why* and the trade-off
  accepted. If a prior decision was reversed, add a new entry and mark the old
  `SUPERSEDED by D-NN`.
- **Section B** — any codebase fact worth not rediscovering.
- **Section C** — any gotcha, using the symptom → cause → fix → watch-for template.
- **Section D** — anything deliberately deferred, and by when it must be decided.

If nothing durable happened, write nothing. An empty append is better than noise.

## 4. Update the context files that changed

| If this changed | Update |
|---|---|
| A model, field or constraint | `.claude/context/01-domain-model.md` |
| Scoping, roles, middleware, decorators | `.claude/context/02-tenancy.md` |
| A service, dependency, env var, compose entry | `.claude/context/03-stack-and-docker.md` |
| A convention or pattern | `.claude/context/04-conventions.md` |

These files must describe the code **as it is now**, not as it was planned. Where they
disagree with the code, the code is right and the file is a bug.

## 5. Update `INSTRUCTIONS.md` § CURRENT STATE

Rewrite the fenced block at the bottom: phase, status, apps, models, migration count, test
count, docker/celery status, next action, blockers. This is the fastest possible orientation
for the next session — keep it accurate and terse.

## 6. Update `CLAUDE.md` — only if a project-wide rule changed

Rare. If the tenancy strategy, role model, or a non-negotiable constraint shifted, reflect it
and note the change in `MEMORY.md`. Otherwise leave it alone.

## 7. Commit

```bash
git add -A
git commit -m "<type>(<scope>): <what landed>

Phase N: <slices completed>
Docs: PROGRESS.md, MEMORY.md, <context files> updated"
```

## 8. Print the handoff

```
── HANDOFF ──────────────────────────────
Phase:    N — <name> (<status>)
Done:     <what landed this session>
Next:     <the single next action>
Watch:    <anything fragile or half-finished>
Files:    PROGRESS.md, MEMORY.md, <context files> updated ✓
─────────────────────────────────────────
```
