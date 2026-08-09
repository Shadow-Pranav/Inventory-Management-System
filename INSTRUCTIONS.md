# INSTRUCTIONS.md — Working Protocol

How Claude Code operates in this repository. `CLAUDE.md` says *what* we build;
this says *how the sessions run*.

**Auto-maintained.** The "Current state" section at the bottom is rewritten by `/session-end`.
Everything above it is stable policy — change it only when a rule genuinely changes.

---

## 1. The session loop

```
START ──► read PROGRESS.md ──► read MEMORY.md ──► read PROMPTS.md (current phase only)
      ──► read the context files that phase names ──► state the plan in ≤5 lines
      ──► WORK in slices ──► test after each slice ──► /session-end ──► handoff summary
```

**Reading budget at session start: five files.** `PROGRESS.md`, `MEMORY.md`, the current phase
of `PROMPTS.md`, and one or two context files. That is the entire point of this setup — if you
find yourself running `find` or grepping the whole tree to work out where things are, the
context files have gone stale and fixing them takes priority over the feature.

---

## 2. Slicing work

A slice is the smallest change that leaves the system working and testable. Order within a slice:

```
model → migration → factory → test → admin → service → selector → view → form → template → test
```

Run tests between slices, not at the end. A phase is many slices and many commits.

If a slice grows past ~300 lines of diff, it was two slices. Split it.

---

## 3. Command reference (everything runs in Docker)

```bash
# lifecycle
docker compose up --build              # start
docker compose down                    # stop, keep data
docker compose down -v                 # stop, DESTROY data — never against real data
docker compose --profile async up -d worker beat     # Phase 8+
docker compose --profile dev up -d mailhog

# django
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py makemigrations --check --dry-run   # CI gate
docker compose exec web python manage.py migrate
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py shell_plus
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py createsuperuser

# quality
docker compose exec web pytest -q
docker compose exec web pytest apps/tenancy -x -vv          # one app, stop on first failure
docker compose exec web pytest -k isolation                 # tenancy suite only
docker compose exec web pytest --cov=apps --cov-report=term-missing
docker compose exec web ruff check . --fix
docker compose exec web ruff format .

# db
docker compose exec db psql -U sits -d sits
docker compose exec db pg_dump -U sits sits > backup.sql

# logs
docker compose logs -f web
docker compose logs -f worker
```

Never run `python manage.py` without `docker compose exec`. There is no host Python.

---

## 4. When you get stuck

1. **Migration conflict** — `showmigrations` first. Never `--fake`. If branched, merge with
   `makemigrations --merge`. If genuinely tangled and there is no real data,
   `docker compose down -v` and rebuild from scratch is legitimate and fast.
2. **Container won't start** — `docker compose logs web`. Check `entrypoint.sh` is executable
   and LF-terminated (see `MEMORY.md` F-07).
3. **A test fails after a "safe" refactor** — the test is probably right. Investigate before
   changing it. Never widen a permission to make a test pass; that is the failure mode this
   whole setup exists to prevent.
4. **Requirement is ambiguous** — stop and ask the user. Do not invent institutional policy
   about approval hierarchies, fiscal years or write-off authority. Log the question in
   `PROGRESS.md` → Open questions.
5. **Something in a context file contradicts the code** — the code wins. Fix the context file
   in the same commit.

---

## 5. Auto-update contract

These files are maintained by Claude Code, not by hand. `/session-end` enforces it.

| File | Updated when | By |
|---|---|---|
| `PROGRESS.md` | Every session, without exception | `/session-end` |
| `MEMORY.md` | A decision, gotcha or codebase fact appears | Immediately, mid-session |
| `.claude/context/01-domain-model.md` | Any model added, renamed, or field changed | Same commit as the model change |
| `.claude/context/02-tenancy.md` | Scoping, roles or middleware change | Same commit |
| `.claude/context/03-stack-and-docker.md` | A service, dependency or env var changes | Same commit |
| `.claude/context/04-conventions.md` | A convention is established or revised | Same commit |
| `INSTRUCTIONS.md` § Current state | Every session | `/session-end` |
| `CLAUDE.md` | Only when a project-wide rule changes | Rare, deliberate |
| `PROMPTS.md` | A phase's scope genuinely changes | Rare — record why in `MEMORY.md` |

**Why this matters:** the alternative is that every session begins by reading 8,000 lines of
code to rediscover the architecture. That is slow, expensive, and the reconstruction is often
subtly wrong. Twenty lines of `PROGRESS.md` replaces it.

---

## 6. Quality gates — no phase closes without these

```bash
docker compose exec web python manage.py makemigrations --check --dry-run   # nothing pending
docker compose exec web pytest -q                                           # green
docker compose exec web pytest -k isolation                                 # green
docker compose exec web ruff check .                                        # clean
docker compose exec web ruff format --check .                               # clean
docker compose exec web python manage.py check --deploy                     # Phase 12
docker compose down -v && docker compose up --build                         # cold start works
```

---

## 7. Communication style

- Lead with what changed and what it means, not a narration of the steps taken.
- Show diffs for non-obvious edits; skip them for boilerplate.
- Flag risky changes explicitly: migrations, permission changes, anything touching
  `apply_movement()`.
- If a decision was made on the user's behalf, say so and say why, so it can be overruled.
- End every session with the five-line handoff.

---

## 8. Handoff format

```
── HANDOFF ──────────────────────────────
Phase:    N — <name> (<status>)
Done:     <what landed this session>
Next:     <the single next action>
Watch:    <anything fragile or half-finished>
Files:    PROGRESS.md, MEMORY.md, <context files> updated ✓
─────────────────────────────────────────
```

---

## 9. CURRENT STATE — auto-updated, do not hand-edit

```
Last updated:     Session 1 (2026-08-09)
Phase:            1 — Tenancy foundation
Status:           IN PROGRESS — all 9 tasks built & tested, not yet gated via /next-phase
Apps existing:    apps.core (scoping machinery, forms, factories, /healthz/),
                  apps.tenancy (Organization, Department, User, Membership, middleware,
                  decorators, org switcher, seed_demo/create_trust_admin)
Models existing:  tenancy.Organization, tenancy.Department (TenantOwnedModel),
                  tenancy.User (AUTH_USER_MODEL, USERNAME_FIELD=email), tenancy.Membership
Migrations:       tenancy 0001_initial, 0002_seed_organizations (7 SRMS orgs from fixture)
                  + django built-ins + django_celery_beat
Tests:            19 passing — core/tests/test_healthz.py (1),
                  tenancy/tests/test_isolation.py (7), tenancy/tests/test_decorators.py (11)
Docker:           up and healthy. DB was dropped/recreated via psql this session for the
                  AUTH_USER_MODEL swap (D-13) — approved, narrower than docker compose down -v
Celery:           wired (config/celery.py), not yet exercised
Next action:      run /next-phase to gate Phase 1 closed (needs a user-run cold-start check,
                  same as Phase 0 — see G-05) and open Phase 2
Open blockers:    none for Phase 2. Q4-Q8 still open, needed before Phase 5.
```
