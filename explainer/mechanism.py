"""Mechanism naming — deriving the *point* of a tactic from geometry.

Not pattern-matching against a motif library: each mechanism is a theorem
about the solution line, checked against board geometry ply by ply. If the
checks pass, the name is earned; the witness carries the full triple so the
claim re-verifies.

Family implemented (the lured/removed-defender group):
  deflection        forcing move; the forced reply is made BY a defender of
                    the target square, which thereby stops defending it
  defender_removal  the first move CAPTURES a defender of the target
  overload          the defender of the target also defends the forcing
                    move's square — it cannot meet both duties
"""
from __future__ import annotations

import chess


def _piece_name(board: chess.Board, sq: int) -> str:
    p = board.piece_at(sq)
    return chess.piece_name(p.piece_type) if p else "?"




def _effective_balance(board: chess.Board) -> int:
    """Material balance from the side-to-move's perspective, counting enemy
    pieces that hang for free as ours-in-waiting. (Ruling #11 refinement,
    cases 0VaRv vs 0JDnk: a raw deficit can be illusory when several enemy
    pieces are en prise — the question is 'after I take what is free, am I
    actually AHEAD?')"""
    v = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
    us = board.turn
    bal = 0
    for sq, p in board.piece_map().items():
        if p.piece_type == chess.KING:
            continue
        if p.color == us:
            bal += v[p.piece_type]
        else:
            bal -= v[p.piece_type]
            if board.attackers(us, sq) and not board.attackers(not us, sq):
                bal += 2 * v[p.piece_type]      # theirs now, ours after the free capture
    return bal


def _battery_toward(board: chess.Board, us: bool, sq: int) -> dict | None:
    """Is there an x-ray battery aimed at sq — a sliding piece attacking sq
    with another of ours BEHIND it on the same ray? (ruling #14, case 03cd7)"""
    for front in board.attackers(us, sq):
        fp = board.piece_at(front)
        if fp is None or fp.piece_type not in (chess.ROOK, chess.QUEEN, chess.BISHOP):
            continue
        df = chess.square_file(front) - chess.square_file(sq)
        dr = chess.square_rank(front) - chess.square_rank(sq)
        step_f = (df > 0) - (df < 0)
        step_r = (dr > 0) - (dr < 0)
        f, r = chess.square_file(front) + step_f, chess.square_rank(front) + step_r
        while 0 <= f <= 7 and 0 <= r <= 7:
            b_sq = chess.square(f, r)
            p = board.piece_at(b_sq)
            if p is not None:
                if p.color == us and p.piece_type in (chess.ROOK, chess.QUEEN, chess.BISHOP):
                    diag = step_f != 0 and step_r != 0
                    ok = (p.piece_type == chess.QUEEN
                          or (p.piece_type == chess.BISHOP and diag)
                          or (p.piece_type == chess.ROOK and not diag))
                    if ok:
                        return {"front": chess.square_name(front),
                                "rear": chess.square_name(b_sq),
                                "through": chess.square_name(sq)}
                break
            f += step_f; r += step_r
    return None


