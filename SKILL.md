---
name: amux-skill
description: Use when the user mentions amux, the AMUX-* kanban board, board cards or gates, amux projects or project tasks, amux workers/sessions, schedules, memory or notes, Telegram routing, browser automation, CRM, or debugging the amux server/API — talks to the amux HTTP API with curl using $AMUX_URL and $AMUX_AUTH_TOKEN.
license: MIT + Commons Clause
activation: /amux
metadata:
  author: amux
  version: 1.0.0
  created: 2026-09-29
  last_reviewed: 2026-09-30
  review_interval_days: 90
  dependencies:
    - name: amux HTTP API
      url: https://localhost:8824
      type: service
      tls_verify: false
  schema_expectations:
    - url: https://localhost:8824/health
      method: GET
      tls_verify: false
      expected_keys:
        - status
        - build
        - commit
        - store
        - board
provenance:
  maintainer: amux
  version: 1.0.0
  created: 2026-09-29
  source_references: []
---

# amux — HTTP API client

amux is a local/LAN agent-orchestration service (board + workers + schedules +
memory + a pile of small APIs). Every interaction is HTTPS JSON: `curl -sk` +
Bearer token. **There is no MCP server — do not go looking for one.**

Long-tail families (email, Gmail, calendar, Telegram, browser, CRM, journal,
files/fs, org, groups, torrents, graph, map, SQL, dictation, TTS, habits,
review, connectors): Read `references/long-tail.md` for one verified example
per route — confirm the route on `GET /api/debug/routes` first.

## 0. Prerequisites: environment variables

```bash
export AMUX_URL=https://<amux-host-ip>:8824   # self-signed cert, port 8824
export AMUX_AUTH_TOKEN=<api token configured on the amux server>
```

- **Send `Authorization: Bearer $AMUX_AUTH_TOKEN` on every `/api/*` call.** A
  measured handful of probe/diagnostic routes skip it (exact list in the
  "Token boundary" Gotcha); `/health` and `/` are the two you should actually
  probe with.
- No token → `401 {"error":"unauthorized","reason":"missing_credential"}`;
  wrong token → `401 invalid_bearer` (most common cause: the server's token
  changed without a `docker compose restart`).
- If either variable is unset, ask the user. Never guess, never print the token.
- Certificate is self-signed: every curl needs `-sk`.

## 1. Standard call templates

```bash
# read
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/board"

# write (JSON body)
curl -sk -X POST \
  -H "Authorization: Bearer $AMUX_AUTH_TOKEN" \
  -H 'Content-Type: application/json' \
  -H "X-Amux-Worker: ${AMUX_WORKER:-opencode}" \
  -d '{"title":"...","type":"code"}' "$AMUX_URL/api/board"
```

- `X-Amux-Worker` attributes the write in the server log (optional, but it makes
  diagnostics easier). **Exception: the operator-only project routes reject
  requests that carry it** — see §7.
- Failure triage: 401 → token problem; 409 `gate_blocked` → §2 gates;
  404 → read the real route table with `GET /api/debug/routes` (the table wins
  over any written doc).

## 2. Board (cards)

```bash
# list / one card / create / delete
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/board"
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/board/AMUX-1"
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Fix the login error copy","type":"code","desc":"..."}' "$AMUX_URL/api/board"
curl -sk -X DELETE -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/board/AMUX-1"

# claim (atomic — keeps two workers from grabbing the same card)
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"session":"my-worker"}' "$AMUX_URL/api/board/AMUX-1/claim"
```

Status flow: `backlog` → `todo` → `doing` → `done` (`done ≠ verified` — they are
two separate gates).

**Create defaults to `status:"todo"`** — omit `status` and the card lands in
`todo`, not `backlog`. `todo` is the *dispatch-checked* population: the
`todo_is_reachable_by_dispatch` invariant counts managed todo cards on lanes
with no registered worker as failures (amux `frustrations.md` AF-957), and
lane todo WIP limits apply to them. A record lane (a project session with no
workers) should pass `"status":"backlog"` explicitly — `backlog` is checked
by neither. A todo filed on an isolated lane is silently stored as `backlog`
anyway; look for the `todo_defaulted_to_backlog` log marker.

