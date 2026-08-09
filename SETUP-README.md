# How to install this setup bundle

Drop these files into the root of your `Inventory-Management-System` clone, open it in
VS Code, and start Claude Code.

```
Inventory-Management-System/
├── CLAUDE.md              ← auto-loaded by Claude Code every session
├── INSTRUCTIONS.md
├── PROMPTS.md
├── PROGRESS.md
├── MEMORY.md
├── ANALYSIS.md
├── SETUP-README.md        ← this file; delete after reading
└── .claude/
    ├── settings.json
    ├── commands/
    │   ├── session-start.md
    │   ├── session-end.md
    │   ├── checkpoint.md
    │   ├── next-phase.md
    │   └── verify-tenancy.md
    └── context/
        ├── 01-domain-model.md
        ├── 02-tenancy.md
        ├── 03-stack-and-docker.md
        └── 04-conventions.md
```

## First session

```
/session-start
```

It will read `PROGRESS.md`, find Phase 0, and propose a plan. Answer Q1 in
`PROGRESS.md` (the exact organisation names) when it asks — that unblocks Phase 1.

If you'd rather be explicit, just say: **"Start Phase 0"**.

## Every session after that

| Command | When |
|---|---|
| `/session-start` | Beginning of a session |
| `/checkpoint` | Before a risky change; every ~45 min |
| `/verify-tenancy` | End of every phase from Phase 2 onward |
| `/next-phase` | When a phase passes its Definition of Done |
| `/session-end` | **Always**, before you close VS Code |

## Which file does what

| File | Role | Who edits it |
|---|---|---|
| `CLAUDE.md` | Project rules and constraints. Auto-loaded. | You (rarely), Claude (rarer) |
| `PROMPTS.md` | The 13-phase build brief | You, if scope changes |
| `PROGRESS.md` | Live status and the resume point | Claude, every session |
| `MEMORY.md` | Append-only decision log | Claude, as decisions happen |
| `INSTRUCTIONS.md` | Session protocol + command reference | Claude updates the bottom block |
| `ANALYSIS.md` | Audit of the original repo | Read once, then ignore |
| `.claude/context/*` | Architecture reference so Claude never rescans the codebase | Claude, same commit as the change |

## Two things to know

**`docker compose down -v` is in the deny list** in `settings.json`. It destroys your database
volume, and `/next-phase` legitimately uses it for cold-start verification — so Claude will ask
you first each time. Say yes when it's a cold-start check, and think twice at any other point.

**Answer the open questions.** `PROGRESS.md` has eight. Q1–Q3 (organisation names, store
structure, approval thresholds) should be answered before Phase 1, or Claude will make
assumptions you'll have to unpick later.

## Adjusting the plan

The phase order in `PROMPTS.md` is deliberate — tenancy before models, procurement before
issuance, intelligence last because it needs history to learn from. Reordering is possible but
Phases 0 → 1 → 2 → 3 are genuinely sequential. If you want to demo something early, the
cheapest impressive slice is Phase 0 → 1 → 2, which gets you a working multi-tenant portal with
the existing UI intact.
