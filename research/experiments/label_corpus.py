"""Corpus-scale mechanism labeling — engine-free, the whole Lichess puzzle DB.

For every puzzle: reconstruct the position, walk the solution line through
name_point (geometric theorems + 15 adjudicated rulings, zero engine calls),
and emit a compact labeled row. Output serves three purposes:
  1. the largest mechanism-labeled chess dataset in existence
  2. stage one of the precompute cache
  3. the unnamed residual = raw material for vocabulary discovery (clustering)

Run:  ./.venv/bin/python experiments/label_corpus.py --csv <puzzles.csv> \
          --out experiments/corpus_labels.jsonl.gz [--limit N] [--workers 8]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chess  # noqa: E402

from explainer.mechanism import name_point  # noqa: E402

KEEP_WITNESS = ("at_move", "target", "target_piece", "forcing_move", "follow_up",
                "fork_move", "fork_square", "targets", "collected_with", "resolution",
                "removed_defender", "removed_on", "removed_free", "with_check",
                "deflected_defender", "deflected_from", "lured_to", "lured_piece",
                "lured_from", "mate_move", "king", "checkers", "hanging_piece",
                "hanging_on", "second_duty", "conscripted_duty", "net_material",
                "profit", "concession", "battery", "liquidation_square",
                "in_between", "postponed_capture", "prime_target_escaped")


def label_row(row: dict) -> dict | None:
    try:
        board = chess.Board(row["FEN"])
        ucis = row["Moves"].split()
        board.push(chess.Move.from_uci(ucis[0]))       # opponent's setup move
        fen = board.fen()
        line = []
        b = chess.Board(fen)
        for u in ucis[1:]:
            mv = chess.Move.from_uci(u)
            line.append(b.san(mv))
            b.push(mv)
        m = name_point(fen, line)
        out = {"id": row["PuzzleId"], "r": int(row["Rating"]),
               "themes": row["Themes"], "fen": fen, "line": line,
               "mech": None}
        if m is not None:
            out["mech"] = m["mechanism"]
            if m.get("also"):
                out["also"] = m["also"]
            out["w"] = {k: m[k] for k in KEEP_WITNESS if k in m}
        return out
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="experiments/corpus_labels.jsonl.gz")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    t0 = time.time()
    n = done = named = 0
    with open(args.csv) as f, gzip.open(args.out, "wt") as out, \
            Pool(args.workers) as pool:
        reader = csv.DictReader(f)
        for res in pool.imap_unordered(label_row, reader, chunksize=500):
            n += 1
            if res is not None:
                done += 1
                named += res["mech"] is not None
                out.write(json.dumps(res, separators=(",", ":")) + "\n")
            if n % 100_000 == 0:
                dt = time.time() - t0
                print(f"{n:,} rows | {done:,} ok | {named:,} named "
                      f"({100*named/max(done,1):.0f}%) | {n/dt:,.0f} rows/s",
                      flush=True)
            if args.limit and n >= args.limit:
                break
    dt = time.time() - t0
    print(f"DONE: {n:,} rows in {dt/60:.1f} min | labeled {done:,} | "
          f"named {named:,} ({100*named/max(done,1):.0f}%)", flush=True)


if __name__ == "__main__":
    main()
