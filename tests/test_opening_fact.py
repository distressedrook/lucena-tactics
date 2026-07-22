"""Opening facts through the fact sheet — moved from the engine's
test_openings.py (core-migration Phase 5): the opening TABLE is lucena_core's,
but the opening FACT is emitted by this repo's build_fact_sheet."""

from lucena_core import openings  # noqa: F401
from lucena_core.board import Board
from src.facts import build_fact_sheet

KINGS_PAWN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"   # 1.e4
RUY_LOPEZ = "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"
SICILIAN = "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2"    # 1.e4 c5
NOT_AN_OPENING = "8/8/8/4k3/8/4K3/8/7R w - - 0 1"


def _facts(fen, **kw):
    return build_fact_sheet(Board(fen), None, **kw)


def _openings_in(facts):
    return [f for f in facts if f.kind == "opening"]


def test_the_fact_sheet_emits_the_opening():
    facts = _facts(SICILIAN)
    got = _openings_in(facts)
    assert len(got) == 1
    assert "Sicilian" in got[0].text
    assert got[0].id, "the opening fact was not assigned an F-id"


def test_no_opening_fact_when_the_position_is_not_an_opening():
    assert _openings_in(_facts(NOT_AN_OPENING)) == []


def test_the_opening_points_at_no_squares():
    """A cited fact draws an arrow; an opening names the whole position, so there is nothing to
    point at."""
    assert _openings_in(_facts(RUY_LOPEZ))[0].squares == []


def test_the_opening_does_not_consume_a_tactical_slot():
    """`top_n` bounds the TACTICS. The opening rides alongside the ranking, so it can neither evict a
    real tactic nor be evicted by one — it must not trade off against them."""
    tactical_only = build_fact_sheet(Board(RUY_LOPEZ), None, top_n=1)
    assert len(_openings_in(tactical_only)) == 1
    # Everything else still fits its own budget.
    assert len([f for f in tactical_only if f.kind != "opening"]) <= 1


def test_ids_stay_contiguous_with_the_opening_appended():
    facts = _facts(RUY_LOPEZ)
    assert [f.id for f in facts] == [f"F{i + 1}" for i in range(len(facts))]


# -- the en-passant convention ---------------------------------------------------
#
# The table keys on norm_fen, which KEEPS the ep field, and it stores ep unconditionally on a double
# push (778/3733 rows carry one; `1.e4` is keyed with `e3`). That only works because our board core
# uses the same convention. python-chess uses the LEGAL-ONLY convention, against which every double
# push resolves to None.
#
# These MUST go through Board.apply, not FEN literals. The other tests in this file use hardcoded
# FENs and would keep passing if the board core switched conventions tomorrow — while every opening
# starting with a double push silently vanished. A miss is indistinguishable from "not an opening",
# which is exactly how the broken table path shipped unnoticed.

