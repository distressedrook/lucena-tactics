# lucena-tactics — grounded tactical-mistake explanations

**Thesis:** a Stockfish PV is a conclusion with the proof deleted. The *why* is
reconstructed by re-querying the engine with counterfactuals — never parsed
from the line, never inferred by an LLM. Every claim carries a machine-checkable
witness; every mechanism name is a geometric theorem confirmed by an engine
counterfactual and ratified by a human adjudicator.

Private and proprietary. The tactical sibling of `lucena-plans` (positional
pedagogy for quiet positions) — same method, independent runtime. Formerly
`chess-lab`.

## Product

`POST /why {fen, solution, played}` → grounded coaching explanation.

    uvicorn src.server:app --port 8000
    python -m src.cli <fen> <solution_san> <played_san>

Requires a running lucena-engine gRPC server (`LUCENA_ADDR`, default
127.0.0.1:50052) and optionally `GEMINI_API_KEY` + `EXPLAINER_GEMINI_MODEL`
for LLM prose (verified; template fallback always available and always true).

## Layout

```
src/                     THE LIBRARY (a Python package; internal imports
                         are package-relative, unaffected by this rename)
  probes.py                engine truth (fixed-node gRPC; deterministic) —
                           re-exports the shared client, see below
  predicates.py             ply-level geometric predicates (python-chess;
                           total functions)
  mechanism.py              mechanism naming: geometric theorems + engine
                           counterfactuals + 15 adjudicated rulings (see
                           research/experiments/test_rulings.py)
  factsheet.py              two-axis fact sheet (forfeit x error), every
                           slot witnessed
  lexicalize.py             LLM as constrained lexicalizer: SAN +
                           mechanism-vocabulary verification, coverage
                           requirement, candidate redaction, deterministic
                           template floor
  poisoned_line_detector.py human-trap detection (rating-weighted Maia
                           policy x Stockfish refutation); moved in from
                           lucena-engine 2026-07-22
  server.py / cli.py        FastAPI endpoint / CLI

docs/                    KNOWN_ISSUES.md (open, understood, not yet fixed)

research/                RESEARCH HARNESS (never shipped)
  experiments/              the labeling pipeline, adjudication records,
                           corpus data, regression suite
```

`/common/engine_client` (in the superrepo, sibling to this repo) holds the
shared gRPC client (`Probes`) + generated protobuf stubs — extracted
2026-07-22 because `lucena-plans`' research harness depended on the same
client via a path hack into this repo, which broke when this repo moved.
`src/probes.py` is a thin re-export; nothing else in this repo changes.

## Validation

- Mistake classification: 86% completeness on held-out 200 Lichess puzzles
- Mechanism naming: 87% label agreement, 11 mechanisms graduated, 55-case
  adjudication complete (`research/experiments/adjudication_verdicts.json`)
- Regression suite: `research/experiments/test_rulings.py` — 15 human
  rulings, two tiers

## Doctrine (the short version)

Presence is geometry; the point is causality. Opportunity requires the freedom
to decline. Cause outranks execution. An unsound proof is worse than silence.

## Docs

- `CLAUDE.md` — the lab notebook: the thesis, what's built, every finding and
  adjudicated ruling, with provenance. Read it before touching the mechanism
  vocabulary.
- `docs/KNOWN_ISSUES.md` — current caveats and gaps.
