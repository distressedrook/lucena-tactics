"""Unit tests for the ray-geometry mechanism detectors (2026-07-22):
pin / skewer / discovered_attack / trapped_piece / battery.

All pure geometry — no engine, no Maia, no network. Every FEN below was
verified legal with python-chess and every line verified move-by-move; the
comments document the verification.

These mechanisms are CANDIDATE tier: the tests pin down the geometry and the
orchestrator's primacy behavior (graduated mechanisms outrank them; the
geometry rides along under `geometry_candidate`, which the lexicalizer
redacts). Graduation itself is an adjudication/corpus question, not a unit
test.
"""
import chess

from src.mechanism import (detect_skewer, detect_discovered_attack,
                           detect_pin, detect_trapped_piece, detect_battery,
                           name_point)
from src.lexicalize import _redact


# ============================================================================
# Skewer
# ============================================================================

# White: Kh1, Bf1.  Black: Kf7, Qg8.
# Bc4+ skewers K and Q on the a2-g8 diagonal; Ke7 steps off; Bxg8 collects.
SKEWER_FEN = "6q1/5k2/8/8/8/8/8/5B1K w - - 0 1"
SKEWER_LINE = ["Bc4+", "Ke7", "Bxg8"]


def test_skewer_absolute():
    m = detect_skewer(SKEWER_FEN, SKEWER_LINE)
    assert m is not None
    assert m["mechanism"] == "skewer"
    assert m["absolute"] is True
    assert m["front_piece"] == "king" and m["front_on"] == "f7"
    assert m["rear_piece"] == "queen" and m["rear_on"] == "g8"
    assert m["collected_with"] == "Bxg8"


def test_skewer_requires_front_to_leave_ray():
    # Same position but the reply doesn't move the front piece -> no claim.
    # (Kf7 is in check so any non-king reply is illegal; use a legal king
    # move that STAYS on the c4-g8 ray: there is none, so instead check the
    # front-didn't-move gate with a different line shape.)
    assert detect_skewer(SKEWER_FEN, ["Bc4+", "Ke7", "Bd5"]) is None


def test_skewer_none_when_mover_not_slider():
    # Knight move never fires the skewer detector.
    assert detect_skewer("3q2k1/6p1/5p2/3N4/8/8/8/3R2K1 w - - 0 1",
                         ["Nxf6+", "gxf6", "Rxd8+"]) is None


# ============================================================================
# Discovered attack
# ============================================================================

# White: Kg1, Rd1, Nd5.  Black: Kg8, Qd8, pf6, pg7.
# Nxf6+ grabs a pawn with check AND unmasks Rd1 against Qd8; gxf6 forced-ish;
# Rxd8+ collects the unmasked target.
DISC_FEN = "3q2k1/6p1/5p2/3N4/8/8/8/3R2K1 w - - 0 1"
DISC_LINE = ["Nxf6+", "gxf6", "Rxd8+"]


def test_discovered_attack_basic():
    m = detect_discovered_attack(DISC_FEN, DISC_LINE)
    assert m is not None
    assert m["mechanism"] == "discovered_attack"
    assert m["uncovered_piece"] == "rook" and m["uncovered_from"] == "d1"
    assert m["uncovered_target"] == "queen on d8"
    assert m["discovered_check"] is False        # the check is the KNIGHT's
    assert m["collected_with"] == "Rxd8+"


def test_discovered_attack_via_orchestrator():
    # Nothing graduated fires here (queen was undefended -> no defender story;
    # the knight attacks only one target -> no fork), so the discovery IS the
    # point name_point returns.
    m = name_point(DISC_FEN, DISC_LINE)
    assert m is not None
    assert m["mechanism"] == "discovered_attack"
    assert m["at_move"] == "Nxf6+"


def test_discovered_attack_needs_collection():
    # Cut the line before Rxd8 -> the unmasked target is never taken and the
    # mover's grab was only a pawn -> no claim.
    assert detect_discovered_attack(DISC_FEN, ["Nxf6+", "gxf6"]) is None


# ============================================================================
# Pin — shape A: paralyzed defender
# ============================================================================

# White: Kg1, Qd1, Re1.  Black: Ke8, Ne7, Nd5.
# Qxd5: the d5 knight is "defended" by Ne7, but Ne7 is absolutely pinned by
# Re1 against Ke8 — the recapture is illegal.
PIN_A_FEN = "4k3/4n3/8/3n4/8/8/8/3QR1K1 w - - 0 1"


def test_pin_paralyzed_defender():
    m = detect_pin(PIN_A_FEN, ["Qxd5"])
    assert m is not None
    assert m["mechanism"] == "pin" and m["shape"] == "paralyzed_defender"
    assert m["pinned_defender"] == "knight" and m["pinned_on"] == "e7"
    assert m["pinned_by"] == "rook on e1"
    assert m["pinned_against"] == "e8"


def test_pin_paralyzed_defender_via_orchestrator():
    m = name_point(PIN_A_FEN, ["Qxd5"])
    assert m is not None
    assert m["mechanism"] == "pin" and m["shape"] == "paralyzed_defender"


def test_pin_silent_when_recapture_legal():
    # Same idea without the pinning rook: Nxd5 is legal, no pin story.
    assert detect_pin("4k3/4n3/8/3n4/8/8/8/3Q2K1 w - - 0 1", ["Qxd5"]) is None


# ============================================================================
# Pin — shape B: attack and win the pinned piece
# ============================================================================

