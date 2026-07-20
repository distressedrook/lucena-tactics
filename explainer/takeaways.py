"""The coach's wisdom layer — curated, human-authored, deterministic.

Maps (forfeit class, error class, mechanism) -> a transferable habit.
This is pedagogy, not chess truth: edit freely, no verification needed,
because these are general principles a coach vouches for — the one layer
that SHOULD be hand-written. First match wins; None = no tip.
"""
from __future__ import annotations

from .factsheet import FactSheet

# (forfeit prefix | "*", error | "*", mechanism | "*") -> habit
_TABLE: list[tuple[str, str, str, str]] = [
    ("mate_in_1", "*", "*",
     "checks before captures — scan every check before any other move."),
    ("mate_in", "*", "back_rank_mate",
     "an unmoved pawn shield means back-rank danger — make luft, or exploit theirs."),
    ("mate_in", "*", "*",
     "when you are winning, hunt forcing moves first: checks, captures, threats."),
    ("forced_mate", "*", "*",
     "when the king is exposed, calculate checks to the end before grabbing material."),
    ("*", "bad_trade", "*",
     "count the whole exchange before starting it — including every recapture."),
    ("*", "hung", "*",
     "before every move, ask what your piece lands on and who attacks it there."),
    ("*", "move_order", "*",
     "right idea, wrong order — play the most forcing version of your idea first."),
    ("*", "wrong_piece", "*",
     "when two pieces can reach the same square, calculate both — the survivor matters."),
    ("*", "*", "fork",
     "after every forcing move, look for squares that attack two things at once."),
    ("*", "*", "deflection",
     "list each defender's jobs — a piece with two duties can be dragged off one."),
    ("*", "*", "defender_removal",
     "attack the guard, not the guarded — remove the defender and the target falls."),
    ("*", "*", "hanging_piece",
     "every move, scan your opponent's last move for what it stopped defending."),
    ("*", "*", "attraction",
     "a compelled capture can be a trap — ask where the capturing piece ends up."),
    ("wins_", "none", "*",
     "nothing was wrong with your move except the missed shot — slow down on quiet-looking positions."),
]


def takeaway(fs: FactSheet) -> str | None:
    forfeit = fs.forfeit.value if fs.forfeit else ""
    error = fs.error.value if fs.error else ""
    mech = ""
    if fs.forfeit is not None:
        m = fs.forfeit.witness.get("mechanism")
        if isinstance(m, dict):
            mech = m.get("mechanism", "")
    for f_pat, e_pat, m_pat, tip in _TABLE:
        if (f_pat == "*" or forfeit.startswith(f_pat)) \
                and (e_pat == "*" or error == e_pat) \
                and (m_pat == "*" or mech == m_pat):
            return tip
    return None
