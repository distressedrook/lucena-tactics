"""Differential harness — the old-vs-new gate for the engine-slim migration.

Runs the OLD implementation (lucena_engine, Rust board era — frozen during the
migration) and the NEW implementation (lucena_core / src rewrites, python-chess)
over a seeded, deterministic corpus slice and diffs the outputs. A rewrite may
not replace its original until its driver reports zero diffs (or every diff has
been explained and adjudicated like a ruling — see docs/MIGRATION.md).

Positions come from lichess_db_puzzle.csv: the raw FEN plus the position after
the puzzle's setup move (capture-dense, tactically loaded — exactly where SEE
and the detectors disagree if they're going to).

Usage:
    .venv/bin/python research/experiments/differential.py see [--n 500] [--seed 7]
    .venv/bin/python research/experiments/differential.py see --self-check   # old vs old, must be 0 diffs

Drivers accumulate per phase (see docs/MIGRATION.md): see (P1), positional (P2),
census (P4), line_tree (P5). A driver whose new side isn't built yet fails with
a clear message rather than pretending.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import chess

HERE = Path(__file__).resolve().parent
PUZZLE_CSV = HERE / "lichess_db_puzzle.csv"


# ---------------------------------------------------------------- positions
def sample_positions(n: int, seed: int) -> list[str]:
    """Seeded FEN slice: each sampled puzzle contributes its raw FEN and the
    position after the setup move (the first move of `Moves`, played by the
    opponent — the actual puzzle position)."""
    rows: list[tuple[str, str]] = []
    with open(PUZZLE_CSV, newline="") as f:
        for row in csv.DictReader(f):
            rows.append((row["FEN"], row["Moves"].split()[0] if row["Moves"] else ""))
    rng = random.Random(seed)
    picked = rng.sample(rows, min(n, len(rows)))
    fens: list[str] = []
    for fen, setup in picked:
        fens.append(fen)
        if setup:
            b = chess.Board(fen)
            try:
                b.push_uci(setup)
                fens.append(b.fen())
            except ValueError:
                pass
    return fens


# ---------------------------------------------------------------- runner
def run_diff(name: str, cases: list, old_fn, new_fn, out_dir: Path) -> int:
    """Run both sides over `cases`; write mismatches to <name>_diffs.jsonl and
    print a summary. Returns the number of diffs (0 = gate passes)."""
    diffs = []
    errors = 0
    for i, case in enumerate(cases):
        try:
            old = old_fn(case)
        except Exception as e:              # an old-side crash is itself a finding
            old = f"OLD_ERROR:{type(e).__name__}:{e}"
            errors += 1
        try:
            new = new_fn(case)
        except Exception as e:
            new = f"NEW_ERROR:{type(e).__name__}:{e}"
            errors += 1
        if old != new:
            diffs.append({"case": case, "old": old, "new": new})
        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(cases)} … {len(diffs)} diffs", file=sys.stderr)
    out = out_dir / f"{name}_diffs.jsonl"
    with open(out, "w") as f:
        for d in diffs:
            f.write(json.dumps(d) + "\n")
    print(f"[{name}] {len(cases)} cases, {len(diffs)} diffs, {errors} errors "
          f"-> {out if diffs else 'gate PASSES'}")
    return len(diffs)


# ---------------------------------------------------------------- drivers
def _old_see():
    from lucena_engine import Board as OldBoard      # Rust board, frozen original

    def f(case):
        fen, uci = case
        return OldBoard(fen).see(uci)
    return f


def _new_see():
    try:
        from lucena_core import see                  # Phase 1 deliverable
    except ImportError:
        sys.exit("lucena_core.see is not built yet (Phase 1) — "
                 "run with --self-check to verify harness plumbing only.")

    def f(case):
        fen, uci = case
        return see(fen, uci)
    return f


def driver_see(fens: list[str], self_check: bool):
    """Cases: every legal capture in every sampled position (SEE's domain)."""
    cases = []
    for fen in fens:
        b = chess.Board(fen)
        for mv in b.legal_moves:
            if b.is_capture(mv):
                cases.append((fen, mv.uci()))
    old = _old_see()
    new = _old_see() if self_check else _new_see()
    return "see", cases, old, new


def driver_positional(fens, self_check):
    sys.exit("positional driver lands in Phase 2")


def driver_census(fens, self_check):
    sys.exit("census driver lands in Phase 4")


def driver_line_tree(fens, self_check):
    sys.exit("line_tree driver lands in Phase 5")


DRIVERS = {"see": driver_see, "positional": driver_positional,
           "census": driver_census, "line_tree": driver_line_tree}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("driver", choices=sorted(DRIVERS))
    ap.add_argument("--n", type=int, default=500, help="puzzles to sample (default 500)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--self-check", action="store_true",
                    help="run old vs old — proves the plumbing, must be 0 diffs")
    args = ap.parse_args()

    fens = sample_positions(args.n, args.seed)
    print(f"sampled {len(fens)} positions (n={args.n}, seed={args.seed})")
    name, cases, old_fn, new_fn = DRIVERS[args.driver](fens, args.self_check)
    if args.self_check:
        name += "_selfcheck"
    return 1 if run_diff(name, cases, old_fn, new_fn, HERE) else 0


if __name__ == "__main__":
    sys.exit(main())