def name_mechanism(fen: str, s_ann: list[dict]) -> dict | None:
    """Given the root FEN and the annotated solution line, name the mechanism.

    Returns {"mechanism": ..., witness fields...} or None (no claim — honest
    silence beats a guessed label).
    """
    if len(s_ann) < 3:
        return None
    s0, s1, s2 = s_ann[0], s_ann[1], s_ann[2]
    if not s2["capture"]:
        return None

    root = chess.Board(fen)
    us = root.turn
    mv0 = root.parse_san(s0["san"])

    # target square: where our follow-up captures
    b1 = root.copy()
    b1.push(mv0)
    try:
        mv1 = b1.parse_san(s1["san"])
    except ValueError:
        return None
    b2 = b1.copy()
    b2.push(mv1)
    try:
        mv2 = b2.parse_san(s2["san"])
    except ValueError:
        return None
    t = mv2.to_square
    if not (s0["check"] or s0["capture"]):
        return None                      # first move must be forcing

    VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
           chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

    # -- attraction: the forced reply lands ON the target square and we
    #    capture the arrived piece profitably (material accounting so a
    #    plain recapture exchange doesn't masquerade as a tactic).
    #    "Forced" is literal: a reply that was a free choice was not lured.
    #    (adjudication case 0JDnk: hxg3 Rxf5 — the rook grabbed a pawn in a
    #    lost position; nothing compelled it. No attraction.)
    if mv1.to_square == t:
        recapturers = [m for m in b1.legal_moves if m.to_square == mv0.to_square
                       and b1.is_capture(m)]
        reply_forced = (
            b1.is_check()                                   # s0 gave check
            or (b1.is_capture(mv1) and mv1.to_square == mv0.to_square
                and len(recapturers) == 1)                  # UNIQUE recapture only
            or b1.legal_moves.count() == 1                  # literally only move
        )
        # (adjudication ruling, case 0VHBI): a recapture chosen among equals is
        # a defensive try, not a lure — Bxf3 loses the same way as Rxf3. The
        # lure needs DIFFERENTIAL compulsion; multiple recapturers void it.
        if not reply_forced:
            return None
        lured = b1.piece_at(mv1.from_square)
        gained = VAL[lured.piece_type] if lured else 0          # piece we capture at t
        gained += VAL[root.piece_at(mv0.to_square).piece_type] if root.piece_at(mv0.to_square) else 0
        lost = VAL[root.piece_at(mv0.from_square).piece_type] if b1.is_capture(mv1) and mv1.to_square == mv0.to_square else 0
        if gained - lost >= 2 and lured is not None:
            return {"mechanism": "attraction",
                    "lured_piece": chess.piece_name(lured.piece_type),
                    "lured_from": chess.square_name(mv1.from_square),
                    "lured_to": chess.square_name(t),
                    "forcing_move": s0["san"], "follow_up": s2["san"],
                    "target": chess.square_name(t),
                    "net_material": gained - lost}
        return None                      # same-square exchange, no tactic claim

    victim_root = root.piece_at(t)
    if victim_root is None or victim_root.color == us:
        return None                      # target didn't exist at root — different tactic
    defenders = root.attackers(not us, t)
    if not defenders:
        return None                      # was hanging already — no defender story

    common = {
        "target": chess.square_name(t),
        "target_piece": chess.piece_name(victim_root.piece_type),
        "forcing_move": s0["san"],
        "follow_up": s2["san"],
        "defenders_at_root": [chess.square_name(d) for d in defenders],
    }

    # -- defender_removal: our first move captured a defender of t ---------
    # (adjudication ruling, case 08dpJ): a hanging piece is not a defender —
    # a defense that costs nothing to remove is fictional. Removal is only a
    # mechanism when the removed piece was protected (a real trade/sacrifice);
    # otherwise the point is simply that the piece was free.
    if s0["capture"] and mv0.to_square in defenders:
        # (adjudication ruling #12, case 0L0Sw): removal proves the collection
        # only when the removed piece was the LAST defender. If others remain,
        # the capture works for some other reason (a pin, an x-ray, a skewer)
        # that this witness does not establish — an unsound proof is worse
        # than silence, because the proof is the product.
        if len(defenders) > 1:
            return None
        protectors = root.attackers(not us, mv0.to_square)
        removed_val = VAL[root.piece_at(mv0.to_square).piece_type]
        target_val = VAL[victim_root.piece_type]
        # (adjudication ruling #13, case 0FQDw): when the removed defender is
        # worth LESS than the target its removal unlocks, the removal is the
        # mechanism — even if the defender was free (being free just makes it
        # better; a check adds tempo). The 08dpJ 'free piece is the point'
        # reading applies only when the removed piece outvalues the target.
        if protectors or removed_val < target_val:
            out = {"mechanism": "defender_removal",
                   "removed_defender": _piece_name(root, mv0.to_square),
                   "removed_on": chess.square_name(mv0.to_square),
                   "removed_free": not bool(protectors),
                   "with_check": s0["check"], **common}
            # (adjudication ruling #15, case 07lKi): the removal's target is
            # the MOST VALUABLE piece the removed defender was guarding —
            # not whichever square the line happens to capture on third.
            # If that prime target escapes, the threat was bought off and
            # the profit is the captured guard itself; the driven piece is
            # the deflection-view of the same event.
            removed_sq = mv0.to_square
            best_sq, best_val = t, target_val
            for sq in root.attacks(removed_sq):
                p = root.piece_at(sq)
                # guarded solely by the removed piece at the root, and
                # attacked NOW — often by the capturer from the guard's own
                # square (Qxb6 re-attacks d8 from b6)
                if (p is not None and p.color != us and sq != removed_sq
                        and b1.attackers(us, sq)
                        and list(root.attackers(not us, sq)) == [removed_sq]
                        and VAL[p.piece_type] > best_val):
                    best_sq, best_val = sq, VAL[p.piece_type]
            if best_sq != t:
                out["target"] = chess.square_name(best_sq)
                out["target_piece"] = chess.piece_name(root.piece_at(best_sq).piece_type)
                out["resolution"] = "bought_off"
                out["prime_target_escaped"] = True
                out["consolation"] = f"{_piece_name(root, t)} on {chess.square_name(t)}"
                out["also"] = ["deflection"]
            return out
        # (adjudication ruling #10): a free PAWN is not a "hanging piece" —
        # if a pawn grab wins, the why is deeper (promotion, structure), and
        # this vocabulary should stay silent rather than claim it.
        if root.piece_at(mv0.to_square).piece_type == chess.PAWN:
            return None
        return {"mechanism": "hanging_piece",
                "hanging_piece": _piece_name(root, mv0.to_square),
                "hanging_on": chess.square_name(mv0.to_square),
                "captured_with": s0["san"],
                "with_check": s0["check"]}

    # -- lured-defender family: one event, several true descriptions -------
    # (adjudication ruling, case 05Q61): mechanisms compose. The same forced
    # reply can be an attraction (arrival exploited), a deflection (departure
    # exploited), and an overload (two duties) AT ONCE. We report all that
    # verify; primacy goes to the arrival when the lured piece is itself hit
    # on its new square, else to the departure. Overload is secondary color.
    if mv1.from_square in defenders:
        # (ruling #1, generalized — case 0FQDw): a free-choice reply was not
        # lured. The forced-reply gate was only on attraction; deflection
        # fabricated a claim from an unforced king stroll. Same gate for all.
        reply_forced = (b1.is_check()
                        or (b1.is_capture(mv1) and mv1.to_square == mv0.to_square)
                        or b1.legal_moves.count() == 1)
        if not reply_forced:
            return None
        still_defends = t in b2.attacks(mv1.to_square)
        if not still_defends:
            # (adjudication ruling, case 0QhFQ): when the defender's reply is
            # RULE-forced (only legal move), nothing was lured — no decision
            # existed to exploit. The story is a duty conflict: the forcing
            # move conscripts the defender into a second mandatory job, and
            # one piece cannot do both. Primary = overload; deflection is the
            # execution view. With a choice (even a bad one), deflection leads.
            rule_forced = b1.legal_moves.count() == 1
            views = ["overload", "deflection"] if rule_forced else ["deflection"]
            out = {"deflected_defender": _piece_name(root, mv1.from_square),
                   "deflected_from": chess.square_name(mv1.from_square),
                   "lured_to": chess.square_name(mv1.to_square), **common}
            if rule_forced:
                out["conscripted_duty"] = (f"blocking on {chess.square_name(mv1.to_square)} "
                                           f"(only legal reply to {s0['san']})")
            # overload view: a TRUE second duty — at the root, the defender
            # also guarded another of its pieces that we attack.
            for sq in root.attacks(mv1.from_square):
                p = root.piece_at(sq)
                if (sq != t and p is not None and p.color != us
                        and root.attackers(us, sq)
                        and len(root.attackers(not us, sq)) == 1):
                    if "overload" not in views:
                        views.append("overload")
                    out["second_duty"] = chess.square_name(sq)
                    break
            # attraction view: the follow-up hits the lured piece where it
            # landed (e.g. Qxc2+ checking the king dragged to a2)
            b3 = b2.copy()
            b3.push(mv2)
            arrival_hit = (s2["check"] and root.piece_at(mv1.from_square).piece_type == chess.KING) \
                or (mv1.to_square in b3.attacks(mv2.to_square))
            if arrival_hit:
                views.insert(0, "attraction")
                out["arrival_exploited_by"] = s2["san"]
            out["mechanism"] = views[0]
            out["also"] = views[1:]
            return out
    return None


