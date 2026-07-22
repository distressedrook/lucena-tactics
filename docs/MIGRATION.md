# Migration record: engine-slim → lucena-core → tactics consolidation

Working record for the 2026-07-23 restructure (plan: superrepo owner's decision log).
The end state: `lucena-engine` (public AGPL, PyPI) shrinks to a pure
Stockfish/Maia wrapper (`uci`, `maia`, `pool`, `evalmodel`, `nnue`); the Rust
board core is **removed** (python-chess becomes the single board substrate in
all private code; SEE reimplemented in python); a new private superrepo dir
`/lucena-core` (import `lucena_core`) takes the board-truth modules + the gRPC
client/server (absorbing `/common/engine_client`); the tactic set (detectors →
`census/`, facts, hints, line_tree, puzzle, brilliant) is **rewritten on
python-chess** in this repo; `analysis.py`/`gamepass.py` move to the backend.

## Phase tracker

| phase | what | status |
|---|---|---|
| 0 | freeze & baseline + differential harness | **done 2026-07-23** (freeze commits: tactics 6523864, backend 90164cf, superrepo 8d0b047; see self-check 439 cases 0 diffs) |
| 1 | python-chess SEE + compat Board in /lucena-core skeleton | **done 2026-07-23** — 60/60 ported contract tests (26 SEE + 34 board); differential vs Rust: 2,279 + 13,276 = **15,555 capture cases, 0 diffs** (seeds 7, 42) |
| 2 | board-truth modules → core; /common folds in | **done 2026-07-23** — 189/189 core tests (incl. ported test_detect 9, test_openings 28, test_positional 32, test_grpc_smoke 11); positional differential 1000 positions → 4 diffs, all pure ±1cp float-accumulation noise at exact .5 rounding boundaries (**adjudicated**: core canonicalizes summation order by square; the Rust-era result depended on piece_list iteration order, so the true value −13.5 rounded differently per substrate — no semantic drift, standings/thresholds unaffected). Constructor divergence adjudicated: python-chess OPPOSITE_CHECK relaxed for adjacent kings (a king can never give check — old-core convention, needed by detect.py paste inputs). engine_client copied from /common (consumer flip + /common deletion = Phase 3). evalmodel.MISTAKE made public in engine (additive freeze exception). |
| 3 | flip consumers (backend/tactics/plans/serve.sh); engine partial slim | **done 2026-07-23** — backend (board/_fen/detect/openings/positional/pgn/server → lucena_core; uci/evalmodel/maia + tactic modules stay lucena_engine), tactics (probes → lucena_core.engine_client; poisoned_line_detector → core reads/_fen/board), plans (fact_sheet hardcoded path killed; research → core; **left uncommitted** — mixed with pre-existing owner edits), serve.sh → lucena_core.server.serve, /common deleted. Backend suite 494+56 green (one transitional fix: test_import catches lucena_engine.pgn.PgnError until gamepass moves in P5). Engine slims nothing yet (tactic modules still consume board.py — per plan, final slim in P5). |
| 4 | census + facts + hints rewritten here; backend shims | **done 2026-07-23** — detectors/ → src/census/ + facts.py + hints.py (dual-context imports, drill.py pattern; census/_util sources the shared trio from lucena_core.reads). Ported tests: test_fork 7 + test_pin 5 + test_facts 62 + test_hints 11 = 90 green. Differential: static 1000 positions → **0 real diffs** (6 benign, two adjudicated ordering classes: fork witness-move under sorted scan, prong tie-order — both canonicalized new-side as functions of the position); engine-backed 60 positions with per-call new_game (the codebase's own reproducibility contract) → **0 diffs**. Backend shims grounding_tools/{facts,hints}.py; tools.py flipped. |
| 5 | line_tree/puzzle/brilliant; analysis+gamepass → backend; engine final slim | **done 2026-07-23** — line_tree/puzzle/brilliant → src/ (51+3 ported tests green; line_tree differential 12 positions fixed-nodes → **0 diffs**); analysis → backend grounding_tools/, gamepass → backend pipelines/ (surfacing test moved to backend/tests/test_gamepass_brilliant.py); backend shims line_tree/brilliant; core server/truth.py serves facts/hints/brilliant from this repo via server/_tactics.py bootstrap (deployment composition, not a package dep); test_openings split (table tests stay core-side, fact-sheet integration → tests/test_opening_fact.py). **Engine slimmed to the wrapper package**: uci+maia+pool+evalmodel+nnue, rust/+board+everything else deleted, de-maturined (pure setuptools), v0.2.0 — 87 passed 8 skipped. **PyPI publish deliberately left to the owner.** |
| 6 | has_tactics front door + _reconcile extraction | **done 2026-07-23** — src/_reconcile.py: the engine-agreement kernel (dangers/opportunities/forks passes + OPP_DROP_THRESHOLD) extracted behavior-verbatim from facts.py (test_facts 67 green as the harness). src/has_tactics.py: `(fen[, move], engine) → TacticVerdict(none|soft|tactic, swing_wp, entry_san, principal_line, motifs)` — census proposes, detect_combination's engine verdict decides "tactic", analyse gap prices uniqueness; a "tactic" fen flows to line_tree (contract #3). 7 engine-gated tests green. |
| 7 | cleanups (PoisonedLine RPC retirement, docs) | **done 2026-07-23** — proto moved engine→lucena-core/proto, PoisonedLine rpc+messages removed (no live callers, verified), stubs regenerated, `engine_client/_pb` duplicate consolidated into the package's one `_pb`; behaviour servicer stub dropped. Docs: superrepo CLAUDE.md (layer table + hygiene + in-process sections), this repo's CLAUDE.md architecture entry. Final sweep recorded below. |

## Baselines (Phase 0, recorded 2026-07-23)

Test suites (must be reproduced or beaten at every phase gate):

| suite | command | result |
|---|---|---|
| engine | `backend/.venv/bin/python -m pytest engine/tests/ -q` (stockfish on PATH) | **435 passed, 8 skipped** |
| backend | `PYTHONPATH=python .venv/bin/python -m pytest tests/ -q --ignore=tests/test_coaching_e2e.py --deselect tests/test_mcp.py::test_assess_move_tool_is_read_only_and_player_facing` | **495 passed, 8 skipped** |
| tactics | `.venv/bin/python -m pytest tests/ -q` | **78 passed, 1 skipped** |
| tactics rulings | `.venv/bin/python research/experiments/test_rulings.py` | **15/15 — ALL RULINGS HOLD** |

Known pre-existing failure (NOT a migration regression):
`backend/tests/test_mcp.py::test_assess_move_tool_is_read_only_and_player_facing`
fails on the clean tree (subprocess/stockfish-related) — deselected above.

Corpus numbers (the behavioral gates; re-run at phases 4, 5, 6, 7):

| claim | number | source |
|---|---|---|
| mistake-explanation completeness (held-out) | **86%** | 200 fresh Lichess puzzles, v2.1 classifier |
| mechanism label agreement | **87%** (lower bound; labels known-incomplete) | 299-puzzle corpus |

Repo state at baseline: substantial uncommitted work in `lucena-tactics`
(ray-geometry detectors 2026-07-22, drill walker move-in) and `backend`
(drill shim + `_tactics_path.py`, plus pre-existing local edits to
`freeform.py`/`handler_base.py`/`mode_prompts.py` not from this effort).
Committing that work is the first freeze action once the owner signs off.

## Differential gates

`research/experiments/differential.py` — the old-vs-new harness. Seeded,
deterministic corpus slice from `research/experiments/lichess_db_puzzle.csv`
(the FEN plus the position after the puzzle's setup move). Drivers accumulate
per phase:

| driver | old side | new side | gate phase |
|---|---|---|---|
| `see` | `lucena_engine.Board.see` (Rust) | `lucena_core.see` (python-chess) | 1 — must be **identical** on every legal capture |
| `positional` | `lucena_engine.positional` | `lucena_core.positional` | 2 — term values identical |
| `census` | `lucena_engine.detectors.*` | `src/census/*` | 4 — Fact sets identical (or every diff adjudicated) |
| `line_tree` | `lucena_engine.line_tree` | `src/line_tree` | 5 — trees identical under fixed nodes |

Run: `.venv/bin/python research/experiments/differential.py <driver> [--n 500] [--seed 7] [--self-check]`
(`--self-check` runs old-vs-old to prove the plumbing; must report 0 diffs.)

## Final record (Phase 7 close, 2026-07-23)

| suite | result |
|---|---|
| tactics + core (one venv) | **418 passed, 1 skipped** |
| rulings | **15/15 — ALL RULINGS HOLD** |
| engine (slimmed, v0.2.0) | **87 passed, 8 skipped** |
| backend | **496 passed, 8 skipped** (+1 pre-existing deselect; e2e gRPC 5/5 through lucena_core.server) |

Differential gates, cumulative: SEE 15,555 cases 0 diffs · positional 1000
positions 4 ±1cp boundary (adjudicated) · census/facts static 1000 positions
0 real diffs + engine-backed 60 positions 0 diffs · line_tree 12 positions
0 diffs. Late catch: the backend's vendored gRPC stubs collided with core's
regenerated ones in the protobuf descriptor pool after the PoisonedLine
removal — resolved by consolidating on core's stubs (backend engine_io
client imports lucena_core._pb; vendored _pb + proto deleted).

Corpus numbers (86% held-out / 87% mechanism agreement): NOT re-run — they
gate `factsheet.py`/`mechanism.py`, which this migration never touched (the
migrated modules are gated by the differential harness instead). Re-run at
the next change to those layers.

Post-close (2026-07-24): all repos pushed. lucena-tactics got its private
remote (distressedrook/lucena-tactics) after a history rewrite purged 1.9GB
of committed corpora (pack 381MB -> 283KB; KNOWN_ISSUES #8 records the one
casualty, corpus_labels.jsonl.gz — regenerable). Registered as a proper
submodule (.gitmodules). Still the owner's: the lucena-engine v0.2.0 tag +
PyPI publish, and lucena-plans' mixed uncommitted worktree.

## No-regression doctrine for the rewrites

1. Port the engine-side tests FIRST (they are the contract), then rewrite.
2. Differential harness must be clean (or every diff explained and adjudicated
   like a ruling) before the old implementation is deleted.
3. Engine originals are FROZEN (no edits) while both copies exist (phases 1–5).
4. Corpus numbers (86%/87%) are the final arbiter — suites can pass while
   behavior drifts; the corpus can't.
