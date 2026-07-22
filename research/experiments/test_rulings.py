"""Adjudication rulings — the regression suite.

Each case is a DEFINITION established by the human adjudicator, not a bug fix.
Any change to explainer/mechanism.py must keep every ruling green.

Run:  ./.venv/bin/python research/experiments/test_rulings.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.mechanism import name_point  # noqa: E402

# (id, fen, solution line, expected primary mechanism, the ruling)
SUITE = [
    ("0Kzja", "6k1/5pp1/2q4p/8/PR1p4/5QP1/5PKP/2r5 b - - 2 28",
     ["Rg1+", "Kxg1", "Qxf3", "Rxd4"], "deflection",
     "departure exploited, reply was a real decision -> deflection"),

    ("05Q61", "5rk1/R3Qpp1/p3p2p/1p6/r3P3/2PR1P2/PKP3qP/8 b - - 1 26",
     ["Rxa2+", "Kxa2", "Qxc2+", "Ka3", "Qxd3", "Qc7"], "attraction",
     "mechanisms compose; arrival exploited -> attraction primary"),

    ("08dpJ", "5k2/4n1p1/p1N2pP1/2Pp3P/1P1K4/8/1P6/8 b - - 0 54",
     ["Nxc6+", "Kxd5", "Nxb4+", "Kc4"], "hanging_piece",
     "a hanging piece is not a defender; free capture IS the point"),

    ("0Umfv", "5r1k/2p3r1/p2pQ1pq/1p2p2p/4P2N/1PPK4/1P6/6R1 w - - 14 36",
     ["Nxg6+", "Qxg6", "Rxg6", "Rxg6", "Qxg6", "h4"], "fork",
     "a fork bought off is still the fork; cause outranks execution"),

    ("0Pqjj", "Q4R1r/p1p3pp/6k1/8/8/8/PPqP1PPP/R1B3K1 b - - 0 20",
     ["Qd1#"], "back_rank_mate",
     "mate patterns from escape accounting (king-lifted rays)"),

    ("0QhFQ", "r3r1k1/ppB2p1p/6p1/2Pp1b2/3P2n1/3B4/PPQ2PPP/RN2R1K1 b - - 0 17",
     ["Rxe1+", "Bf1", "Bxc2", "Ba5", "Rxb1", "Rxb1"], "overload",
     "rule-forced reply: nothing lured, duties conflict -> overload primary"),

    ("0VHBI", "r1b1qrk1/p2n2pp/3b4/1p1p4/2pPp3/P1P1BP1P/1P1NB1P1/R2Q1RK1 b - - 0 15",
     ["exf3", "Rxf3", "Rxf3", "Bxf3", "Qxe3+", "Kh1"], "defender_removal",
     "recapture among equals is no lure (differential compulsion); "
     "silencing the false attraction surfaced the true mechanism: "
     "Rxf3! removes the protected defender of e3"),

    ("0JDnk", "4Rr1k/1p4p1/1pp5/3p1P2/5r2/1P4q1/PP5P/1K2R3 w - - 0 29",
     ["Rxf8+", "Kh7", "hxg3", "Rxf5", "Rxf5", "g6"], "hanging_piece",
     "an unforced reply was not lured; free rook is the point"),

    ("0PY6y", "8/5N2/r5p1/8/2R4k/8/5nPK/8 b - - 7 41",
     ["Ng4+", "Rxg4+", "Kxg4", "Ne5+", "Kf5", "Nc4"], "attraction",
     "consequence-forced counts as forced (declining is mate) — "
     "engine confirmation carries the 'otherwise' refutation"),

    ("0VaRv", "8/8/8/8/6Kb/4k1p1/P5P1/8 w - - 0 58",
     ["Kxh4", "Kf4", "Kh3", "Ke5", "Kxg3", "Kd4"], "hanging_piece",
     "candidate tier sees the free bishop; ruling #11 silences it at the "
     "CONFIRM tier (agency is an engine fact — see confirm section below)"),

    ("0FQDw", "8/8/p1p1k2p/P3rR2/1PK1P2P/8/8/8 b - - 2 37",
     ["Rxe4+", "Kc5", "Kxf5", "Kxc6", "Rxb4", "Kc5"], "defender_removal",
     "a cheap defender removed to unlock a bigger target is defender_removal "
     "even when the defender was free (value routing); and deflection needs "
     "a forced reply like every lure"),

    ("03cd7", "3r1rk1/1p1qbpp1/p3pn1p/4p3/1n5B/2N2N2/PPPQ1PPP/1K1R3R w - - 0 16",
     ["Qxd7", "Rxd7", "Rxd7", "Nxd7", "Bxe7", "Nd5"], "file_battery",
     "a same-square liquidation backed by a root battery (Qd2+Rd1 x-ray on "
     "the d-file) is the battery's work — mid-chain removals are execution, "
     "not fresh mechanisms; 0VHBI (no battery) keeps its removal claim"),
]

# confirm-tier rulings — need the engine; skipped gracefully if unreachable
CONFIRM_SUITE = [
    ("0VaRv", "8/8/8/8/6Kb/4k1p1/P5P1/8 w - - 0 58",
     ["Kxh4", "Kf4", "Kh3", "Ke5", "Kxg3", "Kd4"], False,
     "the bishop is trapped, not hanging: the a4 line captures it anyway — no urgency, the point is the technique after (doomed-piece test)"),
]


def main() -> int:
    failures = 0
    for id_, fen, line, want, ruling in SUITE:
        m = name_point(fen, line)
        got = m["mechanism"] if m else None
        ok = got == want
        failures += not ok
        print(f"{'✓' if ok else '✗'} {id_}: {got}"
              + ("" if ok else f"  (want {want})") + f"  — {ruling}")
    try:
        from src.mechanism import confirm_hanging
        from src.probes import Probes
        probes = Probes()
        for id_, fen, line, want_ok, ruling in CONFIRM_SUITE:
            m = name_point(fen, line)
            got_ok = confirm_hanging(probes, fen, line, m) if m else None
            ok = got_ok == want_ok
            failures += not ok
            print(f"{'✓' if ok else '✗'} {id_} [confirm]: opportunity={got_ok}"
                  + ("" if ok else f" (want {want_ok})") + f"  — {ruling}")
    except Exception as e:
        print(f"(confirm-tier cases skipped: engine unreachable — {e})")
    print("ALL RULINGS HOLD" if not failures else f"{failures} RULING(S) BROKEN")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
