# Known issues

Open bugs and gaps that are understood but not yet fixed. Carried over from
`PROGRESS.md` (retired 2026-07-22, folded into `CLAUDE.md`) — nothing here is
new as of the restructure; these were already-known, not yet actioned.

## 1. The engine server isn't supervised

**Where:** the running lucena-engine gRPC server this repo talks to
(`LUCENA_ADDR`, default `127.0.0.1:50052`).

**What's wrong:** as of day one it ran from a bare `nohup` out of a scratchpad
venv, not a supervised (launchd/systemd-style) process with a repo-local venv.
A stale v0.1.0 pair was also left running on `:50051` from a trashed venv —
`GetInfo`'s `maia_available` lies on those, and the Maia policy field always
reads 0.0. Retire the stale pair; give the real one a supervised launch.

## 2. Failure boundary: tactical puzzles only, no endgame technique

**Where:** `src/mechanism.py` / `src/factsheet.py`'s whole model.

**What's wrong:** validated at ~95%+ on tactical puzzles; ~0% on endgame
technique (pawn races, king walks — anything whose "why" isn't a forcing
tactical branch but a technique/plan). This is a scope boundary, not a bug —
the positional/plan layer (now `lucena-plans`) is where that lives — but it's
worth stating explicitly since a caller could reasonably expect this repo to
explain an endgame mistake and get nothing useful back.

## 3. `intermezzo` and `file_battery` are candidate-tier, unadjudicated

**Where:** `src/mechanism.py`'s mechanism vocabulary.

**What's wrong:** `intermezzo` (two-pending-threats ordering) fired 9 times
one session and was never adjudicated; `file_battery` (ruling #14's new
vocabulary) has no detector at all yet, just the naming precedent. Both need
the same ruling-loop treatment (a human adjudicates a handful of cases, the
verdict compiles into a rule) the other 11 mechanisms already went through.

## 4. `overload` is conditional, not graduated

**Where:** `src/mechanism.py`.

**What's wrong:** two competing views exist (conscription — a rule-forced
reply — vs. second-duty) with no single adjudicated rule picking between them
per case. Ruling #6 (rule-forced reply → conscription, not luring →
overload primary) partially addresses this but the mechanism as a whole
hasn't been pushed to graduated status.

## 5. Precompute cache — the ship-blocker (unbuilt)

**Where:** the whole `src/server.py` request path.

**What's wrong:** `POST /why` computes the fact sheet online (10-60s latency:
engine counterfactuals + LLM lexicalization), for every request, even on a
fixed puzzle set. The fix — puzzle set × Maia top-3 human foils, fact sheets
precomputed offline — turns "click why" into a lookup and freezes outputs for
QA. Flagged as a ship-blocker at the end of day one; still unbuilt.

## 6. `plan_foil` / intent attribution: verdict was "build interactive, not
   automatic"

**Where:** the (unbuilt) intent-classification path referenced in
`CLAUDE.md`'s roadmap.

**What's wrong:** duty-retention enumeration (why a *plan* fails, not just a
move) is reliable only when the user STATES their intended plan — automatic
intent attribution from the board alone was tested and judged unverifiable.
Don't build an automatic version; the interactive one (user states the idea,
system refutes it via the duty table) is the validated design.

## 7. Ray-geometry vocabulary is candidate-tier, zero adjudications

**Where:** `src/mechanism.py` — `detect_pin`, `detect_skewer`,
`detect_discovered_attack`, `detect_trapped_piece`, `detect_battery`
(added 2026-07-22).

**What's wrong:** nothing known — but nothing validated either. The five
detectors are pure geometry with line-anchored causality and 20 green unit
tests, but zero corpus numbers and zero human rulings. Per the graduation
gate they are never spoken: `name_point` returns them only when every
adjudicated mechanism is silent, and the factsheet stores them as
`mechanism_candidate` / attaches them as `geometry_candidate` (both redacted
from the LLM's input). Known soft spots to probe during adjudication:

- `detect_pin` shape B (`win_pinned`, relative pins) is the noisiest by
  construction — a mundane winning exchange can coincide with an incidental
  ray alignment. Expect the adjudication loop to tighten the "pin mattered"
  gate the way rulings #1/#7 tightened the lure gates.
- `detect_trapped_piece` uses attackers() counts for its escape accounting —
  a pinned "hunter" is counted as covering a flight square it can't legally
  take on.
- `detect_battery` requires the rear recapture to come literally from the
  rear square; a tripled battery or a rearranged recapture order won't fire.

Graduation needs the standard funnel: run over the 299-puzzle corpus +
held-out set, sample precision, adjudicate the disagreements, then admit each
mechanism to the factsheet's GRADUATED set (and template prose) one by one.

## 8. corpus_labels.jsonl.gz lost in the history purge (regenerable, engine-hours)

**Where:** `research/experiments/corpus_labels.jsonl.gz` (326MB, gitignored now).

**What's wrong:** the 2026-07-23 pre-push history rewrite (large corpora
should never have been committed; the pack was 381MB) removed the file from
git AND — because it was tracked — from the working tree, and no other copy
existed on this machine. It was the labeling pipeline's intermediate output
(`label_corpus.py` over the Lichess puzzle corpus). The VALIDATED artifacts
all survive: `results.jsonl`, `results_heldout.jsonl`, `episodes.jsonl`,
`adjudication_verdicts.json`, `test_rulings.py`. Regenerate when next needed
by re-running the labeling pipeline over `lichess_db_puzzle.csv` (restored on
disk from the Downloads .zst) — deterministic at fixed nodes, but costs
engine-hours; exact byte-identity with the lost file is not guaranteed if the
upstream puzzle snapshot differs.

## 9. Gap detectors (2026-07-24) are recall-first, zero adjudications

**Where:** `src/mechanism.py` — `detect_pin_setting`, `detect_xray`,
`detect_interference`, `detect_clearance`, `detect_windmill`,
`detect_desperado`, the whole-line annotations, and the loosened
discovered-attack tier.

**What's wrong:** deliberately nothing filtered yet — the owner's ruling for
this batch was "see to it that all the patterns are detected; explanation
comes later." Expect real false positives (the loose discovered-attack tier,
frozen_bystander pins, square-clearance) and taxonomy fights (our attraction
vs lichess's — matched 12% while named 94%). The theme-coverage harness
(research/experiments/theme_coverage.py) is the scoreboard; graduation for
each name needs the standard funnel (corpus precision sampling + human
rulings) before anything is spoken. Interference (25%) and clearance (19%)
matched-rates say the detectors catch the crisp shapes only — the fuzzy
remainder (defensive-line cuts to squares, multi-purpose clearances) needs
either richer shapes or the adjudication loop's verdict that the label is
the noisy party.
