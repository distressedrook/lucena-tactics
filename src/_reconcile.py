"""The engine-agreement kernel — LLD §2.3's hierarchy rule in one place:
*a SEE/geometry fact that contradicts the engine loses.*

Extracted from facts.py (core-migration Phase 6, 2026-07-23) so the two
clients — `build_fact_sheet` (the why-wrong sheet) and `has_tactics` (the
is-there verdict) — share one reconciliation truth. Behavior-verbatim; the
ported test_facts suite is the regression harness.
"""

from __future__ import annotations

from lucena_engine.evalmodel import MISTAKE as _MISTAKE, win_pct_from_score



def reconcile_dangers(facts: list[Fact], threats: list[Fact]) -> list[Fact]:
    """Engine-verdict gate on own-piece "danger" hangs (LLD §2.3 hierarchy: *a
    SEE fact that contradicts the engine line loses*).

    `detect_hanging` flags an own piece as hanging whenever the opponent has a
    SEE-winning capture on it — but SEE sees only the one square, blind to a
    recapture or gambit compensation a move later. A pawn "hanging" to `dxc4`
    that the mover simply regains (eval unchanged) is not a real danger; leading
    with it mis-coaches the position.

    The engine already computes the truth: the null-move probe plays the mover's
    pass and reads the opponent's best reply. A danger hang survives ONLY if a
    threat fact confirms the opponent actually wins that piece (same target
    square). Unconfirmed danger hangs are dropped. Opportunity hangs (winning an
    enemy piece) and everything else are untouched.

    Limitation: the probe surfaces the opponent's single best reply, so if two of
    the mover's pieces hang at once only the graver one is confirmed — acceptable,
    since the mover can save only one and the engine leads with the worst.
    """
    confirmed = {t.squares[1] for t in threats if len(t.squares) >= 2}
    kept = []
    for f in facts:
        is_danger_hang = f.kind == "hanging" and f.provenance.startswith("nullsee:")
        if is_danger_hang and f.squares[0] not in confirmed:
            continue  # SEE says hanging, the engine disagrees — drop it
        kept.append(f)
    return kept

# A SEE/geometry "win" (an opportunity hang or a fork) that drops win% by at least this much versus
# the mover's best move is a FALSE opportunity — it nets material on the target square but the engine
# rates taking clearly inferior (a positional cost, a zwischenzug, a back-rank mate). Tied to the eval
# model's MISTAKE line, not a hand-picked number: if the engine would grade the capture a mistake (or
# worse), the coach must not surface it as "you can win X". Was _BLUNDER (15.0), which let mistake-
# level false wins through (e.g. Bxd5 in the corpus — wins a pawn, throws away +1.6). Locked by
# `test_opportunity_reconciliation_corpus`.
OPP_DROP_THRESHOLD = _MISTAKE
_OPP_DROP_THRESHOLD = OPP_DROP_THRESHOLD  # internal alias, kept for the docstring-cited name


def reconcile_opportunities(
    board, facts, engine, *, nodes=None, movetime_ms=None
) -> list[Fact]:
    """Engine-verdict gate on opportunity hangs (the §2.3 per-candidate
    counterfactual; same hierarchy rule as `reconcile_dangers`).

    An opportunity hang says "you can win X (SEE > 0)". SEE nets material on the
    target square but is blind to everything off it — so the capture can still be
    a blunder (a back-rank mate, a zwischenzug, opening your own king). We play
    the capture and read the engine's eval of the result from the mover's POV; if
    taking drops win% by a blunder's worth vs the mover's best move, the SEE fact
    contradicts the engine and is dropped.

    Cost: one analysis of the real position, then one per *suspect* capture — the
    prune skips any capture that already **is** the engine's best move (obviously
    sound), so clean tactics cost nothing extra. All local Stockfish, no Claude
    tokens. (The real-position analysis duplicates one the null-move probe made
    internally; sharing it is a future tidy-up, not a correctness issue.)
    """
    opp = [
        f for f in facts
        if f.kind == "hanging" and f.provenance.startswith("see:")
    ]
    if not opp:
        return facts

    real = engine.analyse(board.fen, nodes=nodes, movetime_ms=movetime_ms, multipv=1)
    best_move = real.best.pv[0] if real.best.pv else None
    best_win = win_pct_from_score(real.best.score)

    dropped: set[str] = set()
    for f in opp:
        uci = f.provenance.split(":", 1)[1]
        if uci == best_move:
            continue  # the engine's own choice — sound, skip the counterfactual
        after = board.apply(uci)
        if not after.legal_moves():
            after_win = 100.0 if after.in_check else 50.0  # capture mates / stalemates
        else:
            after_score = engine.analyse(
                after.fen, nodes=nodes, movetime_ms=movetime_ms, multipv=1
            ).best.score
            after_win = win_pct_from_score(after_score.negated())
        if best_win - after_win >= _OPP_DROP_THRESHOLD:
            dropped.add(f.provenance)  # SEE says win, the engine says blunder — drop

    if not dropped:
        return facts
    return [f for f in facts if f.provenance not in dropped]


def reconcile_forks(
    board, facts, engine, *, nodes=None, movetime_ms=None
) -> list[Fact]:
    """Engine-verdict gate on fork facts (same §2.3 rule and per-candidate
    counterfactual as `reconcile_opportunities`).

    `detect_fork` is board-geometry only: it sees that a move attacks two loose
    targets, but not whether the whole shot is *sound* — the forking piece may
    itself be lost to a resource off those squares, or the position simply has
    something clearly better, in which case leading with the fork mis-coaches.
    We play each forking move and read the engine's eval of the result from the
    mover's POV; a fork that drops win% by a blunder's worth versus the mover's
    best move contradicts the engine and is dropped. A fork that already **is**
    the engine's best move is kept without a counterfactual (it is the point of
    the position). All local Stockfish, no Claude tokens."""
    forks = [f for f in facts if f.kind == "fork"]
    if not forks:
        return facts

    real = engine.analyse(board.fen, nodes=nodes, movetime_ms=movetime_ms, multipv=1)
    best_move = real.best.pv[0] if real.best.pv else None
    best_win = win_pct_from_score(real.best.score)

    dropped: set[str] = set()
    for f in forks:
        uci = f.provenance.split(":", 1)[1]
        if uci == best_move:
            continue  # the engine's own choice — sound, skip the counterfactual
        after = board.apply(uci)
        if not after.legal_moves():
            after_win = 100.0 if after.in_check else 50.0
        else:
            after_score = engine.analyse(
                after.fen, nodes=nodes, movetime_ms=movetime_ms, multipv=1
            ).best.score
            after_win = win_pct_from_score(after_score.negated())
        if best_win - after_win >= _OPP_DROP_THRESHOLD:
            dropped.add(f.provenance)  # geometry says fork, the engine says worse — drop

    if not dropped:
        return facts
    return [f for f in facts if f.provenance not in dropped]
