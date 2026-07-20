# chess-lab — grounded chess-mistake explanations

**Thesis:** a Stockfish PV is a conclusion with the proof deleted. The *why* is
reconstructed by re-querying the engine with counterfactuals — never parsed
from the line, never inferred by an LLM. Every claim carries a machine-checkable
witness; every mechanism name is a geometric theorem confirmed by an engine
counterfactual and ratified by a human adjudicator.

## Product

`POST /why {fen, solution, played}` → grounded coaching explanation.

    uvicorn explainer.server:app --port 8000
    python -m explainer.cli <fen> <solution_san> <played_san>

Requires a running lucena-engine gRPC server (`LUCENA_ADDR`, default
127.0.0.1:50052) and optionally `GEMINI_API_KEY` + `EXPLAINER_GEMINI_MODEL`
for LLM prose (verified; template fallback always available and always true).

## Architecture

    probes.py      engine truth (fixed-node gRPC; deterministic)
    predicates.py  ply-level geometric predicates (python-chess; total functions)
    mechanism.py   mechanism naming: geometric theorems + engine counterfactuals
                   + 15 adjudicated rulings (see experiments/test_rulings.py)
    factsheet.py   two-axis fact sheet (forfeit x error), every slot witnessed
    lexicalize.py  LLM as constrained lexicalizer: SAN + mechanism-vocabulary
                   verification, coverage requirement, candidate redaction,
                   deterministic template floor
    server.py      FastAPI endpoint

## Validation

- Mistake classification: 86% completeness on held-out 200 Lichess puzzles
- Mechanism naming: 87% label agreement, 9 mechanisms graduated, 55-case
  adjudication complete (experiments/adjudication_verdicts.json)
- Regression suite: experiments/test_rulings.py — 15 human rulings, two tiers

## Doctrine (the short version)

Presence is geometry; the point is causality. Opportunity requires the freedom
to decline. Cause outranks execution. An unsound proof is worse than silence.
