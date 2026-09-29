# amux-skill

Operate the **amux** agent-orchestration service — kanban board, projects,
workers, schedules, memory, diagnostics — from any agent session over its HTTP
API. Every interaction is HTTPS JSON with a Bearer token; there is no MCP
server and none should be invented.

- `SKILL.md` — core families: call templates, board and gates, workers,
  memory, schedules, diagnostics, projects, routing table, remote hosts.
- `references/long-tail.md` — the long-tail families (email, Gmail, calendar,
  Telegram, browser, CRM, journal, files/fs, org, groups, torrents, graph, map,
  SQL, dictation, TTS, habits, review, connectors), one verified example per route.
- `AGENTS.md` — cross-tool companion (activation triggers, Gotchas).
- `evals/` + `scripts/` — the skill's own regression gate; see below.

## Installation

### 1. Environment

```bash
export AMUX_URL=https://<amux-host>:8824     # LAN host running the amux server
export AMUX_AUTH_TOKEN=<api token>           # every /api/* route needs it
```

`AMUX_AUTH_TOKEN` must match the token the server was started with; a token
change on the server requires a server restart to take effect. `GET /health`
and `GET /` are the only token-free routes, which is what the probe below uses.

### 2. Network

The deployment serves a self-signed certificate, so every call needs `curl -sk`
(disable verification) rather than a CA-signed endpoint. Port 8824 is the
server; if a request hangs or times out, check reachability first:

```bash
curl -sk "$AMUX_URL/health"
```

### 3. Install the skill

From this directory:

```bash
./install.sh                 # copies to every detected tool's skill directory
./install.sh --platform opencode --project   # one tool, project-local
./install.sh --dry-run       # show what it would copy
```

### 4. Install the `/amux` command

The command is a sibling of this skill in the source checkout
(`.opencode/command/amux.md`); copy it next to the skill:

```bash
# opencode
mkdir -p ~/.config/opencode/command
cp ../../command/amux.md ~/.config/opencode/command/amux.md

# claude code
mkdir -p ~/.claude/commands
cp ../../command/amux.md ~/.claude/commands/amux.md
```

On a host that received only this skill directory, copy `amux.md` from the
checkout it came from — the command is not part of the skill package.

## Examples

```
You: "add a card: fix the login error copy"

Agent: POST $AMUX_URL/api/board {"title":"fix the login error copy","type":"code"}
       → AMUX-1043, status backlog
```

```
You: "move AMUX-1042 to done"

Agent: POST $AMUX_URL/api/board/AMUX-1042 {"status":"done"}
       → 409 gate_blocked … the gate wants source_ref first
       → POST ... {"status":"done","source_ref":"<commit sha>"}  # no artifact? "none: <reason>"
```

```
You: "create project importer and submit the first outcome"

Agent: PUT $AMUX_URL/api/projects/importer   (NO X-Amux-Worker header — operator route, 403 with it)
       POST $AMUX_URL/api/projects/importer/commands  → 202, tasks appear async
```

## Troubleshooting

### 401 `missing_credential`

No token reached the server. Check the header is present and the variable is
exported in the shell that runs curl: `curl -sk -H "Authorization: Bearer
$AMUX_AUTH_TOKEN" "$AMUX_URL/api/board"`. The `amux` CLI does not send this
header, so CLI calls from another host always 401 — use the curl form.

### 401 `invalid_bearer`

A token was sent but does not match. The server reads its token once at
startup, so a rotated token in your environment is stale until the server
restarts.

### 403 `operator setting`

`PUT /api/projects/<name>` and `POST /api/projects/draft` reject any request
carrying `X-Amux-Worker`. Omit the header on those two routes.

### 404 on a route that looks right

Do not guess: `GET /api/debug/routes` is the live route table and wins over
any written documentation.

### 409 `gate_blocked`

Not a failure. Read the response's `cli`/`gate_ack` and satisfy the gate;
`done` additionally requires `source_ref`.

## Verification

Gate and eval evidence is recorded in [VERIFICATION.md](VERIFICATION.md).
Regenerate it from the skill root after a material change:

```bash
python3 ~/.config/opencode/skills/agent-skills-platform/scripts/generate_verification.py . \
  --run-kind live --environment opencode
```

The rollout performs read-only GETs against `$AMUX_URL`. Use `--no-rollout`
when no amux server is reachable and only static checks are appropriate.

Other checks, all from the skill root:

```bash
python3 scripts/run_evals.py --validate     # eval spec is well-formed
python3 scripts/run_evals.py                # static + baseline checks (20 checks)
python3 scripts/run_evals.py --rollout      # live probe, score the produced report
python3 scripts/evolve.py                   # staleness + deps + drift + rollout
python3 scripts/staleness_check.py . --check-deps --check-drift
```

The normalized graph IR is rebuilt on demand and is deliberately not shipped —
it embeds this machine's absolute contract path:

```bash
python3 ~/.config/opencode/skills/agent-skills-platform/scripts/skill_graph.py \
  build . --output skill.graph.json     # then: skill_graph.py run . --jobs 4
```
