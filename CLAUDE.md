# lucena-tactics — grounded tactical-mistake explanations

**What this project is:** explain WHY a played move loses and WHY the
solution wins, every claim traceable to an engine counterfactual or a total
geometric predicate, never parsed from a PV and never inferred by an LLM. This
is the **tactical** sibling of `lucena-plans` (positional pedagogy — plans in
quiet positions); it shares the method (theorem-first, human-adjudicated,
corpus-validated) but none of its runtime. Formerly `chess-lab`; renamed and
moved into the Lucena superrepo 2026-07-22.

**Layout (2026-07-22 restructure):** `src/` (the library — a proper Python
package, `explainer/` renamed in place, internal relative imports unchanged),
`docs/` (`KNOWN_ISSUES.md`), `research/` (`experiments/`: the labeling
pipeline, adjudication records, corpus data). File names below are module
names inside `src/`.

## The thesis

A Stockfish PV is a **conclusion with the proof deleted**. The engine computes
the why — the tree of refuted alternatives — then discards it. So the why is
never *parsed* from the line and never *inferred* by an LLM; it is
**reconstructed by re-querying the engine with counterfactuals**, expressed as
witnessed predicates, and only then lexicalized into prose.

Core principles, each validated the hard way on day one:

- **Explanation is contrastive.** The explanandum is (line, foil), never the
  line alone. For puzzles the foil is given — the user's failed move.
- **Tactical why = the difference between branches. Positional why = the
  invariant across branches.** (The positional half became `lucena-plans`.)
- **Presence is geometry; the point is causality.** A fork that exists but
  isn't *used* is trivia. Every mechanism claim needs a counterfactual.
- **An unsound proof is worse than silence.**
- **The LLM is a lexicalizer, never an analyst.** Every sentence must trace to
  a witnessed slot; violations are detected mechanically and rejected.
- **Human adjudication supplies definitions, not labels.** One ruling on one
  case compiles into a rule that re-adjudicates the whole corpus.

## What is built

### The product pipeline (`src/`)

`POST /why {fen, solution, played}` → grounded coaching explanation.

| module | role |
|---|---|
| `probes.py` | engine truth — fixed-node gRPC to lucena-engine's Truth service (deterministic). Re-exports the shared client from `/common/engine_client` (2026-07-22 — see below). |
| `predicates.py` | ply-level geometric predicates (total functions, python-chess) |
| `mechanism.py` | mechanism naming: geometric theorems + engine counterfactuals |
| `factsheet.py` | two-axis fact sheet (forfeit × error), every slot witnessed |
| `takeaways.py` | curated habit table — hand-written pedagogy, deterministic |
| `lexicalize.py` | Gemini as constrained lexicalizer + verifier + template floor |
| `server.py` / `cli.py` | FastAPI endpoint / CLI |
| `poisoned_line_detector.py` | human-trap detection (rating-weighted Maia policy × Stockfish refutation). Moved in from `lucena-engine` 2026-07-22 — see below. |

### The fact sheet (two axes + trimmings)

- **forfeit** (what the solution won): `mate_in_N`, `forced_mate`,
  `winning_attack`, `wins_<piece>` (NET accounting — trades don't count as
  wins), `promotion`, `decisive_threat`, `advantage` (margin-scaled language)
- **error** (what the played move did wrong): `hung`, `bad_trade` (initiated
  exchange ≠ hanging), `wrong_piece`, `move_order`, `allowed_forcing_reply`,
  `none` (pure omission — no scolding)
- plus `refutation`, `delta`, `salvage` (3-state), `mechanism`, `takeaway`

### Mechanism vocabulary (11 graduated + 2 candidate/conditional)

