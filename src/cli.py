"""CLI: python -m explainer.cli <fen> <solution_san> <played_san>"""
import json, sys
from .factsheet import build
from .lexicalize import explain
from .probes import Probes

def main():
    fen, solution, played = sys.argv[1], sys.argv[2], sys.argv[3]
    fs = build(Probes(), fen, solution, played)
    out = explain(fs)
    print(f"[{fs.status} | {out['source']}]")
    print(out["prose"])
    if "--json" in sys.argv:
        print(json.dumps(fs.to_dict(), indent=2, default=str))

if __name__ == "__main__":
    main()