**Reading full text.** `GET /api/board` returns *slim* rows: `desc` is
absent — not empty — replaced by `desc_head` + `desc_len`, and a `slim`
array names every dropped field. Read `desc_len`/`slim`, or fetch the whole
card. Full description comes from `GET /api/board/{id}`, or from
`GET /api/board/export?format=json|md` — whose payload key is **`issues`**
(there is no `cards`/`items`; it names the underlying table) and whose
`desc` field is a self-describing note about completeness, not card
content.

**Gates.** Advancing status on gated types (`code` and most others) is
intercepted. **That is not a failure, it is a request to confirm:**

```json
{"blocked":true,"error":"gate not acknowledged",
 "gate":["Scope & acceptance criteria are clear","No blocking dependency","Has an owner"],
 "cli":"amux board doing AMUX-5 --checked \"Scope & acceptance criteria are clear\" ..."}
```

- Follow the response's `cli` field, or just PATCH with
  `{"status":"doing","gate_ack":true}` (acknowledges the whole gate — simplest).
- **Fix the type first if the type is wrong** (gates are derived from `type`);
  do not acknowledge criteria that did not happen.

**`done` requires evidence** — `gate_ack` alone is not enough:

```bash
curl -sk -X PATCH -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"status":"done","source_ref":"<commit sha | URL | file path | PR number>"}' \
  "$AMUX_URL/api/board/AMUX-1"
```

No artifact? Write `"source_ref":"none: <reason>"` (it is recorded and counted,
not a bypass).
Gate details: `GET /api/board/contract?card=AMUX-1`.

## 3. Workers / Sessions

```bash
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/workers"           # list
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/workers/WORKER_ID" # one
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/workers/WORKER_ID/start"
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/workers/WORKER_ID/stop"
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"continue with the next step"}' "$AMUX_URL/api/workers/WORKER_ID/send"   # inject into a live session
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/workers/WORKER_ID/peek"
```

`/api/sessions/*` is the legacy spelling of the same shapes (`send`/`peek`/
`list`); new code uses `/api/workers/*`. More worker verbs (pause/resume/keys/
steer/git sub-resources/dead-letters) are documented in `references/long-tail.md`.

`sessions send` injects input into a **real running agent session** — use it
deliberately, never as a smoke test.

## 4. Memory / Notes

```bash
# per-session memory (read-modify-write: read first — set overwrites)
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/sessions/NAME/memory"
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"content":"# Notes\n..."}' "$AMUX_URL/api/sessions/NAME/memory"

# global memory
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/memory/global"

# notes/documents are the `memories` primitive (**there is no /api/notes route — do not use it**)
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/memories"
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"scope":{"level":"global"},"name":"runbook","content":"# ...","memory_type":"reference"}' \
  "$AMUX_URL/api/memories"
curl -sk -X PATCH -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"content":"updated body"}' "$AMUX_URL/api/memories/MEMORY_ID"
curl -sk -X DELETE -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/memories/MEMORY_ID"
```

`memory_type`: `reference` (documents/runbooks), also `project`, `user`,
`feedback`. Scope can be `global`, `group`, or `worker`.

## 5. Schedules (recurring / one-shot)

```bash
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/schedules"
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Daily check","session":"lane-x","command":"check the pipeline and post a summary to the board",
       "kind":"tmux","sched_type":"recurring","schedule_expr":"0 9 * * 1"}' \
  "$AMUX_URL/api/schedules"
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/schedules/RUN_ID/run"  # run now
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/schedules/runs"               # recent runs
curl -sk -X PATCH -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled":0}' "$AMUX_URL/api/schedules/RUN_ID"
```

Fields: `once` uses `run_at` (ISO), `recurring` uses `schedule_expr`
(5-field cron). `watch`, `watch_timeout`, `done_pattern`, `done_action`,
`trigger_on`, `trigger_sessions` are **refused with 400** on this server — they
were never ported; see `references/long-tail.md`.

## 6. Diagnostics (check these before grepping logs)