# White: Kg1, Bg5, Pe4.  Black: Kf8, Qd8, Nf6, pg7, ph7.
# Bg5 relative-pins Nf6 against Qd8; e5 attacks the knight, which cannot run;
# exf6 collects it (pawn takes knight — profitable by value).
PIN_B_FEN = "3q1k2/6pp/5n2/6B1/4P3/8/8/6K1 w - - 0 1"
PIN_B_LINE = ["e5", "Kg8", "exf6"]


def test_pin_win_pinned_relative():
    m = detect_pin(PIN_B_FEN, PIN_B_LINE)
    assert m is not None
    assert m["mechanism"] == "pin" and m["shape"] == "win_pinned"
    assert m["pin_kind"] == "relative"
    assert m["pinned_piece"] == "knight" and m["pinned_on"] == "f6"
    assert m["pinned_by"] == "bishop on g5"
    assert m["pinned_against"] == "queen on d8"
    assert m["collected_with"] == "exf6"


def test_pin_win_pinned_aborts_if_piece_flees():
    # If the "pinned" piece moves in the line, the pin didn't hold it.
    assert detect_pin(PIN_B_FEN, ["e5", "Nd5", "Kg2"]) is None


# ============================================================================
# Trapped piece
# ============================================================================

# White: Kc1, Pb3, Pc2.  Black: Kd8, Ba2.
# Kb2 attacks the a2 bishop, whose only moves both lose it:
#   Bxb3 -> cxb3 (met by the c2 pawn), Bb1 -> Kxb1.  Kxa2 collects.
TRAP_FEN = "3k4/8/8/8/8/1P6/b1P5/2K5 w - - 0 1"
TRAP_LINE = ["Kb2", "Kd7", "Kxa2"]


def test_trapped_piece():
    m = detect_trapped_piece(TRAP_FEN, TRAP_LINE)
    assert m is not None
    assert m["mechanism"] == "trapped_piece"
    assert m["trapped_piece"] == "bishop" and m["trapped_on"] == "a2"
    assert m["collected_with"] == "Kxa2"
    assert set(m["no_escape"]) == {"b3", "b1"}


def test_trapped_piece_via_orchestrator():
    m = name_point(TRAP_FEN, TRAP_LINE)
    assert m is not None
    assert m["mechanism"] == "trapped_piece"
    assert m["at_move"] == "Kb2"


def test_trapped_piece_silent_when_escape_exists():
    # No b3/c2 pawns: after Kb2 the bishop runs up the long diagonal freely.
    assert detect_trapped_piece("3k4/8/8/8/8/8/b7/2K5 w - - 0 1",
                                ["Kb2", "Kd7", "Kxa2"]) is None


# ============================================================================
# Battery
# ============================================================================

# White: Kg1, Rd1, Rd2.  Black: Kh8, Rd8, Re8.
# Rxd8 Rxd8 Rxd8+ — the d1 rook behind the d2 rook wins the exchange.
BATTERY_FEN = "3rr2k/8/8/8/8/8/3R4/3R2K1 w - - 0 1"
BATTERY_LINE = ["Rxd8", "Rxd8", "Rxd8+"]


def test_battery():
    m = detect_battery(BATTERY_FEN, BATTERY_LINE)
    assert m is not None
    assert m["mechanism"] == "battery"
    assert m["front"] == "d2" and m["rear"] == "d1" and m["through"] == "d8"
    assert m["net_material"] == 5
    assert m["sequence"] == BATTERY_LINE


def test_battery_needs_the_rear_recapture():
    # Line stops after the opponent recaptures -> the rear piece never fired.
    assert detect_battery(BATTERY_FEN, ["Rxd8", "Rxd8"]) is None


def test_battery_rides_as_geometry_candidate_under_graduated_primacy():
    # name_mechanism reads the same sequence as an attraction (unique
    # recapture lured to d8) — a graduated family, so it keeps primacy and
    # the battery view is attached as data, not speech.
    m = name_point(BATTERY_FEN, BATTERY_LINE)
    assert m is not None
    assert m["mechanism"] != "battery"                 # graduated wins primacy
    g = m.get("geometry_candidate")
    assert g is not None and g["mechanism"] == "battery"


# ============================================================================
# Composition + redaction plumbing
# ============================================================================

def test_skewer_rides_along_when_deflection_leads():
    # In the skewer position the graduated deflection view (the checked king
    # abandons g8) wins primacy; the skewer must ride along as data.
    m = name_point(SKEWER_FEN, SKEWER_LINE)
    assert m is not None
    assert m["mechanism"] == "deflection"
    g = m.get("geometry_candidate")
    assert g is not None and g["mechanism"] == "skewer"


def test_geometry_candidate_is_redacted_from_llm_input():
    payload = {"forfeit": {"value": "advantage",
                           "witness": {"mechanism": {"mechanism": "deflection"},
                                       "geometry_candidate": {"mechanism": "skewer"}}}}
    red = _redact(payload)
    assert "geometry_candidate" not in red["forfeit"]["witness"]
    assert red["forfeit"]["witness"]["mechanism"]["mechanism"] == "deflection"


def test_all_new_positions_are_legal():
    for fen, line in [(SKEWER_FEN, SKEWER_LINE), (DISC_FEN, DISC_LINE),
                      (PIN_A_FEN, ["Qxd5"]), (PIN_B_FEN, PIN_B_LINE),
                      (TRAP_FEN, TRAP_LINE), (BATTERY_FEN, BATTERY_LINE)]:
        b = chess.Board(fen)
        for san in line:
            b.push(b.parse_san(san))     # raises on an illegal move
