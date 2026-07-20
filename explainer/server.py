"""The product endpoint: user fails a puzzle -> clicks "why" -> grounded answer.

    POST /why  {"fen": ..., "solution": ..., "played": ...}   (moves in SAN)

Response: prose + the full fact sheet with witnesses, so the client can render
board arrows/highlights from the same data the prose was generated from.

Run:  uvicorn explainer.server:app --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .factsheet import build
from .lexicalize import explain
from .probes import Probes

app = FastAPI(title="chess-lab explainer")
probes = Probes()


class WhyRequest(BaseModel):
    fen: str
    solution: str   # SAN
    played: str     # SAN — the user's failed attempt


@app.post("/why")
def why(req: WhyRequest) -> dict:
    fs = build(probes, req.fen, req.solution, req.played)
    out = explain(fs)
    return {
        "prose": out["prose"],
        "source": out["source"],
        "verified": out["verified"],
        "status": fs.status,
        "fact_sheet": fs.to_dict(),
    }


@app.get("/health")
def health() -> dict:
    legal, _ = probes.validate("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    return {"ok": legal}