| Endpoint | Use |
|---|---|
| `GET /health` | liveness, build/commit, store (**token-free**, use this to probe) |
| `GET /api/health/invariants` | invariants currently failing |
| `GET /api/logs/analyze?since_h=24` | error groups + verdicts |
| `GET /api/logs/stats?since_h=24` | traffic/latency |
| `GET /api/debug/routes` | **the live route table — check this before assuming a route exists** |
| `GET /api/debug/sse?since_h=24` | has realtime degraded to polling |
| `GET /api/debug/tmux` | session discovery as the server sees it |
| `GET /api/system-jobs` | are the background loops running |

**Token-free for probing** (measured 2026-09-30): `/health`, `/`, the four
`/api/debug/*` rows above, `/api/health/invariants`, `/api/system-jobs`,
`/manifest.json`, `/api/calendar.ics`. Everything else in this table needs the
Bearer (§0).

**Read `measured` before the number**: `total_errors: 0, measured: false` means
"not measured", not "no errors". `n_considered` is the other half — it says how
big the population behind the number was, and a 0 there means the probe never
saw a row. Grep server logs on the host with `-a` — one NUL byte makes grep
treat the whole file as binary and silently drop matches.

## 7. Projects (project → tasks)

A project is a task container (board cards carrying `project_group`). You submit
an **outcome**; the server's intake decomposes it asynchronously into cards,
which the project's dedicated worker then executes.

**Which project?** amux has no repo→project registry — the local-project →
amux-project name mapping is YOUR integration config (one name per project).
The name must PASS `valid_name`: starts `[a-z0-9]`, then `[a-z0-9_-]`,
≤48 chars. The server never rewrites it — a violation is a hard
`400 invalid project name`, so pick a conforming name yourself (`MyRepo` is
rejected, not lowercased; send `myrepo`). Both calls below are operator
calls (no `X-Amux-Worker` header):

```bash
# discover: 200 {measured, n_considered, projects:[{name, revision, policy, ...}]}
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/projects"

# ensure-exists, idempotent: 200 = created; 409 "revision conflict:
# expected 0, current N" = already there → treat as success, use it as-is;
# 400 "invalid project name" = the name fails valid_name (above) — pick
# another name, the server does not rewrite it
curl -sk -X PUT -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"expect_rev":0,"policy":{"repository":"/abs/path/or/placeholder",
       "coordinator":{"provider":"claude","model":"<model>"},
       "executor":{"provider":"codex","model":"<model>"},
       "verify_command":"<command>"}}' \
  "$AMUX_URL/api/projects/<name>"
```

- Those four policy fields are the minimum. `repository` is checked for
  absolute-path SHAPE only — and it is resolved on the **amux server**,
  never on client machines: other dev machines' checkouts and local paths
  are irrelevant to amux (each machine maps its local path → project name
  in its own integration config). A path the server cannot reach is legal
  while `enabled` is false — the driver refuses every run before any
  filesystem access (`project_paused_or_disabled`) — and omitting
  `enabled` defaults it to false. So a project can exist purely as a
  config record on a server that never holds the code; before enabling
  execution, make sure the SERVER (its container — check the compose
  mounts) can reach the path.
- To EDIT an existing project: `GET` its `revision` first and send it back;
  `expect_rev:0` on an existing project is always 409, never an overwrite.

**Submit modes** — declare one per integration (your config, e.g.
`amux_submit_mode`); do not probe at runtime, a probe parks rows:

| mode | server capability | submit task as | read tasks back |
|---|---|---|---|
| `lane` | no intake models | `POST /api/board` with `session:"<project>"` (+`status`, +`tags`) | `GET /api/board?session=<project>` |
| `command` | intake models configured | `POST /api/projects/<name>/commands` → 202 | poll `GET /api/projects/<name>` → `cards` |
| `project_group` | build with project-group attach (not yet shipped) | `POST /api/board` with `project_group:"<project>"` | `GET /api/projects/<name>` → `cards` |

- `lane` mode: never submit via `commands` — it answers 202 and, with no
  model client wired, intake returns immediately and the row stays pending
  forever.
- `lane` mode: omit `X-Amux-Worker`. With the header present, `session` must
  equal that worker or the create → 403 `cross_board_create_forbidden`.
