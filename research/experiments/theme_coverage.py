"""Per-theme geometric coverage audit — the recall harness for name_point.

Runs the retrospective mechanism layer over Lichess-labeled puzzles and
tabulates, per theme: how often ANY mechanism fires ("named") and how often
the theme's own family is among the fired views ("matched" — primary,
also-views, secondary/execution, riding geometry_candidate, annotations).

This is the detection-completeness scoreboard (2026-07-24: the audit that
drove the gap-filling detectors — pin-as-setting, x-ray, interference,
clearance, windmill, desperado, underpromotion, sacrifice wiring). Recall
first; precision is the adjudication loop's job later.

Run: .venv/bin/python research/experiments/theme_coverage.py [--cap 120]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.mechanism import name_point  # noqa: E402

CSV = Path(__file__).parent / "lichess_db_puzzle.csv"

THEMES = ["fork", "pin", "skewer", "discoveredAttack", "deflection", "attraction",
          "backRankMate", "smotheredMate", "hangingPiece", "trappedPiece",
          "intermezzo", "capturingDefender", "doubleCheck", "interference",
          "clearance", "xRayAttack", "quietMove", "sacrifice", "mateIn2",
          "promotion"]
MAP = {
    "fork": {"fork"}, "pin": {"pin"}, "skewer": {"skewer"},
    "discoveredAttack": {"discovered_attack", "clearance"},
    "deflection": {"deflection"}, "attraction": {"attraction"},
    "backRankMate": {"back_rank_mate"}, "smotheredMate": {"smothered_mate"},
    "hangingPiece": {"hanging_piece"}, "trappedPiece": {"trapped_piece"},
    "intermezzo": {"intermezzo"}, "capturingDefender": {"defender_removal"},
    "doubleCheck": {"discovered_attack", "windmill", "double_check"},
    "interference": {"interference"}, "clearance": {"clearance"},
    "xRayAttack": {"xray", "battery", "skewer", "file_battery"},
    "quietMove": set(), "sacrifice": {"sacrifice"},
    "mateIn2": {"mating_net", "back_rank_mate", "smothered_mate"},
    "promotion": {"underpromotion", "promotion"},
}


def families(m: dict) -> set[str]:
    fams = {m.get("mechanism", "")} | set(m.get("also", []))
    g = m.get("geometry_candidate")
    if g:
        fams |= families(g)
    for key in ("secondary", "execution"):
        sub = m.get(key)
        if isinstance(sub, dict):
            fams.add(sub.get("mechanism", ""))
    for ann in ("sacrifice", "underpromotion", "promotion", "double_check"):
        if m.get(ann):
            fams.add(ann)
    return fams


def judge(fen: str, ucis: list[str]):
    b = chess.Board(fen)
    try:
        b.push_uci(ucis[0])
        start = b.fen()
        sans = []
        for u in ucis[1:]:
            sans.append(b.san(chess.Move.from_uci(u)))
            b.push_uci(u)
    except Exception:
        return None
    try:
        return name_point(start, sans)
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=120)
    ap.add_argument("--scan", type=int, default=250_000)
    args = ap.parse_args()

    quota: dict[str, list] = {t: [] for t in THEMES}
    with open(CSV, newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i > args.scan or all(len(v) >= args.cap for v in quota.values()):
                break
            ths = set(row["Themes"].split())
            for t in THEMES:
                if t in ths and len(quota[t]) < args.cap:
                    quota[t].append((row["FEN"], row["Moves"].split()))

    print(f"{'theme':18} {'n':>4} {'named':>10} {'matched':>10}")
    for t in THEMES:
        n = named = matched = 0
        for fen, moves in quota[t]:
            m = judge(fen, moves)
            if m is False:
                continue
            n += 1
            if m is None:
                continue
            named += 1
            if families(m) & MAP[t]:
                matched += 1
        tag = "  (no family mapped)" if not MAP[t] else ""
        print(f"{t:18} {n:>4} {named:>4} ({100*named//max(n,1):>3}%) {matched:>4} ({100*matched//max(n,1):>3}%){tag}")


if __name__ == "__main__":
    main()