# ═══════════════════════════════════════════════════════════════════════
# Mate patterns — why is the final position mate?
# Fully closed computation on the mating position: every king escape is
# accounted for (blocked by own piece / covered by attacker), then the
# accounting is pattern-matched to classical names where the geometry fits.
# ═══════════════════════════════════════════════════════════════════════

def detect_mate_pattern(fen: str, san_line: list[str]) -> dict | None:
    board = chess.Board(fen)
    mate_san = None
    for san in san_line:
        try:
            mv = board.parse_san(san)
        except ValueError:
            return None
        board.push(mv)
        if board.is_checkmate():
            mate_san = san
            break
    if mate_san is None:
        return None

    loser = board.turn
    winner = not loser
    k = board.king(loser)
    checkers = list(board.checkers())

    # coverage must be computed with the king lifted — the king itself blocks
    # sliding rays, hiding squares that become attacked the moment it steps back
    ghost = board.copy()
    ghost.remove_piece_at(k)
    escapes: dict[str, str] = {}
    for sq in chess.SQUARES:
        if chess.square_distance(sq, k) != 1:
            continue
        p = board.piece_at(sq)
        if p and p.color == loser:
            escapes[chess.square_name(sq)] = f"blocked by own {chess.piece_name(p.piece_type)}"
        elif ghost.attackers(winner, sq):
            att = next(iter(ghost.attackers(winner, sq)))
            escapes[chess.square_name(sq)] = (
                f"covered by {chess.piece_name(ghost.piece_at(att).piece_type)} on "
                f"{chess.square_name(att)}")
        else:
            escapes[chess.square_name(sq)] = "unreachable"

    out = {"mechanism": "mating_net", "mate_move": mate_san,
           "checkers": [f"{chess.piece_name(board.piece_at(c).piece_type)} on {chess.square_name(c)}"
                        for c in checkers],
           "king": chess.square_name(k), "escapes": escapes}

    # -- classical names, geometry-gated ----------------------------------
    back = 0 if loser == chess.WHITE else 7
    blocked = [v for v in escapes.values() if v.startswith("blocked")]
    if (chess.square_rank(k) == back and len(checkers) == 1
            and board.piece_at(checkers[0]).piece_type in (chess.ROOK, chess.QUEEN)
            and chess.square_rank(checkers[0]) == back
            and all(v.startswith("blocked") for s, v in escapes.items()
                    if chess.square_rank(chess.parse_square(s)) != back)):
        out["mechanism"] = "back_rank_mate"
    elif (len(checkers) == 1
          and board.piece_at(checkers[0]).piece_type == chess.KNIGHT
          and all(v.startswith("blocked") for v in escapes.values())):
        out["mechanism"] = "smothered_mate"
    return out


