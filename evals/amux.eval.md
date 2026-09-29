# Eval Spec: amux

Two layers of checks, both deterministic. The static layer asserts that the
skill's own prose still carries the facts an operator cannot afford to lose
(English-only text, no repo-specific references, the operator-only project
routes, the done-evidence rule, `measured` before a diagnostic number). The
report layer scores what `scripts/run_pipeline.py` observed against the live
server: reachable, `/health` status ok, and which Bearer branch was taken.

The probe is GET-only, so a rollout never mutates the amux server. Golden
baselines are the promoted probe reports; `compare: "none"` keeps volatile
fields (build, commit, `checked_at`) out of the regression gate while the
criteria above still pin the stable ones.

Run every command from the skill root — the static criteria read `SKILL.md`
relative to the current directory.

```json
{
  "skill": "amux",
  "run": "python3 scripts/run_pipeline.py --input {input} --output {output}",
  "criteria": [
    {"id": "english-only", "text": "Skill prose stays English (no CJK drift)", "type": "command", "cmd": "! grep -rP '[\\x{4e00}-\\x{9fff}]' SKILL.md references AGENTS.md README.md discovery.json evals"},
    {"id": "no-repo-leak", "text": "No repo-specific references in the portable skill", "type": "command", "cmd": "! grep -rqE 'amux-worker\\.sh|AF-321|server\\.env|nec8-docker|\\.claude/commands' SKILL.md references AGENTS.md discovery.json"},
    {"id": "reference-layout", "text": "Long-tail detail sits in references/ and SKILL.md points at it", "type": "command", "cmd": "test -f references/long-tail.md && grep -q 'references/long-tail.md' SKILL.md"},
    {"id": "spec-name", "text": "name field carries the -skill suffix the standard asks for", "type": "command", "cmd": "grep -qE '^name: [a-z0-9]+(-[a-z0-9]+)*-skill$' SKILL.md"},
    {"id": "operator-rule", "text": "Documents that X-Amux-Worker on project routes is 403", "type": "command", "cmd": "grep -q 'X-Amux-Worker' SKILL.md && grep -q '403 operator' SKILL.md"},
    {"id": "projects-family", "text": "Documents the projects create and intake routes", "type": "command", "cmd": "grep -q 'expect_rev' SKILL.md && grep -q '/api/projects/<name>/commands' SKILL.md"},
    {"id": "done-evidence", "text": "Documents that done requires source_ref, none: reason when there is no artifact", "type": "command", "cmd": "grep -q 'source_ref' SKILL.md && grep -q 'none:' SKILL.md"},
    {"id": "measured-first", "text": "Reads measured and n_considered before trusting a diagnostic number", "type": "command", "cmd": "grep -q 'measured' SKILL.md && grep -q 'n_considered' SKILL.md"},
    {"id": "diagnostics-routes", "text": "Names the live route table and the SSE diagnostic", "type": "command", "cmd": "grep -q '/api/debug/routes' SKILL.md && grep -q '/api/debug/sse' SKILL.md"},
    {"id": "server-reachable", "text": "Probe reached the amux server", "type": "command", "cmd": "grep -q '\"reachable\": true' {output}"},
    {"id": "health-ok", "text": "GET /health reports status ok", "type": "command", "cmd": "grep -q '\"health_status\": \"ok\"' {output}"},
    {"id": "auth-branch", "text": "Report records the Bearer branch taken (ok, or skipped without a token)", "type": "command", "cmd": "grep -qE '\"board_auth\": \"(ok|skipped)\"' {output}"}
  ],
  "golden": [
    {"id": "board-status", "input": "golden/board-status/input.txt", "expected": null, "split": "val", "expected_status": "pending-first-green", "compare": "none"},
    {"id": "diagnostics", "input": "golden/diagnostics/input.txt", "expected": null, "split": "val", "expected_status": "pending-first-green", "compare": "none"},
    {"id": "remote-401", "input": "golden/remote-401/input.txt", "expected": null, "split": "test", "expected_status": "pending-first-green", "compare": "none"}
  ]
}
```
