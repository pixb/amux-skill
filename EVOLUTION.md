# Evolution log

Appended automatically by scripts/run_evals.py (and scripts/evolve.py) when a check fails. Each entry is the raw evidence for a fix/regenerate step.

## 2026-09-29T11:10:32Z — skill created

Initial evidence for the portable `amux` skill (English, repo-independent):

- gates: `validate.py` valid (1 warning: name `amux` does not end in `-skill`,
  kept deliberately so the `/amux` command and the skill directory share one
  name); `security_scan.py` clean; `skill_graph.py run` all four gates pass.
- evals: `run_evals.py --validate` valid; `--rollout --promote` scored
  20/20 against the live server (GET-only probe, no token required) and
  promoted `board-status` and `diagnostics`; `remote-401` is the holdout.
- the probe (`scripts/run_pipeline.py`) reports an unreachable server inside
  the report instead of raising, so the same command works on hosts with no
  amux running; the criteria decide whether that is a failure.

Anything this loop could not catch — a route that moved on the server, a
response shape that drifted, a rule a later editor broke — should arrive here
as a `## <timestamp> — run_evals ... FAILED` entry with its raw failing checks.
## 2026-09-29T11:11:08Z — staleness_check FRESH

- days_since_review: 0 (source: last_reviewed)
- raw findings:

```json
[
  {
    "level": "error",
    "message": "Dependency 'amux HTTP API' is unreachable",
    "detail": "Failed to connect to https://localhost:8824: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1082)"
  },
  {
    "level": "error",
    "message": "Cannot reach https://localhost:8824/health for schema check",
    "detail": "Error: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1082)"
  }
]
```

## 2026-09-29T11:14:02Z — staleness_check degraded (resolved)

- counts: staleness exit 2; dependency and schema probes failed while
  `GET /health` answered 200 in the browser and in the skill's own probe.
- raw evidence (as recorded by the run above): `[SSL: CERTIFICATE_VERIFY_FAILED]
  certificate verify failed: self-signed certificate` for both
  `https://localhost:8824` and `https://localhost:8824/health`.
- root cause: the platform's health/drift checkers verify TLS strictly, while
  this deployment serves a self-signed certificate by design (SKILL.md §0 and
  §9 tell every curl call to use `-sk`). The endpoint was healthy; the checker
  could not trust it.
- fix: `metadata.dependencies` and `metadata.schema_expectations` now carry
  `tls_verify: false` for the amux service, and the skill's copies of
  `scripts/dependency_health.py` and `scripts/schema_drift.py` honour that flag
  for that one URL only (default stays full CA verification). Same opt-out the
  skill's own probe already documents.
- re-check: `python3 scripts/staleness_check.py . --check-deps --check-drift`
  → fresh, dependency healthy (HTTP 200), schema matches; then
  `python3 scripts/evolve.py` → all checks fresh and green.
## 2026-09-29T11:33:05Z — layout deviation: root reference.md → references/long-tail.md

- reported as: "reference.md is a file, is a references/ directory compliant?"
- root cause: `architecture-guide` §2.1 puts detail under `references/` and
  `skill_graph` types that directory as `reference`, but the real problem was
  invisible — validate's "say Read `references/x.md` for ..." rule matches only
  `references/[\w./-]+\.md`, so a root `reference.md` was never seen. The check
  reported clean by matching nothing, not by passing.
- fix: moved the file to `references/long-tail.md`, rewrote the SKILL.md/AGENTS/
  README/discovery pointers as read-directives, and added eval criterion
  `reference-layout` so the path can only regress deliberately.
- evidence: `validate._find_unlabeled_mentions` on the new body finds 4
  mentions, 0 unlabeled; graph artifact type is now `reference`; gates
  spec/security/pipeline/eval_schema PASS; evals 22/22 in both default and
  rollout; `evolve.py` fresh and green; VERIFICATION.md regenerated clean.

## 2026-09-29T11:51:16Z — rename: `amux` → `amux-skill` (dir + `name` field)

- trigger: validate's last remaining warning was the name convention the
  standard asks for (`<name>-skill`), and `validate.py:296-300` hard-errors
  when the directory name and the frontmatter `name` disagree — so the
  directory has to move with the field, not the other way around.
- change: `skills/amux/` → `skills/amux-skill/`; `name: amux` → `amux-skill`;
  `.claude-plugin/{plugin,marketplace}.json` name; README/AGENTS headings;
  `.opencode/command/amux.md` skill pointer. The opencode command file stays
  `/amux` (documented entry point), only the skill name moved.
- second-order finding: `marketplace_discovery._examples` (line 80) rejects
  any example whose invocation does not start with `/{name}`. The four
  discovery examples therefore moved from `/amux …` to `/amux-skill …` —
  that is the *skill invocation* form the contract models; the short
  `/amux` command remains a separate opencode shortcut and both still name
  the same skill. First rewrite produced `/amux-skillx …` (off-by-one slice);
  caught by reading the printed examples, re-sliced, collapsed to single spaces.
- installers: re-rendered from the official `render_installers.py` with
  `SKILL_NAME="amux-skill"` (the `-skill` suffix is exactly the regex the
  renderer requires, so this is the first clean render — no hand edits).
- regression lock: new eval criterion `spec-name`
  (`grep -qE '^name: [a-z0-9]+(-[a-z0-9]+)*-skill$' SKILL.md`) makes the
  convention a hard local check instead of a platform warning.
- evidence: validate VALID, **0 warnings**; security CLEAN; skill graph
  spec/security/pipeline/eval_schema PASS; `run_evals` 24 passed / 0 failed
  (default, `--validate`, and `--rollout`; holdout `remote-401` still held
  out); `evolve.py` all checks fresh and green; VERIFICATION.md regenerated
  `clean: true` (fingerprint `67c4f4651fc8b550abeb08a8a7618049dc4d9294653d0fc5afcd3fcbc7669cf8`);
  install.sh `--dry-run` resolves target dir `amux-skill`; CJK sweep 0 hits.