# ═══════════════════════════════════════════════════════════════════════
# Fork — one move, two targets, at most one can be saved.
# ═══════════════════════════════════════════════════════════════════════

_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
        chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 99}


def detect_fork(fen: str, san_line: list[str], ply: int = 0) -> dict | None:
    """Does the own move at `ply` (0-indexed, must be even) fork ≥2 targets?"""
    board = chess.Board(fen)
    for san in san_line[:ply]:
        try:
            board.push(board.parse_san(san))
        except ValueError:
            return None
    us = board.turn
    try:
        mv = board.parse_san(san_line[ply])
    except (ValueError, IndexError):
        return None
    board.push(mv)
    s = mv.to_square
    forker = board.piece_at(s)
    if forker is None:
        return None

    # forker must be safe on s: no cheaper attacker; if attacked at all, defended
    atk = board.attackers(not us, s)
    if any(_VAL[board.piece_at(a).piece_type] < _VAL[forker.piece_type] for a in atk):
        return None
    if atk and not board.attackers(us, s):
        return None

    targets = []
    for t in board.attacks(s):
        p = board.piece_at(t)
        if p is None or p.color == us:
            continue
        worth_it = (p.piece_type == chess.KING
                    or _VAL[p.piece_type] > _VAL[forker.piece_type]
                    or not board.attackers(not us, t))
        if worth_it:
            targets.append((t, p.piece_type))
    if len(targets) < 2:
        return None

    # causality: the fork must be USED. Two resolutions qualify —
    #   collected:  a later own ply captures a prong
    #   bought_off: the reply gives a MORE valuable piece for the forker
    #               (0Umfv ruling: Nxg6+ forks K+R; Qxg6 pays the queen to
    #               stop it, Rxg6 collects — the fork extracted the queen)
    target_sqs = {t for t, _ in targets}
    resolution = collected = concession = None
    b2 = board.copy()
    for j, san in enumerate(san_line[ply + 1:], start=ply + 1):
        try:
            m2 = b2.parse_san(san)
        except ValueError:
            break
        if (j - ply) % 2 == 0 and b2.is_capture(m2) and m2.to_square in target_sqs:
            resolution, collected = "collected", san
            break
        if j == ply + 1 and b2.is_capture(m2) and m2.to_square == s:
            payer = b2.piece_at(m2.from_square)
            if payer and _VAL[payer.piece_type] > _VAL[forker.piece_type]:
                # opponent pays a bigger piece for the forker; we must recapture
                nxt = san_line[ply + 2] if len(san_line) > ply + 2 else None
                if nxt:
                    b3 = b2.copy(); b3.push(m2)
                    try:
                        m3 = b3.parse_san(nxt)
                        if b3.is_capture(m3) and m3.to_square == s:
                            resolution = "bought_off"
                            concession = chess.piece_name(payer.piece_type)
                            collected = nxt
                            break
                    except ValueError:
                        pass
        b2.push(m2)
    if resolution is None:
        return None

    if resolution == "bought_off":
        profit = _VAL[chess.PIECE_NAMES.index(concession)] - _VAL[forker.piece_type] \
            if concession in chess.PIECE_NAMES else 0
    else:
        # value of the collected prong
        prong = next((pt for t, pt in targets
                      if chess.square_name(t) in collected), None)
        profit = _VAL[prong] if prong else 0
    out = {"mechanism": "fork", "resolution": resolution, "profit": profit,
           "forker": chess.piece_name(forker.piece_type),
           "fork_move": san_line[ply], "fork_square": chess.square_name(s),
           "targets": [f"{chess.piece_name(pt)} on {chess.square_name(t)}"
                       for t, pt in targets],
           "collected_with": collected}
    if concession:
        out["concession"] = concession
    return out


