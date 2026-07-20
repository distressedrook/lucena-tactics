"""Layer 2/3 — the two-axis fact sheet.

Every mistake decomposes along two independent axes:
  forfeit — what the solution won that the played move didn't (S-line property)
  error   — what the played move actively did wrong, or NONE (M-line property)

Every slot carries a `witness`: the probe/predicate evidence that regenerates
it. The lexicalizer may only assert what a slot contains; anything else is a
hallucination by construction and the verifier will catch it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import chess

from .mechanism import (name_mechanism, name_point, confirm_fork,
                        confirm_attraction, confirm_hanging)
from .probes import Probes
from .predicates import annotate_line, predset, best_material_win

PREMISE_GAP = 10.0      # win% gap for the solution to count as unique
MISTAKE_DWP = -12.0     # win% drop for the played move to count as a mistake


@dataclass
class Slot:
    value: str
    witness: dict = field(default_factory=dict)


@dataclass
class FactSheet:
    status: str                     # ok | not_a_mistake | premise_not_unique | premise_engine_disagrees | illegal
    fen: str = ""
    solution: str = ""
    played: str = ""
    forfeit: Slot | None = None     # what S wins: mate_in_N | wins_<piece> | promotion | decisive_threat | advantage
    error: Slot | None = None       # commission: hung | allowed_forcing_reply | wrong_piece | move_order | none
    refutation: Slot | None = None  # opponent's punishing line after M
    delta: Slot | None = None       # win% swing
    salvage: Slot | None = None     # tactic_alive | position_lost
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def build(probes: Probes, fen: str, solution_san: str, played_san: str) -> FactSheet:
    legal, err = probes.validate(fen)
    if not legal:
        return FactSheet(status="illegal", fen=fen, note=err)

    # -- premise gate: is the solution actually best and unique? ---------
    root = probes.analyze(fen, multipv=3)
    if not root or root[0].san[0] != solution_san:
        return FactSheet(status="premise_engine_disagrees", fen=fen,
                         solution=solution_san, played=played_san,
                         note=f"engine best is {root[0].san[0] if root else '?'}")
    gap = root[0].win_pct - root[1].win_pct if len(root) > 1 else 100.0
    if gap < PREMISE_GAP:
        return FactSheet(status="premise_not_unique", fen=fen,
                         solution=solution_san, played=played_san,
                         note=f"second-best move is within {gap:.1f} win%")

    # -- is the played move actually bad? --------------------------------
    dwp, refut_pv, m_cp, m_win = probes.evaluate(fen, played_san)
    if dwp > MISTAKE_DWP:
        return FactSheet(status="not_a_mistake", fen=fen,
                         solution=solution_san, played=played_san,
                         delta=Slot(f"{dwp:+.1f} win%", {"probe": "Evaluate", "dwp": dwp}),
                         note="the played move holds the position; the puzzle solution is "
                              "stronger but this is not a serious error")

    # -- branch annotation ------------------------------------------------
    s_pv = root[0].san
    s_ann = annotate_line(fen, s_pv)
    b = chess.Board(fen)
    b.push(b.parse_san(played_san))
    m_refut_ann = annotate_line(b.fen(), refut_pv)
    m_ann = annotate_line(fen, [played_san] + refut_pv)
    diff = predset(s_ann) - predset(m_ann)

    fs = FactSheet(status="ok", fen=fen, solution=solution_san, played=played_san)
    fs.delta = Slot(f"{dwp:+.1f} win%", {"probe": "Evaluate", "dwp": round(dwp, 1),
                                         "eval_after_cp": m_cp})

    # -- forfeit axis (S-line): severity-ordered --------------------------
    # Mate may lie beyond the root PV horizon; probe the S-branch directly
    # at a deeper budget — the forfeit is the headline, worth the extra nodes.
    s_end_fen, s_cp, s_mate_in, _, s_deep_pv = probes.explore(
        fen, [solution_san], nodes=4_000_000)
    forces_mate = ("own", "mate") in diff or s_mate_in != 0 or abs(s_cp) >= 1000
    if forces_mate:
        if ("own", "mate") in diff:
            mate_ply = next(i for i, p in enumerate(s_ann) if p["mate"])
            wit = {"predicate": "mate", "line": [p["san"] for p in s_ann[: mate_ply + 1]],
                   "checks": [p["san"] for p in s_ann[: mate_ply + 1] if p["check"]]}
            fs.forfeit = Slot(f"mate_in_{mate_ply // 2 + 1}", wit)
        else:
            fs.forfeit = Slot("forced_mate",
                              {"probe": "ExploreLine(solution)", "mate_in": s_mate_in,
                               "eval_cp": s_cp, "line": [solution_san] + s_deep_pv[:5]})
    elif root[0].cp >= 500:
        # Overwhelming but mate not provable at probe depth: the forfeit is
        # the attack itself, not the incidental material the PV happens to win.
        fs.forfeit = Slot("winning_attack",
                          {"probe": "Analyze", "eval_cp": root[0].cp,
                           "win_pct": round(root[0].win_pct, 1), "line": s_pv[:6]})
    elif (piece := best_material_win(diff)) is not None:
        # (ruling: gross vs net — case 0L0Sw/f5) A capture that gets recaptured
        # is a trade, not a win. Claim the piece only if the NET material flow
        # of the solution line actually keeps it; otherwise the forfeit is the
        # resulting advantage, with the trade line as witness. An unsound slot
        # is an invitation for the lexicalizer to hallucinate ("a clean piece up").
        VAL = {"pawn": 1, "knight": 3, "bishop": 3, "rook": 5, "queen": 9}
        net = 0
        for i, p in enumerate(s_ann):
            if p.get("capture"):
                v = VAL.get(p.get("captured", ""), 0)
                net += v if i % 2 == 0 else -v
        if net >= VAL[piece] - 1:
            fs.forfeit = Slot(f"wins_{piece}",
                              {"predicate": f"wins_{piece}", "line": s_pv[:6],
                               "net_material": net, "eval_cp": root[0].cp})
        else:
            fs.forfeit = Slot("advantage",
                              {"probe": "Analyze", "eval_cp": root[0].cp,
                               "net_material": net, "line": s_pv[:6],
                               "note": "material is traded, not won outright; "
                                       "the profit is the resulting position"})
    elif ("own", "promotes") in diff or ("own", "pawn_advanced") in diff:
        fs.forfeit = Slot("promotion", {"predicate": "pawn_play", "line": s_pv[:6]})
    else:
        end_fen, _, _, _, _ = probes.explore(fen, [solution_san])
        threat = probes.threat_if_pass(end_fen)
        if threat and threat.is_mate:
            fs.forfeit = Slot("decisive_threat",
                              {"probe": "null_move", "threat_pv": threat.pv})
        else:
            # Root PV can be truncated; prefer the deep S-branch continuation.
            line = s_pv[:6] if len(s_pv) >= 3 else [solution_san] + s_deep_pv[:5]
            fs.forfeit = Slot("advantage",
                              {"probe": "Analyze+ExploreLine", "eval_cp": root[0].cp,
                               "line": line})

    # -- error axis (M-line): what the move actively did wrong ------------
    m_mv = chess.Board(fen).parse_san(played_san)
    s_mv = chess.Board(fen).parse_san(solution_san)
    if m_refut_ann and m_refut_ann[0]["capture"] \
            and m_refut_ann[0]["to"] == chess.square_name(m_mv.to_square):
        fs.error = Slot("hung",
                        {"predicate": "refutation_captures",
                         "capture": m_refut_ann[0]["san"],
                         "square": m_refut_ann[0]["to"]})
    elif s_mv.to_square == m_mv.to_square:
        fs.error = Slot("wrong_piece",
                        {"predicate": "shared_target",
                         "square": chess.square_name(s_mv.to_square)})
    elif played_san in [p["san"] for p in s_ann][1:]:
        fs.error = Slot("move_order",
                        {"predicate": "appears_later_in_solution",
                         "solution_line": s_pv[:6]})
    elif m_refut_ann and any(p["mate"] or p["check"] for p in m_refut_ann[:2]):
        fs.error = Slot("allowed_forcing_reply",
                        {"predicate": "refutation_forcing",
                         "reply": [p["san"] for p in m_refut_ann[:2]]})
    else:
        fs.error = Slot("none",
                        {"predicate": "no_active_flaw",
                         "note": "the move is passively reasonable; the failure is pure omission"})

    fs.refutation = Slot(" ".join(refut_pv[:6]) or "(quiet)",
                         {"probe": "Evaluate.refutation_pv", "pv": refut_pv[:6]})

    # -- mechanism: name the point of the tactic, if geometry proves one ---
    # Graduation gate: only mechanisms whose precision has been validated are
    # ever spoken. Candidates below the bar are stored but not lexicalized.
    # Fork additionally requires the engine counterfactual (no defense saves
    # both prongs) — presence is geometry; the point is causality.
    GRADUATED = {"mating_net", "back_rank_mate", "smothered_mate", "fork"}
    deep_line = s_pv if len(s_pv) >= 3 else [solution_san] + s_deep_pv
    mech = name_point(fen, deep_line)
    if mech is not None:
        if mech["mechanism"] == "fork" and not confirm_fork(probes, fen, deep_line, mech):
            mech["confirmed"] = False
        if mech["mechanism"] == "hanging_piece" and not confirm_hanging(probes, fen, deep_line, mech):
            mech["confirmed"] = False      # ruling #11: compelled consolidation, stay silent
        if mech["mechanism"] == "attraction" and "forcing_move" in mech:
            refut = confirm_attraction(probes, fen, deep_line, mech)
            if refut is None:
                mech["confirmed"] = False      # a sound decline exists — not lured
            else:
                mech["declining_loses"] = refut  # the coach's "otherwise..." sentence
                # (adjudication ruling, case 01Mlb): when the compulsion derives
                # from a MATE threat, nothing was lured — the defender paid
                # ransom, choosing the cheapest tribute. Cause outranks
                # execution: primacy transfers to the threat; the capture is
                # the cash-out, attraction stays as the execution view.
                # refinement (0PY6y vs 01Mlb): the boundary is BAIT. If the
                # compelled reply CAPTURED our offered piece, value was
                # extracted at the arrival — attraction stands. If it merely
                # interposed/stepped under a mate threat, it paid ransom.
                bait_taken = False
                try:
                    import chess as _c
                    _b = _c.Board(fen)
                    idx = deep_line.index(mech["forcing_move"])
                    for s in deep_line[:idx + 1]:
                        _b.push(_b.parse_san(s))
                    _mv = _b.parse_san(deep_line[idx + 1])
                    bait_taken = _b.is_capture(_mv)
                except (ValueError, IndexError):
                    pass
                if (not bait_taken) and any(abs(w["eval_cp"]) >= 1000 for w in refut.values()):
                    mech["also"] = ["attraction"] + mech.get("also", [])
                    mech["mechanism"] = "mate_threat"
                    mech["resolution"] = "bought_off"
                    mech["concession"] = mech.get("lured_piece", "material")
        if mech["mechanism"] in GRADUATED and mech.get("confirmed", True):
            fs.forfeit.witness["mechanism"] = mech
        else:
            fs.forfeit.witness["mechanism_candidate"] = mech   # data, not speech

    # -- salvage: what is left after M? Three states, from our POV --------
    m_lines = probes.analyze(b.fen(), multipv=1)
    our_cp = -m_lines[0].cp if m_lines else 0   # engine eval is opponent-POV
    if our_cp >= 150:
        salv = "still_winning"
    elif our_cp >= -100:
        salv = "advantage_gone"                 # roughly equal now
    else:
        salv = "position_lost"
    fs.salvage = Slot(salv, {"probe": "Analyze(after_played)", "our_pov_cp": our_cp})
    return fs
