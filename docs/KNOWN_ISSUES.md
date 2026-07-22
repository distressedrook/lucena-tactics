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