# ═══════════════════════════════════════════════════════════════════════
# Orchestrator — the single entry point.
# Mate outranks everything (a material mechanism inside a mating line is
# subplot, not point). Otherwise scan each own-move window along the line:
# the mechanism may sit at move two or three of the combination.
# ═══════════════════════════════════════════════════════════════════════

def name_point(fen: str, san_line: list[str]) -> dict | None:
    from .predicates import annotate_line

    mate = detect_mate_pattern(fen, san_line)
    if mate is not None:
        return mate

    board = chess.Board(fen)
    orig_root = chess.Board(fen)
    hanging_candidate = None
    prev_capture_sq = None
    for ply in range(0, max(1, len(san_line) - 2), 2):
        sub_fen = board.fen()
        suffix = san_line[ply:]
        # (adjudication ruling #14, case 03cd7): a window whose first move
        # recaptures on an ongoing liquidation square, with a battery aimed
        # at that square from the ORIGINAL root, is not a fresh mechanism —
        # the battery (x-ray) is the cause; mid-chain "removals" are its
        # execution. Named as candidate vocabulary; never spoken ungraduated.
        if ply > 0 and prev_capture_sq is not None:
            try:
                mv_here = board.parse_san(suffix[0])
                if board.is_capture(mv_here) and mv_here.to_square == prev_capture_sq:
                    bat = _battery_toward(orig_root, orig_root.turn, prev_capture_sq)
                    if bat is not None:
                        return {"mechanism": "file_battery", "at_move": suffix[0],
                                "battery": bat,
                                "liquidation_square": chess.square_name(prev_capture_sq),
                                "note": "doubled pieces win the exchange sequence; "
                                        "x-ray through the front piece"}
            except ValueError:
                pass
        m = name_mechanism(sub_fen, annotate_line(sub_fen, suffix))
        f = detect_fork(sub_fen, suffix, 0)
        # primacy (0Umfv ruling): the CAUSE outranks the follow-through.
        # A fork that forces the reply is the point; a lure narrative built
        # on that forced reply is its execution, kept as a secondary view.
        if f is not None and m is not None:
            # independent views (hanging piece vs fork): bigger profit leads.
            # dependent views (lure built on the fork's forced reply): cause first.
            _V = {"pawn":1,"knight":3,"bishop":3,"rook":5,"queen":9}
            if (m["mechanism"] == "hanging_piece"
                    and _V.get(m.get("hanging_piece"), 0) >= f.get("profit", 0)):
                m["also"] = ["fork"] + m.get("also", [])
                m["secondary"] = {k: v for k, v in f.items()}
                m["at_move"] = suffix[0]
                return m
            f["also"] = [m["mechanism"]] + m.get("also", [])
            f["execution"] = {k: v for k, v in m.items() if k not in ("also",)}
            f["at_move"] = suffix[0]
            return f
        if m is not None:
            m["at_move"] = suffix[0]
            return m
        if f is not None:
            f["at_move"] = suffix[0]
            return f
        # hanging piece (08dpJ ruling: if it hangs, "free" IS the point) —
        # but only as a LAST RESORT and only for the puzzle's first move:
        # a free capture mid-combination is a step, not the story. Record
        # the candidate here; it's returned after the scan finds nothing richer.
        if ply == 0 and hanging_candidate is None:
            try:
                mv = board.parse_san(suffix[0])
                vic = board.piece_at(mv.to_square)
                if (vic is not None and board.is_capture(mv)
                        and vic.piece_type != chess.PAWN     # ruling #10: pawns excluded
                        and not board.attackers(not board.turn, mv.to_square)):
                    hanging_candidate = {
                        "mechanism": "hanging_piece", "at_move": suffix[0],
                        "hanging_piece": chess.piece_name(vic.piece_type),
                        "hanging_on": chess.square_name(mv.to_square),
                        "captured_with": suffix[0],
                        "with_check": board.gives_check(mv)}
            except ValueError:
                break
        # advance two plies — but only through a FORCED reply. Once the
        # opponent had a free choice, the rest of the PV is best-play filler,
        # not the puzzle's content; patterns found there are coincidences.
        try:
            mv_own = board.parse_san(san_line[ply])
            own_to = mv_own.to_square
            prev_capture_sq = own_to if board.is_capture(mv_own) else None
            board.push(mv_own)
            mv_reply = board.parse_san(san_line[ply + 1])
            reply_forced = (board.is_check()
                            or (board.is_capture(mv_reply) and mv_reply.to_square == own_to)
                            or board.legal_moves.count() == 1)
            if not reply_forced:
                break
            board.push(mv_reply)
        except (ValueError, IndexError):
            break
    return hanging_candidate


