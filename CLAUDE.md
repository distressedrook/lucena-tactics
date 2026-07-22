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

### Mechanism vocabulary (11 graduated + 7 candidate/conditional)

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
| pin | candidate | two shapes: paralyzed defender (illegal recapture — total geometry) + win-the-pinned-piece; 0 adjudications — `docs/KNOWN_ISSUES.md` #7 |
| skewer | candidate | front outranks rear on a ray, compelled to step off, line collects the rear |
| discovered_attack | candidate | mover unmasks a slider + poses a second threat; line collects one of the two |
| trapped_piece | candidate | every legal move of the victim loses it (witnessed per-square); names the doomed case ruling #11 rejects as "hanging" |
| battery | candidate | generalizes ruling #14 to window-start: front captures, rear wins the exchange |

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

## 2026-07-22 (later): the ray-geometry vocabulary lands (candidate tier)

The gap between the verifier's word-blocklist and the detector vocabulary is
closed: pin, skewer, x-ray/battery, discovered attack, and trapped piece were
named in `lexicalize._MECHANISM_WORDS` as fabrications to catch, but nothing
could ever *earn* those words. Five detectors added to `src/mechanism.py`
(`detect_pin`, `detect_skewer`, `detect_discovered_attack`,
`detect_trapped_piece`, `detect_battery`), all following the house theorems:

- **Total geometry over (fen, line)** — no probes, no LLM. The contract for
  this layer is `(fen, pv)`: the single top engine line, start to end. No
  rolls, no diffing of alternatives — that's `lucena-plans`' problem shape,
  not this one.
- **Presence is geometry; the point is the collection.** Every detector
  requires the line itself to USE the geometry: the skewered rear must be
  taken, the pinned piece collected with the pin still standing, the trapped
  piece hunted down square-by-square, the battery's rear piece must actually
  recapture. A shape that exists but is never cashed is trivia and stays silent.
- **Pin has two shapes** — `paralyzed_defender` (our capture's defenders have
  NO legal recapture and at least one is absolutely pinned: python-chess
  legality makes this a total fact; relative pins deliberately excluded here
  because an ill-advised recapture is an engine question) and `win_pinned`
  (absolute or relative pin + the line collects the piece on its square).
- **trapped_piece is ruling #11's missing name**: `confirm_hanging` rejects
  the doomed piece ("no urgency, no lesson") — this detector names why it was
  doomed, with a per-square `no_escape` witness (mate-pattern style).
- **Primacy: candidates never preempt adjudicated vocabulary — not even
  across windows.** First cut returned a window-0 geometry hit immediately
  and broke rulings 0VHBI (early discovered-attack view silenced the true
  defender_removal two plies in) and 03cd7 (preempted file_battery). Fixed:
  `name_point` records the earliest geometry hit, finishes the graduated
  scan, attaches it as `geometry_candidate` (redacted from the LLM, like
  `mechanism_candidate`) and returns it alone only when mechanism, fork,
  hanging, and intermezzo are all silent. All 15 rulings green after.
- Verifier hardening: "battery" added to the doctrine-word blocklist (it was
  missing — an LLM could have said it unpunished).
- Tests: `tests/test_geometry_mechanisms.py` — 20 pure-geometry cases,
  positive + negative + orchestrator-primacy + redaction plumbing, every FEN
  hand-verified. Also repaired `research/experiments/test_rulings.py`'s stale
  `explainer.` imports/`sys.path` from the morning's `src/` rename (it
  couldn't run at all).

