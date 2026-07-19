# Workflow Lessons (Compound Asset — CADL)

Reusable playbook distilled from the AIOps self-healing B2 batch + `opt/*` optimization
effort (2026-07-19). Apply on the next multi-skill / parallel-subagent batch.

## L1 — Relative link depth from `gcp-X-ops/references/advanced/`

A file at `gcp-X-ops/references/advanced/foo.md` needs **3 levels up** to reach the
repo-root `docs/` dir:

```
gcp-X-ops/references/advanced/  ->  ../../../docs/...
```

- `../../docs/...`  = wrong (lands in `gcp-X-ops/docs/`, which doesn't exist)
- `../../../docs/...` = correct

**Why it bites:** many pre-existing repo docs use the wrong `../../docs/` depth. The
`opt/deadlinks` commit fixed 89 such errors repo-wide (`140ff1a` family). When you
create new `references/advanced/` docs, use `../../../docs/` from the start.

## L2 — grep false-negatives: Chinese headings + bracketed links

Plain `grep` for a literal string missed real matches twice:

- Searching `详见 docs/cross-skill-blast-radius` returned 0, but the file actually says
  `详见 [docs/cross-skill-blast-radius.md]` (Markdown link with brackets). Grep the
  **bare filename** instead: `cross-skill-blast-radius`.
- Searching Chinese headings (触发条件 / 检测 / 自愈动作) missed docs that use the
  **English** heading (Trigger / Detection / Self-heal). Grep the English form too, or
  read the file directly.

**Rule:** when a grep returns 0 for something you expect to exist, re-grep with the
bracket-stripped token and/or the English synonym before concluding "doesn't exist".

## L3 — Stop-hook "Insufficient evidence" is a transcript-completeness gate

The stop hook fires when the transcript lacks per-critic PASS evidence, even if the work
is actually done. Fix by **re-verifying at the end of the goal** with real command
output (test counts, lint counts, link checks) rather than relying on agent PASS
messages that scrolled out of context. Post-goal evidence commands:

- tests: `python3 -m pytest gcp-gcl-runner-ops/tests/ -q -p no:cacheprovider`
- lint:   `npx markdownlint-cli2 "gcp-X-ops/**/*.md"`
- links:  `ls` the referenced files; grep bare filenames for pointers

## L4 — Test isolation / pollution looks like a code regression

A background full-suite run reported `1 failed` (`test_log_metrics::test_create_new_metric`,
`Exception: Not found` at `create_log_metrics.py:105`). On re-run in isolation and in the
module it **passed**. Root cause was a real but *already-fixed* regression:

- `opt/code-quality` narrowed a bare `except:` → `except NotFound:` in
  `create_log_metrics.py:106`.
- `be0c728` aligned the test mock (`side_effect = NotFound(...)`) to match.

**Rule:** before assuming a regression, (a) re-run the single test in isolation, (b)
re-run the containing module, (c) check `git log` for a recent except-narrowing /
refactor commit touching the file. The bare `Exception: Not found` text came from a
leaked mock in a *different* test, not from `create_log_metrics.py` (grep showed no
`raise NotFound` / `Exception("Not found")` in the source).

## L5 — Subagent turn-limit / stuck handling

A critic agent hit its max-turns (8) mid-audit and returned FAIL without a clean
verdict. Per GCL rules §11, when an agent is stuck/dead the **main Agent takes over**:
re-audit directly, fix, commit, and report the hash. Don't wait indefinitely — nudge
once, then take over.

## L6 — De-dup check for canonical/mainlined runbooks

A self-healing runbook inlined a 6-step auto-mute flow verbatim from a legacy anomaly
doc. Critic flagged it BLOCKER (TE-6 / §0.6 no-cross-file-dup). Fix: replace the
inlined block with a pointer to the canonical doc + runbook-specific notes
(GCL / idempotency / reversibility / blast-radius). **Rule:** when a `references/advanced/`
doc overlaps an existing legacy doc, point to it, don't copy it.

## L7 — Batch completion checklist (run before declaring done)

1. `git status` clean, `git log origin/main..HEAD` reviewed.
2. Full test suite green (`pytest` on the product dir that owns tests; this repo's
   tests live under `gcp-gcl-runner-ops/tests/`, not repo root).
3. `markdownlint-cli2` 0 issues on touched docs.
4. AIOps/acceptance criteria checkboxes updated with real numbers.
5. Remote push confirmed (`git rev-parse HEAD origin/main` equal).
6. All subagents shutdown (`shutdown_request` → `shutdown_response`), then `TeamDelete`.