def confirm_fork(probes, fen: str, san_line: list[str], mech: dict) -> bool:
    """Causality check: the fork is the point only if NO defense saves both
    prongs. After the fork move, take the engine's top defenses; in every one,
    the continuation must still collect a target with the eval holding.
    Presence is geometry; the point is a counterfactual."""
    import chess
    board = chess.Board(fen)
    # replay to just after the fork move
    idx = san_line.index(mech["fork_move"])
    for san in san_line[: idx + 1]:
        board.push(board.parse_san(san))
    fork_fen = board.fen()
    target_sqs = {t.split()[-1] for t in mech["targets"]}   # "queen on d5" -> "d5"

    defenses = probes.analyze(fork_fen, multipv=3)
    if not defenses:
        return False
    for d in defenses:
        if not d.san:
            continue
        # after this defense, does the engine's own continuation capture a prong
        # while we stay winning? (defender POV eval: negative = we're winning)
        end_fen, cp, mate_in, best, pv = probes.explore(fork_fen, [d.san[0]])
        line = [best] + pv if best else pv
        collects = any(m.rstrip("+#").endswith(sq) and "x" in m
                       for m in line[:4] for sq in target_sqs)
        still_winning = (-d.cp) >= 150 or cp >= 150 or mate_in != 0
        if not (collects or still_winning):
            return False        # a defense exists that saves both prongs
    return True


