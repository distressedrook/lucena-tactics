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
| 0 | freeze & baseline + differential harness | **in progress (2026-07-23)** |
| 1 | python-chess SEE + compat Board in /lucena-core skeleton | pending |
| 2 | board-truth modules → core; /common folds in | pending |
| 3 | flip consumers (backend/tactics/plans/serve.sh); engine partial slim | pending |
| 4 | census + facts + hints rewritten here; backend shims | pending |
| 5 | line_tree/puzzle/brilliant; analysis+gamepass → backend; engine final slim + publish | pending |
| 6 | has_tactics front door + _reconcile extraction | pending |
| 7 | cleanups (PoisonedLine RPC retirement, docs) | pending |

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

## No-regression doctrine for the rewrites

1. Port the engine-side tests FIRST (they are the contract), then rewrite.
2. Differential harness must be clean (or every diff explained and adjudicated
   like a ruling) before the old implementation is deleted.
3. Engine originals are FROZEN (no edits) while both copies exist (phases 1–5).
4. Corpus numbers (86%/87%) are the final arbiter — suites can pass while
   behavior drifts; the corpus can't.