- `session` is a first-class board filter; `?tag=` is NOT one — it is dropped
  with an ignored-param WARN and the unfiltered answer comes back
  (BACKE-3228).
- `lane` mode: pass `status` explicitly — create defaults to `todo`, the
  dispatch-checked population (§2); a record lane wants `backlog`.
- `project_group` is not writable yet: create/PATCH report the key in
  `ignored_fields` and the card lands unowned. Confirm the response no
  longer lists it before relying on the mode.
- The project board (`GET /api/projects/<name>` → `cards`) only ever shows
  `project_group` cards — in `lane` mode it reads `cards: []` while the lane
  holds the work. Expected, not a bug.

```bash
# list / one project's board (tasks, commands, acceptance state)
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/projects"
curl -sk -H "Authorization: Bearer $AMUX_AUTH_TOKEN" "$AMUX_URL/api/projects/<name>"

# create (expect_rev:0 = creation; initial_command submits the first outcome too)
curl -sk -X PUT -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"expect_rev":0,
       "policy":{"repository":"/abs/path/to/repo",
                 "coordinator":{"provider":"claude","model":"<model>"},
                 "executor":{"provider":"codex","model":"<model>"},
                 "verify_command":"<a command that runs in the repo>"},
       "initial_command":{"idempotency_key":"<uuid>","text":"Build <outcome> and hand over evidence"}}' \
  "$AMUX_URL/api/projects/<name>"

# add another outcome to an existing project → 202, decomposed asynchronously
curl -sk -X POST -H "Authorization: Bearer $AMUX_AUTH_TOKEN" -H 'Content-Type: application/json' \
  -d '{"idempotency_key":"<uuid>","text":"add one more outcome"}' "$AMUX_URL/api/projects/<name>/commands"

# task side / acceptance / migration
# POST /api/projects/<name>/tasks/<id>/{report,wait,retry,required-outputs}
# POST /api/projects/<name>/acceptance/{approve,rerun}
# POST /api/projects/<name>/migration/{preview,apply,rollback}
```

- **Operator-only writes**: `PUT /api/projects/<name>` (create/reconfigure) and
  `POST /api/projects/draft` require the request to carry **no `X-Amux-Worker`
  header**; with it you get `403 operator setting`. The §1 template adds that
  header by default — **drop that line** for these two calls.
- `expect_rev:0` is creation only. To change an existing project, `GET` its
  current `revision` and send it back; mismatch → 409.
- `commands` is **async intake**: it answers `202 {id, state:"accepted"}` and
  the tasks appear later — "no tasks yet" is not a failure. Poll
  `GET /api/projects/<name>` (the board list has **no** `?project=` filter).
- Project tasks are ordinary cards (`project_group` field), so §2's status
  flow, gates and `done`-needs-evidence rules apply unchanged.
- **The deployed binary may predate this doc**: `GET /api/projects` 404 (or a
  route table with no `/api/projects`) is not your call being wrong — check
  which binary is live first. `/health` cannot tell you: prebuilt images carry
  no build stamp, so it reports `commit: "unknown"` (measured on both the old
  and the rebuilt image, 2026-09-30). Read the route-table fingerprint instead:

  ```bash
  curl -sk "$AMUX_URL/api/debug/routes" | python3 -c '
  import json,sys; d=json.load(sys.stdin)
  print(d["count"], sum(1 for r in d["routes"] if r["path"].startswith("/api/projects")))'
  # current (serves /api/projects):        478 16
  # pre-projects build (7b84f923):         422 0
  ```

  Why it happens: `ghcr.io/mixpeek/amux:latest` only advances when the `rust`
  workflow is green — a red run leaves `deploy-cloud.yml` skipped and the
  digest frozen (`sha256:902448decf09…` = build `7b84f923`, 2026-09-23, still
  being served days later while origin/main moved on), so the container serves
  stale code with nothing in `/health` saying so.

## 8. Which family (routing table)

