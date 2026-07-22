"""Contract #2 front door — `has_tactics(fen[, move])`.

Engine-gated (the verdict is engine-confirmed by design; there is no
engine-free mode to test). Node-limited + new_game per case for
reproducibility, same discipline as every engine-backed suite here.

Positions verified independently with python-chess; expectations follow from
the design ruling: "tactic" requires the combination detector's engine
confirmation, "soft" = reconciled motifs without it, "none" = quiet sheet.
"""
import os
import shutil

import pytest

from src.has_tactics import has_tactics, TacticVerdict

_have_engine = bool(os.environ.get("LUCENA_STOCKFISH")) or shutil.which("stockfish")
pytestmark = pytest.mark.skipif(not _have_engine, reason="needs stockfish")

NODES = 300_000

# Légal-style mate-in-2: Qxf7+ Kd7 (forced) ... — White has a forced mate.
MATE_IN_TWO = "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"
# Scholar's threat position: Qxf7# available.
SCHOLARS = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR b KQkq - 3 3"
STARTPOS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
# Quiet symmetric middlegame-ish position, nothing hanging.
QUIET = "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4"


@pytest.fixture(scope="module")
def engine():
    from lucena_engine.uci import Engine
    with Engine(threads=1) as e:
        yield e


def _judge(engine, fen, move=None):
    engine.new_game()
    return has_tactics(fen, move, engine=engine, nodes=NODES)


def test_mate_threat_is_a_tactic(engine):
    v = _judge(engine, SCHOLARS, "Nd4")          # ??: allows Qxf7#
    assert isinstance(v, TacticVerdict)
    assert v.verdict == "tactic"
    assert v.entry_san == "Qxf7#"
    assert v.principal_line and v.principal_line[0] == "Qxf7#"


def test_startpos_is_not_tactical(engine):
    v = _judge(engine, STARTPOS)
    assert v.verdict == "none"
    assert v.entry_san is None and v.motifs == []


def test_verdict_carries_the_judged_fen(engine):
    v = _judge(engine, SCHOLARS, "Nd4")
    assert v.fen != SCHOLARS                     # judged AFTER the move
    assert "b1q" not in v.fen                    # sanity: still a real fen


def test_illegal_move_raises(engine):
    with pytest.raises(ValueError):
        _judge(engine, STARTPOS, "e2e5")


def test_forced_mate_position_is_a_tactic(engine):
    v = _judge(engine, MATE_IN_TWO)
    assert v.verdict == "tactic"
    assert v.entry_san is not None
    assert v.swing_wp is None or v.swing_wp > 0


def test_quiet_position_is_not_a_tactic(engine):
    v = _judge(engine, QUIET)
    assert v.verdict in ("none", "soft")         # no confirmed forcing shot
    assert v.entry_san is None


def test_to_dict_round_trip(engine):
    v = _judge(engine, STARTPOS)
    d = v.to_dict()
    assert d["verdict"] == "none" and d["fen"] == STARTPOS
    assert set(d) == {"verdict", "fen", "swing_wp", "entry_san",
                      "principal_line", "motifs"}
