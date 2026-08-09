---
description: Close the current phase and open the next one
---

Transition to the next phase. Do not skip the gate.

## 1. Gate — the current phase must genuinely be done

```bash
docker compose down -v && docker compose up --build -d    # cold start from empty volumes
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web pytest -q
docker compose exec web pytest -k isolation
docker compose exec web ruff check . && docker compose exec web ruff format --check .
docker compose exec web python manage.py seed_demo
```

Then walk the Definition of Done in `CLAUDE.md` §7 item by item. If any item fails, the phase
is not done — say which, set the status to `IN PROGRESS`, and continue working. Do not advance
on a partial pass; every later phase builds on this one.

## 2. Close

- `PROGRESS.md`: phase → `DONE`, fill the Done date, tick the checklist, update the test table
- `MEMORY.md`: record decisions and gotchas from the phase
- Update every context file the phase changed
- Commit: `feat(<scope>): complete Phase N — <name>`

## 3. Open the next phase

- Read the next phase block in `PROMPTS.md`
- `PROGRESS.md`: next phase → `IN PROGRESS`, Started date, **expand its task checklist now**
  (checklists are expanded on entry, never pre-expanded — they go stale)
- Update the RESUME HERE block
- Check whether the new phase depends on an OPEN question in `PROGRESS.md`. If so, ask the
  user before writing code.

## 4. Report

```
Phase N complete ✓   →   Phase N+1 open
Delivered:  <2–3 bullets>
Next up:    <goal of the new phase>
Blocked on: <open questions, or "nothing">
```