| mechanism | status | basis |
|---|---|---|
| mating_net | **graduated** | escape accounting (king-lifted rays); 66/66 labels |
| back_rank / smothered | **graduated** | geometry-gated classical names |
| fork | **graduated** | 98% + engine counterfactual (no defense saves both prongs); bought-off resolution |
| hanging_piece | **graduated** (confirm tier) | perishability: not compelled, not doomed |
| deflection | **graduated** | 86% + forced-reply gate; two human ratifications |
| defender_removal | **graduated** | three human ratifications after rulings #12/#13/#15 |
| attraction | **graduated** (confirm tier only) | differential compulsion + bait boundary |
| mate_threat | **graduated** (confirm tier) | ransom reclassification, carries refutations |
| overload | conditional | conscription (rule-forced reply) or second-duty view — see `docs/KNOWN_ISSUES.md` #4 |
| intermezzo | candidate | two-pending ordering shape (0JDnk); 9 fired, needs adjudication — `docs/KNOWN_ISSUES.md` #3 |
| file_battery | candidate | new vocabulary from ruling #14; needs a real detector — `docs/KNOWN_ISSUES.md` #3 |

### The verifier contract (LLM hardening)

1. No fabricated moves — SAN tokens must trace to witnesses (recursive)
2. No fabricated mechanisms — doctrine-word blocklist
3. No omitted mechanisms — graduated mechanism must be spoken (coverage)
4. No unratified claims — candidates are redacted from the LLM's input
5. Floor = deterministic template, always true

Stress-tested against Sonnet (fabricated "overload"/"clean piece up" —
caught) and gemini-flash-lite (omitted the mechanism — caught). Config:
`GEMINI_API_KEY`, `EXPLAINER_GEMINI_MODEL` (currently flash-lite).

## Validation (all measured, all reproducible)

| claim | number | where |
|---|---|---|
| Mistake-explanation completeness | **86% held-out** (== train; no overfit) | 200 fresh Lichess puzzles, v2.1 classifier |
| Maia foil coverage | 400/400 | both runs |
| Mechanism coverage | 53% of puzzles get a named point | 299-puzzle corpus |
| Mechanism label agreement | **87%** (labels known-incomplete → lower bound) | same corpus |
| Adjudication | **55 cases → 0 pending** | `research/experiments/adjudication_verdicts.json` |
| Regression suite | 15 rulings, two tiers, all green | `research/experiments/test_rulings.py` |

