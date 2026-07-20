# chess-lab — progress log

*Last updated: 2026-07-20 (day one — theory to shipped pipeline in one session)*

---

## The thesis

A Stockfish PV is a **conclusion with the proof deleted**. The engine computes
the why — the tree of refuted alternatives — then discards it. So the why is
never *parsed* from the line and never *inferred* by an LLM; it is
**reconstructed by re-querying the engine with counterfactuals**, expressed as
witnessed predicates, and only then lexicalized into prose.

Core principles, each validated the hard way today:

- **Explanation is contrastive.** The explanandum is (line, foil), never the
  line alone. For puzzles the foil is given — the user's failed move.
- **Tactical why = the difference between branches. Positional why = the
  invariant across branches.** (Positional layer designed, not yet built.)
- **Presence is geometry; the point is causality.** A fork that exists but
  isn't *used* is trivia. Every mechanism claim needs a counterfactual.
- **An unsound proof is worse than silence.**
- **The LLM is a lexicalizer, never an analyst.** Every sentence must trace to
  a witnessed slot; violations are detected mechanically and rejected.
- **Human adjudication supplies definitions, not labels.** One ruling on one
  case compiles into a rule that re-adjudicates the whole corpus.

---

## What is built (committed)

### The product pipeline (`explainer/`)

`POST /why {fen, solution, played}` → grounded coaching explanation.

| module | role |
|---|---|
| `probes.py` | engine truth — fixed-node gRPC to lucena-engine (deterministic) |
| `predicates.py` | ply-level geometric predicates (total functions, python-chess) |
| `mechanism.py` | mechanism naming: geometric theorems + engine counterfactuals |
| `factsheet.py` | two-axis fact sheet (forfeit × error), every slot witnessed |
| `takeaways.py` | curated habit table — hand-written pedagogy, deterministic |
| `lexicalize.py` | Gemini as constrained lexicalizer + verifier + template floor |
| `server.py` / `cli.py` | FastAPI endpoint / CLI |

### The fact sheet (two axes + trimmings)

- **forfeit** (what the solution won): `mate_in_N`, `forced_mate`,
  `winning_attack`, `wins_<piece>` (NET accounting — trades don't count as
  wins), `promotion`, `decisive_threat`, `advantage` (margin-scaled language)
- **error** (what the played move did wrong): `hung`, `bad_trade` (initiated
  exchange ≠ hanging), `wrong_piece`, `move_order`, `allowed_forcing_reply`,
  `none` (pure omission — no scolding)
- plus `refutation`, `delta`, `salvage` (3-state), `mechanism`, `takeaway`

### Mechanism vocabulary (11 mechanisms)

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
| overload | conditional | conscription (rule-forced reply) or second-duty view |
| intermezzo | candidate | new tonight — two-pending ordering shape (0JDnk); 9 fired, needs adjudication |
| file_battery | candidate | new vocabulary from ruling #14; needs a real detector |

### The verifier contract (LLM hardening)

1. No fabricated moves — SAN tokens must trace to witnesses (recursive)
2. No fabricated mechanisms — doctrine-word blocklist
3. No omitted mechanisms — graduated mechanism must be spoken (coverage)
4. No unratified claims — candidates are redacted from the LLM's input
5. Floor = deterministic template, always true

Stress-tested against Sonnet (fabricated "overload"/"clean piece up" —
caught) and gemini-flash-lite (omitted the mechanism — caught). Config:
`GEMINI_API_KEY`, `EXPLAINER_GEMINI_MODEL` (currently flash-lite).

---

## Validation (all measured, all reproducible)

| claim | number | where |
|---|---|---|
| Mistake-explanation completeness | **86% held-out** (== train; no overfit) | 200 fresh Lichess puzzles, v2.1 classifier |
| Maia foil coverage | 400/400 | both runs |
| Mechanism coverage | 53% of puzzles get a named point | 299-puzzle corpus |
| Mechanism label agreement | **87%** (labels known-incomplete → lower bound) | same corpus |
| Adjudication | **55 cases → 0 pending** | `experiments/adjudication_verdicts.json` |
| Regression suite | 15 rulings, two tiers, all green | `experiments/test_rulings.py` |