Graduation path: same as everything else — corpus run over the puzzle set,
precision sampling, human adjudication of the disagreements. Until then these
five are data, not speech (`docs/KNOWN_ISSUES.md` #7).

## 2026-07-22 (later still): the drill walker moves in from the backend

`drill.py` (`DrillState` — the forcing-win tree walker/adjudicator: play,
branch backtrack with deferred Continue, structural-path serialize/restore)
and `drill_feedback.py` (the deterministic feedback beats — never
LLM-authored) moved here from `lucena-backend/grounding_tools`, by the same
reasoning as the poisoned-line detector that morning: pure tree-walking
coaching logic, no DB, no session state — it belongs beside the tactical
vocabulary. Specifics:

- The tree itself is still built by `lucena_engine.line_tree.build_line_tree`
  (engine infrastructure); this module only WALKS caller-supplied trees.
- The backend keeps a thin re-export shim at `grounding_tools/drill.py`, so
  every import site (`tools.py`, `coaching/strategies.py`) is untouched; its
  sys.path bootstrap now has ONE home, `grounding_tools/_tactics_path.py`
  (shared with the poisoned_line_detector import).
- `drill.py` dual-imports `drill_feedback` (package-relative here, top-level
  under the backend's bootstrap).
- The two pure walker test files (`test_drill_restore.py`,
  `test_drill_history.py`) moved with it into `tests/`; the backend keeps its
  integration tests (`test_coach_drill.py` et al.), all green through the shim.
- An unreachable stale block after `continue_branch`'s return (a leftover
  duplicate of `_next_or_finish`'s ending) was dropped in transit — provably
  dead, behavior identical.

## 2026-07-23: the core migration — this repo becomes the tactical lifecycle

The engine-slim migration (full record: `docs/MIGRATION.md`) landed the rest
of the tactical stack here. lucena-engine is now a pure Stockfish/Maia
wrapper (public, AGPL); board truth (python-chess board + differential-gated
SEE port, positional, detect/pgn/openings) lives in the private
superrepo-level `lucena-core`; and this repo owns the whole tactical
lifecycle behind its three-part contract:

1. **why** — `(fen, solution, played)` → fact sheet (`factsheet.py`, existing)
2. **has_tactics** — `(fen[, move], engine)` → `TacticVerdict` (`has_tactics.py`,
   new): census proposes, `detect_combination`'s engine verdict decides
   "tactic", the analyse gap prices uniqueness
3. **tree** — tactical FEN → forcing-win tree (`line_tree.py`, `puzzle.py`,
   moved in) → walked by `DrillState` (`drill.py`)

New residents, all differential-gated against the frozen engine originals
before those were deleted (0 real diffs everywhere; two benign ordering
classes adjudicated + canonicalized — see MIGRATION.md):
- `src/census/` — the prospective detectors (fork, pin, hanging, defender,
  null_move, combination): what EXISTS in the position, complementing
  `mechanism.py`'s retrospective what-the-line-USED. SEE via `lucena_core.see`.
- `src/facts.py` + `src/hints.py` — the salience-ranked fact sheet + Socratic
  hint ladder.
- `src/_reconcile.py` — the engine-agreement kernel ("a SEE/geometry fact
  that contradicts the engine loses"), shared by `build_fact_sheet` and
  `has_tactics`.
- `src/brilliant.py` — sound-sacrifice (!!) classification.

Substrate: python-chess everywhere (the Rust board is gone); migrated modules
ride `lucena_core.board.Board` — the compat class with the old wrapper API —
while new code uses python-chess directly. That seam is deliberate and
documented, not an accident.

## 2026-07-24: detection completeness — the gap detectors land

The theme-coverage audit (`research/experiments/theme_coverage.py`, now the
permanent recall scoreboard: name_point over 120 Lichess-labeled puzzles per
theme) mapped the voids; this session filled them, recall-first — precision
is the adjudication loop's job later, and everything new stays candidate
tier (data, not speech).

New in `mechanism.py`: `detect_pin_setting` (fictional_defender +
frozen_bystander — the pin-as-setting shapes the capture-anchored pin
missed), `detect_xray` (through an ENEMY piece: the blocker leaves the ray,
the slider lands), `detect_interference` (occupying a defense ray; Novotny
flagged when ≥2 lines cut), `detect_clearance` (square + line shapes;
along-ray vacations are battery's job), `detect_windmill`, `detect_desperado`,
whole-line annotations (`sacrifice` via brilliant.is_material_sacrifice,
`promotion`/`underpromotion` incl. 7th-rank passers, `double_check`) with
promotion/underpromotion/sacrifice as last-resort candidates, mate returns
decorated with the window-0 geometry (the clearance that BUILT the mate is
still the geometric story), and a loosened discovered-attack (any-minor
second threat tier; mate counts as collection).

Coverage movement (named / theme-matched, before → after):
pin 56/10 → 83/45 · doubleCheck 87/2 → 95/95 · interference 45/0 → 72/25 ·
clearance 43/0 → 70/19 · xRay 76/0 → 91/67 · sacrifice 71/0 → 93/75 ·
promotion —/0 → **100/100** · attraction named 80 → 94 (matched stays 12 —
our graduated gates are stricter than the lichess label; adjudicate later).
Mates stay 100/100. Regression pins: `tests/test_gap_detectors.py`
(corpus-pinned real puzzles per detector). All 15 rulings hold throughout.

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