def confirm_attraction(probes, fen: str, san_line: list[str], mech: dict) -> dict | None:
    """Causality check for attraction after a check (0PY6y ruling): check
    forces A response, not THIS response. The lure is real only if declining
    loses — an engine fact, not geometry. Returns the refutation of declining
    (which is also the coach's sentence: "the rook must take — otherwise ...")
    or None if a sound decline exists (claim rejected)."""
    import chess
    board = chess.Board(fen)
    idx = san_line.index(mech["forcing_move"])
    for san in san_line[:idx + 1]:
        board.push(board.parse_san(san))
    pos = board.fen()
    us_winning_sign = -1        # after our forcing move, evals are opponent-POV

    lured_reply = san_line[idx + 1]
    declines = probes.analyze(pos, multipv=3)
    chosen_cp = next((d.cp for d in declines if d.san and d.san[0] == lured_reply), None)
    if chosen_cp is None:
        return None
    refutations = {}
    for d in declines:
        if not d.san or d.san[0] == lured_reply:
            continue
        # (0VHBI ruling) DIFFERENTIAL compulsion: the alternative must be
        # substantially worse than the chosen reply — equal-loss alternatives
        # mean the choice extracted nothing and there was no lure.
        if (chosen_cp - d.cp) >= 200 or abs(d.cp) >= 1000:
            refutations[d.san[0]] = {"eval_cp": d.cp, "vs_chosen": chosen_cp - d.cp,
                                     "line": d.san[:4]}
        else:
            return None          # an equally-good defense exists — not lured
    return refutations


def confirm_hanging(probes, fen: str, san_line: list[str], mech: dict) -> bool:
    """(Adjudication ruling #11, case 0VaRv): a hanging piece is a PERISHABLE
    opportunity — take it now or it escapes. Two engine facts kill the claim:
      compelled  — every alternative loses; the capture is survival
      doomed     — the alternative line captures the same piece anyway
                   (the piece is trapped; the capture is bookkeeping, and the
                   puzzle's real point lies elsewhere, e.g. the technique after)
    0JDnk passes both: hxg3 first lets the f8 rook escape — genuinely urgent."""
    lines = probes.analyze(fen, multipv=2)
    if len(lines) < 2 or not lines[1].san:
        return False                      # no alternative at all — compelled
    if lines[1].cp <= -150:
        return False                      # everything else loses — compelled
    sq = mech.get("hanging_on", "")
    for san in lines[1].san[:6]:
        if "x" in san and san.rstrip("+#").endswith(sq):
            return False                  # doomed piece — no urgency, no lesson
    return True