Failure boundary is *mapped*: tactical puzzles ~95%+, endgame technique ~0%
(pawn races, king walks — the positional layer's job).

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

## Supporting results from earlier in the day

- **Positional pipeline (designed + prototyped):** term-trajectory extractor
  over the Carlsbad corpus works (`experiments/trajectory.py`); v1 needs
  quiescence filtering + drift (not event) segmentation. 311k elite games
  downloaded; ~15k/month Carlsbad candidates.
- **Plan-discovery design:** segment → delta-vectors → cluster within pawn
  structures → human names clusters → rediscovery test on Carlsbad. Pilot
  costed at ~$0 cash, ~15–25 human hours.
- **plan_foil analysis** (why a *plan* fails): duty-retention enumeration
  demonstrated on 0L0Sw (`f5 Ng3!` — one square does both jobs). Verdict:
  reliable only for *stated* intent (user tells us their idea); automatic
  intent attribution is unverifiable — build interactive, not automatic.
- **LLM-provider decision:** Gemini (user's key). Model is deliberately the
  least-trusted, most-replaceable component.

---

## Next plans (priority order)

### Ship-blockers
1. **Precompute cache** — puzzle set × Maia top-3 human foils → fact sheets
   computed offline. Kills the 10–60s online latency; click-"why" becomes a
   lookup. Also freezes outputs for QA.
2. **Supervised engine server** — v0.1.2 currently runs from a `nohup` out of
   a scratchpad venv on :50052. Needs a launchd/systemd-style supervised
   launch + repo-local venv. (Also: `maia_available` lies on the stale
   :50051 servers; Maia policy field always 0.0 — file upstream.)

### Product depth
3. **0IJMb final ruling** (user ✅ vs confirm-tier reject; recommendation:
   uphold ruling #7 — all defenses within 27cp).
4. **Intermezzo adjudication** (9 candidates) and **x-ray/skewer vocabulary**
   (0L0Sw: skewer-poisoned recapture; founding case waiting).
5. **Takeaway table curation** — expand/edit `takeaways.py` (user-owned).
6. **Tagged-sentence verification** — sentence-level slot citations; the last
   step before letting a stronger LLM write prose in production.
7. **plan_foil interactive mode** — "here's what I was trying" → duty-table
   refutation of the stated plan (founding case 0L0Sw, user's own f5 idea).

### Research track
8. **Positional layer v1** — quiescence + drift segmentation → first human
   audit of ~100 episodes → invariance probes.
9. **Plan discovery pilot** — Carlsbad rediscovery test.
10. **idea.py** — explain *correct* moves: foil = opponent's defenses;
    enumerate → refute → ablate.

### Longer horizon
- Mechanism vocabulary expansion: pins/skewers as alignment triples,
  discovered attacks (predicate exists), clearance, interference.
- Intent classifier as proposer-only (Maia-style firewall), trained on
  pipeline output at scale; unsupervised plan discovery feeding a named,
  verifiable plan vocabulary.
- The falsification tests: explanation→position identification; annotator
  agreement on mechanism names vs Lichess themes at scale.

---

## Infrastructure notes

- Engine: lucena-engine gRPC on :50052 (v0.1.2 from ~/Development/lucena via
  PYTHONPATH; stale v0.1.0 pair on :50051 from a Trashed venv — retire them).
- Maia: `~/.lucena/maia-venv` (maia3), wired via `LUCENA_MAIA`.
- Determinism: fixed nodes everywhere (`EXPLAINER_NODES=2M`, forfeit probe 4M).
- Data: experiments/*.jsonl are the validated corpus runs (train + held-out);
  adjudication record in `adjudication_verdicts.json`.
- Gemini key was pasted in-session — **rotate it**.

---

## Addendum (late day one): the three-tagged-games experiment

Three annotated study games (Lilienthal, Tal, Benko — minority attack, spans
marked by the annotator) produced the positional track's first major finding:

**The minority attack's CREATION phase is invisible to static term drift.**
Across all three annotated spans, no eval term moves consistently (pawns +8/+9cp
— the backward c-pawn's value is future pressure, not present centipawns). What
v1's drift detection finds is the EXPLOITATION phase (Benko: activity +181,
pawns +136 after the weakness was fixed). The sowing is silent; the harvest drifts.

**The invariant is the CHOREOGRAPHY**: minority-side pawn traffic (b2-b4-b5,
a4 support) and the b5/c6 lever. Plans that restructure are observable in the
moves; plans that accumulate are observable in the terms. The episode
representation must carry both channels or clustering finds only harvests.

**Consequence delivered immediately**: `detect_minority_attack()` — a
choreography theorem, mechanism-style — found **53 minority attacks in 28,461
elite games** on first run. The first named, detectable, corpus-validated plan
in the system. Method note: 3 tagged games -> falsified a representation,
refined the theory, and yielded a working detector, in under an hour — the
ruling-loop applied to plans.

---

## 2026-07-21: positional track split out

The plan-naming / positional-pedagogy work now lives in its own project:
`~/Development/chess-plans` (detectors, trajectories, episodes, study data,
CLAUDE.md with full context). chess-lab stays focused on tactical puzzle
explanations. Shared method, independent code.
