"""Layer 1 — mechanical ply-level predicates.

Every function here is a total, decidable function of board geometry
(python-chess: notation and legality only, never evaluation). These are the
primitives that make explanations verifiable: any claim the system emits must
bottom out in one of these or in an engine probe.
"""
from __future__ import annotations

import chess


def annotate_line(fen: str, san_moves: list[str]) -> list[dict]:
    """Stamp each ply of a SAN line with mechanical predicates."""
    b = chess.Board(fen)
    out: list[dict] = []
    for san in san_moves:
        try:
            mv = b.parse_san(san)
        except ValueError:
            break
        p: dict = {"san": san, "to": chess.square_name(mv.to_square)}
        p["capture"] = b.is_capture(mv)
        if p["capture"]:
            cap = b.piece_at(mv.to_square)
            p["captured"] = chess.piece_name(cap.piece_type) if cap else "pawn"
        piece = b.piece_at(mv.from_square)
        p["piece"] = chess.piece_name(piece.piece_type) if piece else "?"
        p["check"] = b.gives_check(mv)
        p["promotion"] = mv.promotion is not None
        if piece and piece.piece_type == chess.PAWN:
            rank = chess.square_rank(mv.to_square)
            rel = rank if piece.color == chess.WHITE else 7 - rank
            p["pawn_advanced"] = rel >= 5
        b.push(mv)
        if p["check"]:
            checkers = b.checkers()
            p["discovered"] = bool(checkers and mv.to_square not in checkers)
            p["double_check"] = len(checkers) > 1
        p["mate"] = b.is_checkmate()
        p["forced_reply"] = (not p["mate"]) and b.legal_moves.count() == 1
        out.append(p)
    return out


def predset(ann: list[dict]) -> set[tuple[str, str]]:
    """Bag of mechanism-relevant predicates for branch diffing.

    'own' = the side whose move is being explained (even plies).
    """
    s: set[tuple[str, str]] = set()
    for i, p in enumerate(ann):
        who = "own" if i % 2 == 0 else "opp"
        if p["check"]:
            s.add((who, "check"))
        if p.get("discovered"):
            s.add((who, "discovered_check"))
        if p.get("double_check"):
            s.add((who, "double_check"))
        if p["mate"]:
            s.add((who, "mate"))
        if p["capture"] and who == "own":
            s.add(("own", "wins_" + p.get("captured", "?")))
        if p.get("forced_reply") and who == "own":
            s.add(("own", "forcing"))
        if p.get("promotion") and who == "own":
            s.add(("own", "promotes"))
        if p.get("pawn_advanced") and who == "own":
            s.add(("own", "pawn_advanced"))
    return s


PIECE_ORDER = ["queen", "rook", "bishop", "knight", "pawn"]


def best_material_win(diff: set[tuple[str, str]]) -> str | None:
    """Largest piece the solution line wins that the played line doesn't."""
    won = {k[len("wins_"):] for w, k in diff if w == "own" and k.startswith("wins_")}
    for piece in PIECE_ORDER:
        if piece in won:
            return piece
    return None
