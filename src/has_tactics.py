"""Contract #2 — `(fen[, move])` → is there a tactic here?

A grounded verdict assembled from existing machinery — no new detection
science, pure re-plumbing (the design ruling for this front door):

  1. CENSUS proposes: `build_fact_sheet` runs the detectors and the
     engine-agreement kernel (`_reconcile`) — every surviving motif is
     already engine-reconciled.
  2. The COMBINATION verdict decides "tactic": `detect_combination` is the
     engine's own confirmation that a forcing win / decisive shot exists
     (mate, or a forcing move clearly better than every alternative). No
     combination fact → no "tactic" claim, however loud the geometry.
  3. The ANALYSE GAP prices uniqueness: best-vs-second win% — the same
     quantity the factsheet's premise gate uses.

Verdicts:
  tactic — engine-confirmed forcing shot (combination fact present); the FEN
           then flows to `line_tree.build_line_tree` for contract #3.
  soft   — reconciled motifs exist (something hangs, a fork is in the air)
           but no confirmed forcing shot.
  none   — the sheet is quiet.

Determinism: same split as everything else — pass `nodes=` (tests,
reproducible with threads=1 + `new_game()`) or `movetime_ms=` (production).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lucena_core.board import Board
from lucena_core.reads import pv_san
from lucena_engine.evalmodel import win_pct_from_score

try:                                  # package context (src.has_tactics)
    from .facts import build_fact_sheet
except ImportError:                   # top-level context (backend bootstrap)
    from facts import build_fact_sheet


@dataclass(frozen=True)
class TacticVerdict:
    verdict: str                      # none | soft | tactic
    fen: str                          # the position judged (after `move` if given)
    swing_wp: float | None            # best-vs-second win% gap (uniqueness)
    entry_san: str | None             # the shot's first move (tactic only)
    principal_line: list[str] = field(default_factory=list)   # SAN, engine best line
    motifs: list[dict] = field(default_factory=list)          # reconciled census facts

    def to_dict(self) -> dict:
        return {"verdict": self.verdict, "fen": self.fen,
                "swing_wp": self.swing_wp, "entry_san": self.entry_san,
                "principal_line": list(self.principal_line),
                "motifs": list(self.motifs)}


def has_tactics(fen: str, move: str | None = None, *, engine,
                nodes: int | None = None,
                movetime_ms: int | None = None) -> TacticVerdict:
    """Judge the position (after applying `move`, if given). Requires an
    engine — the whole point of the verdict is that it is engine-confirmed,
    never geometry alone."""
    b = Board(fen)
    if move is not None:
        b = b.apply(move)             # raises ValueError on an illegal move

    facts = build_fact_sheet(b, engine, nodes=nodes, movetime_ms=movetime_ms)
    motifs = [f.to_dict() for f in facts if f.kind != "opening"]
    combo = next((f for f in facts if f.kind == "combination"), None)

    a = engine.analyse(b.fen, nodes=nodes, movetime_ms=movetime_ms, multipv=2)
    swing = None
    if len(a.lines) > 1:
        swing = round(win_pct_from_score(a.best.score)
                      - win_pct_from_score(a.lines[1].score), 1)
    line = pv_san(b.fen, a.best.pv)

    if combo is not None:
        entry_uci = combo.provenance.split(":", 1)[1]     # "combo:<uci>" | "mate:<uci>"
        return TacticVerdict("tactic", b.fen, swing, Board(b.fen).san(entry_uci),
                             line, motifs)
    if motifs:
        return TacticVerdict("soft", b.fen, swing, None, line, motifs)
    return TacticVerdict("none", b.fen, swing, None, [], motifs)
