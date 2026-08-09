---
description: Mid-session save without ending the session
---

Save state without closing the session. Use this before a risky change (a migration, a
permission refactor, anything touching `apply_movement()`), or roughly every 45 minutes of work.

1. Run `docker compose exec web pytest -q` and note the result.
2. Update **only** the RESUME HERE block in `PROGRESS.md` — current phase, phase status, and a
   concrete next action reflecting exactly where you are right now.
3. Append anything learned to `MEMORY.md` Section B or C.
4. Commit work-in-progress:
   ```bash
   git add -A && git commit -m "wip(<scope>): <what is half-done>"
   ```
5. Print one line: `Checkpoint: <phase> — <next action>`

Do not update the full progress board, the context files, or `INSTRUCTIONS.md`. That is
`/session-end`'s job. Keep this cheap so it actually gets used.
