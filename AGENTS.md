# amux-skill (companion)

Cross-tool companion for the `amux-skill` skill (the amux HTTP API). Read `SKILL.md` first (core
families); read `references/long-tail.md` for the long-tail families: email,
Gmail, calendar, Telegram, browser, CRM, journal, files/fs, org, groups,
torrents, graph, map, SQL, dictation, TTS, habits, review, connectors.

## Purpose

Operate the **amux** agent-orchestration service (kanban board, workers,
schedules, memory, diagnostics) from any agent session over its HTTP API.

## Activation triggers

- "amux", "AMUX-* card/board/gate", "amux project / project tasks",
  "amux worker/session", "amux schedule",
  "amux memory/notes", "amux Telegram/browser/CRM"
- debugging the amux server or API (`$AMUX_URL`, `/api/debug/routes`)
- **Do NOT trigger** for generic kanban, generic cron, or non-amux HTTP work.

## Usage

```bash
export AMUX_URL=https://<amux-host>:8824
export AMUX_AUTH_TOKEN=<api token>

# every call: self-signed TLS + Bearer token
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/board"
```

- Only `/health` and `/` skip the token; every `/api/*` route requires it.
- Confirm with the user before write calls (create/update/delete cards,
  send messages, trigger schedules).
- `PUT /api/projects/<name>` and `POST /api/projects/draft` are operator-only:
  omit the `X-Amux-Worker` header on those two (403 if present). Project
  outcomes are submitted via `POST /api/projects/<name>/commands` (202, async
  intake) — tasks appear after the server decomposes them.
- 401 → auth problem; 409 gate_blocked → follow the gate rules in SKILL.md;
  404 → check `GET /api/debug/routes` before assuming a route exists.

## Gotchas

- Two 401s differ: `missing_credential` (no token sent) vs `invalid_bearer`
  (wrong token — usually the server was not restarted after a token change).
- The `amux` CLI does not send an Authorization header; remote CLI calls 401.
  Use the curl form from SKILL.md.
- Advancing a card can be blocked by its gate — that is a request to confirm,
  not a failure. `done` additionally requires a `source_ref` evidence pointer.
- Diagnostics: read `measured`/`n_considered` before trusting a zero count.
- Grep server logs with `-a` (a single NUL byte otherwise silences matches).