Failure boundary is *mapped*: tactical puzzles ~95%+, endgame technique ~0%
(pawn races, king walks — the positional layer's job; see
`docs/KNOWN_ISSUES.md` #2).

## The 15 adjudicated rulings (the doctrine)

1. A free-choice reply was not lured (forced-reply gate; scan stops at unforced replies)
2. Mechanisms **compose** — primary + also-views; arrival exploited → attraction primary
3. A hanging piece is not a defender (defense must cost something to remove)
4. A bought-off fork is still the fork; **cause outranks execution**
5. Consequence-forced (all alternatives lose) is real compulsion; the refutation goes in the prose
6. Rule-forced reply = **conscription**, not luring → overload primary
7. **Differential compulsion**: a recapture among equals is a defensive try, not a lure
8. Compulsion from a mate threat = **ransom** → mate_threat primary
9. **Bait boundary**: bait taken → attraction stands; no bait → ransom
10. A free pawn is not a "hanging piece"
11. Hanging = **perishable** opportunity: not compelled, not doomed (would it escape?)
12. Defender-removal requires the **last** defender — an unsound proof is worse than silence
13. Cheap defender removed for a bigger target = removal, even when the defender was free
14. A same-square liquidation backed by a root **battery** is the battery's work
15. Removal targets the **most valuable ward**; if it escapes, the threat was bought off

Meta-lesson: every ruling was a *definition*, not a label — agency, bait,
differential, urgency, soundness. ~90 minutes of adjudication moved mechanism
agreement from 38% → 87% and queue 55 → 0.

## Supporting results from the founding session

- **Positional pipeline (designed + prototyped):** term-trajectory extractor
  over the Carlsbad corpus works; v1 needed quiescence filtering + drift (not
  event) segmentation. This whole track became `lucena-plans` the next day
  (2026-07-21 split) — see that repo's own `CLAUDE.md` for everything after.
- **plan_foil analysis** (why a *plan* fails): duty-retention enumeration
  demonstrated on 0L0Sw (`f5 Ng3!` — one square does both jobs). Verdict:
  reliable only for *stated* intent; automatic intent attribution is
  unverifiable — build interactive, not automatic (`docs/KNOWN_ISSUES.md` #6).
- **LLM-provider decision:** Gemini (user's key). Model is deliberately the
  least-trusted, most-replaceable component.

## The three-tagged-games experiment (the founding result, shared with lucena-plans)

Three annotated study games (Lilienthal, Tal, Benko — minority attack, spans
marked by the annotator) produced the positional track's first major finding,
right before it split off:

**The minority attack's CREATION phase is invisible to static term drift.**
Across all three annotated spans, no eval term moves consistently (pawns
+8/+9cp — the backward c-pawn's value is future pressure, not present
centipawns). What v1's drift detection finds is the EXPLOITATION phase
(Benko: activity +181, pawns +136 after the weakness was fixed). The sowing is
silent; the harvest drifts.

**The invariant is the CHOREOGRAPHY**: minority-side pawn traffic (b2-b4-b5,
a4 support) and the b5/c6 lever. Plans that restructure are observable in the
moves; plans that accumulate are observable in the terms.

**Consequence delivered immediately**: `detect_minority_attack()` — a
choreography theorem, mechanism-style — found **53 minority attacks in 28,461
elite games** on first run, the first named, corpus-validated plan in the
system, and the seed of everything `lucena-plans` became.

## 2026-07-22: extraction and restructure

Two things moved OUT of this repo's orbit and one thing moved IN, all the
same day:

- **`/common/engine_client`** — the `Probes` gRPC client + generated
  protobuf stubs, previously vendored here (`gen/lucena/engine/v1/`) AND
  independently re-vendored/cross-imported by `lucena-plans`' research
  harness via a `sys.path` hack straight into this repo's source tree (which
  broke outright when this repo was renamed from `chess-lab`). Extracted to
  the superrepo's `/common` — genuinely shared code gets ONE copy, not a
  cross-repo path hack. `src/probes.py` is now a thin re-export.
- **`docs/KNOWN_ISSUES.md` + this file** replace `PROGRESS.md` — same
  content, reorganized to match `lucena-plans`' documentation convention
  (a lab-notebook `CLAUDE.md` + a caveats-only `KNOWN_ISSUES.md`), so both
  sibling repos read the same way.
- **`poisoned_line_detector.py`** moved IN from `lucena-engine` (the
  human-trap detector: rating-weighted Maia policy × Stockfish refutation,
  node-limited/deterministic search). `lucena-engine` is being kept as thin,
  license-neutral infrastructure (board core + UCI/gRPC transport); anything
  that's genuinely differentiated coaching logic belongs in a private repo —
  this detector is squarely that, and belongs beside the rest of the tactical
  vocabulary it complements (a trap is just a mechanism the OPPONENT is
  hoping you walk into). Imports rewritten from `lucena_engine`'s internal
  relative imports (`.reads`, `._fen`, `.board`, `.evalmodel`) to the normal
  external form (`lucena_engine.reads`, etc.) — this repo now depends on
  `lucena-engine` as an ordinary pip package, the same relationship
  `lucena-backend` already has.

## Infrastructure notes

- Engine: lucena-engine gRPC, `LUCENA_ADDR` (default `127.0.0.1:50052`).
  See `docs/KNOWN_ISSUES.md` #1 for the unsupervised-server gap.
- Maia: wired via `LUCENA_MAIA`.
- Determinism: fixed nodes everywhere (`EXPLAINER_NODES=2M`, forfeit probe 4M).
- Data: `research/experiments/*.jsonl` are the validated corpus runs (train +
  held-out); adjudication record in `adjudication_verdicts.json`.

## Relation to lucena-plans

- `lucena-plans` = positional pedagogy (plans in quiet positions). This repo
  = tactical mistake explanation (why a forcing line wins/loses). Shared
  philosophy (theorem-first, human-adjudicated, corpus-validated,
  counterfactual-verified) and now shared plumbing (`/common/engine_client`);
  independent detector vocabulary and independent data.
- Both repos' research harnesses run under THIS repo's venv (`.venv/`) for
  gRPC/protobuf — see `lucena-plans/research/experiments/tools/rolls.py` and
  neighboring scripts, which reach `.venv/bin/python` here by the same
  sibling-path convention as `/common`.