| Need | Use |
|---|---|
| Tasks / action items | `/api/board` |
| Create a project / submit an outcome | `/api/projects` (operator-only, §7) |
| People / contacts | `amux crm` (on the server) or `/api/crm/contacts` |
| Documents / reference | `/api/memories` (`memory_type: reference`) |
| Recurring automation | `/api/schedules` |
| Message a session | `/api/workers/{id}/send` |
| Telegram in/out | `/api/telegram/status`, `/api/telegram/send` |
| Browser automation | `/api/browser/start` → `state` → `action` (send `X-Amux-Session`) |
| Everything else | see `references/long-tail.md`: email, Gmail, calendar, journal, files vs fs, org, groups, torrents, graph, map, SQL, dictation, TTS, habits, review, connectors, ollama — and confirm on `GET /api/debug/routes` first |

## 9. Remote hosts

- **The `amux` CLI does not send an Authorization header** (it assumes a
  localhost straight-through), so it 401s from any remote host. Use this
  skill's curl form remotely; on the amux server itself you may use
  `docker exec amux amux board ls` (localhost inside the container skips the
  token).
- `AMUX_AUTH_TOKEN` is read once at startup — changing it requires
  `docker compose restart`.
- Self-signed cert: curl needs `-sk`; a browser needs to accept the warning once.

## 10. Security

- Read the token only from the environment; never write it to a file, echo it,
  or commit it.
- Say what a write will do (create/delete a card, send a message, trigger a
  schedule) before executing it.
- Port 8824 is reachable on the LAN and the token is the only gate on data
  routes — never paste it into chat, logs, or code. The diagnostic routes (§6)
  answer **without** it, so do not expose 8824 past the LAN.

## Gotchas (environment facts — do not assume otherwise)

- **Token boundary** (measured 2026-09-30, no `Authorization` header):
  token-free = `/health`, `/`, `/api/debug/{routes,invariants,tmux,sse}`,
  `/api/health/invariants`, `/api/system-jobs`, `/manifest.json`,
  `/api/calendar.ics`; `401 missing_credential` = `/api/{board,projects,workers,
  schedules,memories,groups,sessions,logs/*}` and, by the same rule, every
  other `/api/*`. The older wording "only `/health` and `/`" was wrong — but
  keep probing liveness against `/health`, and never read a 401 as "the server
  is down".
- **The two 401s are different**: `missing_credential` = no token sent;
  `invalid_bearer` = wrong token — most often the server's `AMUX_AUTH_TOKEN`
  changed without a restart (it is read once at startup).
- **The `amux` CLI sends no Authorization header**, so any `amux ...` command on
  a remote host ends in a 401 traceback. That is a client limitation, not a
  dead server — use this skill's curl form.
- **A 409 on a status change is not a failure**: `gate not acknowledged` is the
  gate asking for confirmation, and the response's `cli` field is the retry
  command. If the type is wrong, fix the type first; never acknowledge criteria
  that did not happen.
- **`done` needs evidence**: `gate_ack` cannot move `done`; it needs
  `source_ref` (commit/URL/path/PR number). No artifact → `none: <reason>`.
- **Operator project writes reject `X-Amux-Worker`**: creating/configuring a
  project or calling `/projects/draft` with that header is a 403 (operator =
  no worker header + global scope) — the exact opposite of the "always attribute
  your writes" habit in §1.
- **Project intake is async**: `POST /api/projects/<name>/commands` returning
  202 only means the outcome was received; the server decomposes it into tasks
  afterwards. Not seeing tasks immediately is not a failure — poll
  `GET /api/projects/<name>`.
- **Docs may run ahead of the deployment, and `/health` cannot tell you**: on a
  404 (or a route the table does not list), read `GET /api/debug/routes` —
  use the §7 fingerprint, since prebuilt images report `commit: "unknown"`.
- **This skill's own directory can be replaced out from under you**: cloning
  over an existing checkout swaps the gitdir link and silently drops every
  uncommitted edit (cost 2026-09-29: a Gotcha, a §7 bullet and two EVOLUTION
  entries). Before cloning over it or replacing the directory: `git -C <dir>
  status --porcelain` empty **and** pushed.
- **Read `measured` before trusting a diagnostic number**: `total_errors: 0,
  measured: false` is an unrun probe.
- **Grep server logs with `-a`**: one NUL byte makes grep treat the file as
  binary and silently print no matches (while `grep -c` keeps counting).
