"""The fact sheet — deterministic salience extraction (LLD-analysis §2.3).

Every engine-tool response is built from a fact sheet, never a bare position.
This module owns the `Fact` record and `build_fact_sheet`, which runs the M3
detector trio, ranks the raw facts by salience, assigns stable `F#` ids, and
truncates to the top five.

Detectors are *hints ranked by salience, never verdicts* — the material
verdict is always SEE / the engine, never these facts. Salience weights are
hand-tuned in v1 (LLD OQ#8); the formulas live in each detector and are pinned
in `docs/contracts/M3-facts.md`.

`Fact` is defined here (not in the detectors package) so the detectors import
it without a cycle: `build_fact_sheet` imports the detector functions lazily.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lucena_engine.evalmodel import MISTAKE as _MISTAKE, win_pct_from_score


@dataclass(frozen=True)
class Fact:
    """One salient, deterministically-extracted observation about a position.

    `id` is assigned by `build_fact_sheet` (detectors leave it ""). `squares`
    drive board arrows (a cited fact = an arrow). `provenance` is for
    debuggability; `concept_id` routes to the mastery model.
    """

    kind: str                       # "hanging" | "threat" | "defender-removed" | "opening"
    squares: list[str]              # board squares this fact points at
    text: str                       # short human sentence (no id, no eval)
    provenance: str                 # e.g. "see", "nullmove", "static"
    salience: float                 # 0..1, higher = lead with this
    concept_id: str                 # mastery routing (memory/domain.json)
    id: str = ""                    # "F1".. assigned at assembly time

    def with_id(self, id: str) -> "Fact":
        return Fact(
            kind=self.kind,
            squares=self.squares,
            text=self.text,
            provenance=self.provenance,
            salience=self.salience,
            concept_id=self.concept_id,
            id=id,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "squares": list(self.squares),
            "text": self.text,
            "provenance": self.provenance,
            "salience": round(self.salience, 3),
            "concept_id": self.concept_id,
        }


TOP_N = 5


def build_fact_sheet(
    board,
    engine=None,
    *,
    nodes: int | None = None,
    movetime_ms: int | None = None,
    top_n: int = TOP_N,
) -> list[Fact]:
    """Run the detectors over `board`, return the top `top_n` facts.

    Board-only detectors (hanging, defender-removed) always run. The null-move
    threat probe runs only when an `engine` is supplied; pass `nodes=` (tests,
    reproducible) or `movetime_ms=` (production) exactly as `Engine.analyse`
    expects — the same determinism split.

    When an engine is present, both hang directions are reconciled against the
    engine verdict (the §2.3 rule *a SEE fact that contradicts the engine loses*):
    `_reconcile_dangers` drops own-piece hangs the null-move probe does not
    confirm (a regained gambit pawn); `_reconcile_opportunities` drops enemy-piece
    hangs whose capture the engine scores as a blunder (a back-rank trap). Without
    an engine, neither runs — the board core cannot see past the single exchange,
    so the sheet is best-effort.

    Ranking: salience descending, with a deterministic tie-break so identical
    inputs always yield identical ids. Facts are assigned `F1..Fn` in rank
    order. Returns at most `top_n` facts (may be fewer, or empty).
    """
    # Lazy import breaks the facts <-> detectors cycle (detectors import Fact).
    try:                                  # package context (src.facts)
        from .census.hanging import detect_hanging
        from .census.defender import detect_defender_removed
        from .census.fork import detect_fork
        from .census.pin import detect_pin
        from .census.combination import detect_combination
        from .census.null_move import detect_null_move_threat
    except ImportError:                   # top-level context (backend bootstrap)
        from census.hanging import detect_hanging
        from census.defender import detect_defender_removed
        from census.fork import detect_fork
        from census.pin import detect_pin
        from census.combination import detect_combination
        from census.null_move import detect_null_move_threat

    raw: list[Fact] = []
    raw += detect_hanging(board)
    raw += detect_defender_removed(board)
    raw += detect_fork(board)
    raw += detect_pin(board)   # absolute pins — geometry, always true, no reconciliation
    if engine is not None:
        threats = detect_null_move_threat(
            board, engine, nodes=nodes, movetime_ms=movetime_ms
        )
        raw += threats
        raw += detect_combination(board, engine, nodes=nodes, movetime_ms=movetime_ms)
        raw = _reconcile_dangers(raw, threats)
        raw = _reconcile_opportunities(
            board, raw, engine, nodes=nodes, movetime_ms=movetime_ms
        )
        raw = _reconcile_forks(
            board, raw, engine, nodes=nodes, movetime_ms=movetime_ms
        )

    raw = _dedupe(raw)
    raw.sort(key=_rank_key)
    kept = raw[:top_n]

    # The opening name rides ALONGSIDE the ranking, never inside it. It is context ("this is the
    # Sicilian"), not a competing observation about the position, and the two do not trade off: given
    # a salience it would either evict a hanging queen from top_n, or be evicted by one and vanish
    # exactly when the position is quiet enough for the name to be the most useful thing to say.
    # `top_n` bounds the TACTICS, so it is applied before this.
    opening = _opening_fact(board)
    if opening is not None:
        kept = kept + [opening]
    return [f.with_id(f"F{i + 1}") for i, f in enumerate(kept)]


def _opening_fact(board) -> "Fact | None":
    """This position's opening, or None when it isn't a known one (any drill starting mid-game).

    No `squares`: an opening names the whole position, so there is nothing to point an arrow at — and
    a cited fact draws an arrow. Salience is set but unused for ordering (see above); it is kept
    non-zero so the field stays meaningful if the fact is ever ranked.
    """
    from lucena_core import openings
    name = openings.name_for(board.fen)
    if not name:
        return None
    return Fact(
        kind="opening",
        squares=[],
        text=f"This is the {name}.",
        provenance="openings-table",
        salience=0.3,
        concept_id="openings",
    )


# -- ranking -----------------------------------------------------------------

# Stable ordering when salience ties: a fixed kind priority, then squares, then
# text — so the same position always produces the same F-numbering.
_KIND_ORDER = {"combination": 0, "threat": 1, "fork": 2, "pin": 3, "hanging": 4,
               "defender-removed": 5, "opening": 6}


def _rank_key(f: Fact):
    return (-f.salience, _KIND_ORDER.get(f.kind, 99), tuple(f.squares), f.text)


try:                                  # package context (src.facts)
    from ._reconcile import (
        OPP_DROP_THRESHOLD as _OPP_DROP_THRESHOLD,   # noqa: F401 — re-export (tests pin it)
        reconcile_dangers as _reconcile_dangers,
        reconcile_forks as _reconcile_forks,
        reconcile_opportunities as _reconcile_opportunities,
    )
except ImportError:                   # top-level context (backend bootstrap)
    from _reconcile import (
        OPP_DROP_THRESHOLD as _OPP_DROP_THRESHOLD,   # noqa: F401
        reconcile_dangers as _reconcile_dangers,
        reconcile_forks as _reconcile_forks,
        reconcile_opportunities as _reconcile_opportunities,
    )



def _dedupe(facts: list[Fact]) -> list[Fact]:
    """Collapse facts of the same kind pointing at the same squares, keeping
    the highest-salience one. Two detectors can surface the same motif (e.g. a
    static own-piece hang and the null-move threat on it); we keep the stronger
    statement rather than double-count it in the top five."""
    best: dict[tuple, Fact] = {}
    for f in facts:
        key = (f.kind, tuple(f.squares))
        cur = best.get(key)
        if cur is None or f.salience > cur.salience:
            best[key] = f
    return list(best.values())
