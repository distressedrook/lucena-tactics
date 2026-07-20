"""Branch-diff explanation pipeline over Lichess puzzles.

Measures: for (position, solution S, human foil M), can a deterministic
procedure produce a non-empty, classified explanation of why M fails?

  completeness = % puzzles with class != 'other' AND non-empty mechanism diff
  soundness    = every emitted slot carries its numeric witness (by construction)

Foils come from Maia (Behaviour.TopHumanMoves) when available, else engine #2.
All engine truth from lucena-engine gRPC (:50052, fixed nodes => deterministic).
Predicates computed client-side with python-chess (notation/legality only —
never eval).
"""
import sys, csv, json, random, time, argparse, concurrent.futures as cf
sys.path.insert(0, 'gen')
import grpc, chess
from lucena.engine.v1 import engine_pb2 as pb, engine_pb2_grpc as rpc

ADDR = '127.0.0.1:50052'
NODES = 1_000_000
THREAT_NODES = 600_000
MISTAKE_DWP = -15.0          # win% drop for a move to count as a mistake
PREMISE_GAP = 10.0           # win% gap between best and #2 for a valid puzzle

def stubs():
    ch = grpc.insecure_channel(ADDR)
    return rpc.TruthStub(ch), rpc.BehaviourStub(ch)

L = lambda n=NODES: pb.Limit(nodes=n, threads=1)

# ---------------------------------------------------------------- predicates
def annotate_line(fen, san_moves):
    """Deterministic ply-level predicates for a SAN line. Layer 1."""
    b = chess.Board(fen)
    out = []
    for san in san_moves:
        try:
            mv = b.parse_san(san)
        except ValueError:
            break
        p = {'san': san}
        p['capture'] = b.is_capture(mv)
        if p['capture']:
            cap = b.piece_at(mv.to_square)
            p['captured'] = chess.piece_name(cap.piece_type) if cap else 'pawn(ep)'
        p['check'] = b.gives_check(mv)
        piece = b.piece_at(mv.from_square)
        p['piece'] = chess.piece_name(piece.piece_type) if piece else '?'
        p['to'] = chess.square_name(mv.to_square)
        b.push(mv)
        if p['check']:
            # discovered = the moved piece is not (the only) checker
            checkers = b.checkers()
            p['discovered'] = bool(checkers and mv.to_square not in checkers)
            p['double_check'] = len(checkers) > 1
        p['mate'] = b.is_checkmate()
        p['forced_reply'] = (not p['mate']) and b.legal_moves.count() == 1
        # v2 primitives (learned from run 1: empty diffs were endgame/pawn puzzles)
        p['promotion'] = mv.promotion is not None
        if piece and piece.piece_type == chess.PAWN:
            rank = chess.square_rank(mv.to_square)
            rel = rank if piece.color == chess.WHITE else 7 - rank
            p['pawn_advanced'] = rel >= 5          # 6th rank or beyond
        out.append(p)
    return out

def predset(ann):
    """Bag of mechanism-relevant predicates for diffing."""
    s = set()
    for i, p in enumerate(ann):
        who = 'own' if i % 2 == 0 else 'opp'
        if p['check']:          s.add((who, 'check'))
        if p.get('discovered'): s.add((who, 'discovered_check'))
        if p.get('double_check'):s.add((who, 'double_check'))
        if p['mate']:           s.add((who, 'mate'))
        if p['capture'] and who == 'own':
            s.add(('own', 'wins_' + p.get('captured', '?')))
        if p.get('forced_reply') and who == 'own':
            s.add(('own', 'forcing'))
        if p.get('promotion') and who == 'own':
            s.add(('own', 'promotes'))
        if p.get('pawn_advanced') and who == 'own':
            s.add(('own', 'pawn_advanced'))
    return s

# ---------------------------------------------------------------- probes
def threat_if_pass(t, fen_after_move):
    """Null-move probe: what does the mover threaten? Returns (pv, cp, is_mate)."""
    f = fen_after_move.split()
    f[1] = 'w' if f[1] == 'b' else 'b'
    f[3] = '-'
    try:
        r = t.Analyze(pb.AnalyzeReq(fen=' '.join(f), limit=L(THREAT_NODES), multipv=1))
    except grpc.RpcError:
        return None
    if not r.lines:
        return None
    l = r.lines[0]
    return {'pv': list(l.pv_san)[:4], 'cp': l.eval.cp, 'win': l.eval.win_pct}

def explore(t, fen, moves):
    return t.ExploreLine(pb.ExploreReq(fen=fen, moves=moves, analyze=True, limit=L()))

# ---------------------------------------------------------------- classifier
def classify(fen, S, M, s_ann, m_ann, m_refut_ann, e_m, threat_S, threat_M):
    """Layer 2 v2: total decision tree, priorities learned from run 1.

    Run-1 lessons applied:
      - missed_mate promoted above move_order (theme matrix showed move_order
        stealing 19 mate puzzles)
      - move_order now STRICT: M must literally appear later in the S-line
        (same-from-square alone over-fired, 36% of run 1)
      - diff-fallback rules (mate/wins-material) are first-class, not post-hoc
      - promotion/advanced-pawn primitives cover run-1 empty-diff endgames
    """
    b = chess.Board(fen)
    s_mv, m_mv = b.parse_san(S), b.parse_san(M)
    ev = {}
    diff = predset(s_ann) - predset(m_ann)
    own_moves_later = [p['san'] for p in s_ann][1:]

    # 1. missed_mate: solution line mates; the played line doesn't.
    #    Outranks 'hung' by severity: forfeiting mate is the headline even
    #    when the played move also hangs material (both slots still filled).
    if ('own', 'mate') in diff:
        mate_ply = next((i for i, p in enumerate(s_ann) if p['mate']), None)
        ev['mate_in'] = (mate_ply // 2) + 1 if mate_ply is not None else None
        ev['mating_line'] = [p['san'] for p in s_ann[:(mate_ply or 0) + 1]]
        return 'missed_mate', ev
    # 2. hung: the refutation immediately captures the piece M just moved
    if m_refut_ann:
        r1 = m_refut_ann[0]
        if r1['capture'] and r1['to'] == chess.square_name(m_mv.to_square):
            ev['refutation_captures'] = f"{r1['san']} takes on {r1['to']}"
            return 'hung', ev
    # 3. wrong_piece: same destination square as the solution
    if s_mv.to_square == m_mv.to_square:
        ev['shared_target'] = chess.square_name(s_mv.to_square)
        return 'wrong_piece', ev
    # 4. move_order (strict): the exact move M occurs later in the solution line
    if M in own_moves_later:
        ev['S_line_reaches'] = M
        return 'move_order', ev
    # 5. missed_threat: refutation carries forcing punishment the player ignored
    if m_refut_ann and any(p['mate'] or p['check'] for p in m_refut_ann[:2]):
        ev['refutation_forcing'] = [p['san'] for p in m_refut_ann[:2]]
        return 'missed_threat', ev
    # 6. missed_tactic: S-line wins material that the M-line doesn't
    wins = sorted(k for w, k in diff if w == 'own' and k.startswith('wins_'))
    if wins:
        ev['forfeited_material'] = wins
        return 'missed_tactic', ev
    # 7. missed_tactic via null-move: S carried a decisive threat M forfeits
    if threat_S and (threat_S['cp'] >= 500) and not (threat_M and threat_M['cp'] >= 500):
        ev['forfeited_threat'] = threat_S['pv']
        return 'missed_tactic', ev
    # 8. missed_promotion: solution promotes / runs a passer; played line doesn't
    if ('own', 'promotes') in diff or ('own', 'pawn_advanced') in diff:
        ev['pawn_play'] = [p['san'] for p in s_ann if p.get('promotion') or p.get('pawn_advanced')]
        return 'missed_promotion', ev
    return 'other', ev

# ---------------------------------------------------------------- foils
def maia_foil(bh, t, fen, rating, S, log):
    try:
        m = bh.TopHumanMoves(pb.MaiaReq(fen=fen, rating=max(1100, min(1900, rating)), n=5))
    except grpc.RpcError as e:
        log['maia_error'] = e.details()
        return None, None
    for mv in m.moves:
        if mv.san == S:
            continue
        e = t.Evaluate(pb.EvaluateReq(fen=fen, moves=[mv.san], limit=L()))
        if e.delta_win_pct <= MISTAKE_DWP:
            return mv.san, {'source': 'maia', 'policy': mv.policy, 'rank': mv.rank,
                            'dwp': e.delta_win_pct, 'eval_resp': e}
        log.setdefault('maia_fine_moves', []).append((mv.san, e.delta_win_pct))
    return None, None

def engine2_foil(t, fen, root, S, log):
    for l in root.lines:
        san0 = l.pv_san[0] if l.pv_san else None
        if not san0 or san0 == S:
            continue
        e = t.Evaluate(pb.EvaluateReq(fen=fen, moves=[san0], limit=L()))
        if e.delta_win_pct <= MISTAKE_DWP:
            return san0, {'source': 'engine#2', 'dwp': e.delta_win_pct, 'eval_resp': e}
    return None, None

# ---------------------------------------------------------------- per-puzzle
def run_puzzle(row):
    t, bh = stubs()
    log = {'id': row['PuzzleId'], 'rating': int(row['Rating']), 'themes': row['Themes']}
    t0 = time.time()
    try:
        b = chess.Board(row['FEN'])
        ucis = row['Moves'].split()
        b.push(chess.Move.from_uci(ucis[0]))          # opponent's setup move
        fen = b.fen()
        S = b.san(chess.Move.from_uci(ucis[1]))        # solution in SAN
        sol_line = []
        bb = chess.Board(fen)
        for u in ucis[1:]:
            mv = chess.Move.from_uci(u); sol_line.append(bb.san(mv)); bb.push(mv)
        log['fen'], log['S'] = fen, S

        # premise: S unique?
        root = t.Analyze(pb.AnalyzeReq(fen=fen, limit=L(), multipv=3))
        log['root_best'] = root.lines[0].pv_san[0] if root.lines else None
        log['root_win'] = root.eval.win_pct
        if log['root_best'] != S:
            log['status'] = 'premise_engine_disagrees'; return log
        gap = (root.lines[0].eval.win_pct - root.lines[1].eval.win_pct) if len(root.lines) > 1 else 100.0
        log['gap'] = round(gap, 1)
        if gap < PREMISE_GAP:
            log['status'] = 'premise_not_unique'; return log

        # foil
        M, meta = maia_foil(bh, t, fen, int(row['Rating']), S, log)
        if M is None:
            M, meta = engine2_foil(t, fen, root, S, log)
        if M is None:
            log['status'] = 'no_valid_foil'; return log
        e_m = meta.pop('eval_resp')
        log['M'], log['foil'] = M, meta

        # branches
        s_pv = list(root.lines[0].pv_san)              # S-line from engine
        m_line = [M] + list(e_m.refutation_pv)
        s_ann = annotate_line(fen, s_pv)
        m_ann = annotate_line(fen, m_line)
        m_refut_ann = annotate_line(explore(t, fen, [M]).end_fen if True else fen,
                                    list(e_m.refutation_pv)) if e_m.refutation_pv else []
        x_s = explore(t, fen, [S]); x_m = explore(t, fen, [M])
        threat_S = threat_if_pass(t, x_s.end_fen)
        threat_M = threat_if_pass(t, x_m.end_fen)

        # layer 3: mechanism diff
        diff = predset(s_ann) - predset(m_ann)
        log['diff'] = sorted(f"{w}:{k}" for w, k in diff)
        # layer 2: classification
        cls, evidence = classify(fen, S, M, s_ann, m_ann, m_refut_ann, e_m, threat_S, threat_M)
        log['class'], log['evidence'] = cls, evidence
        log['dwp'] = round(e_m.delta_win_pct, 1)
        log['refutation'] = list(e_m.refutation_pv)[:6]
        log['s_pv'] = s_pv[:8]
        log['threat_S'] = threat_S; log['threat_M'] = threat_M
        log['complete'] = bool(diff) and cls != 'other'
        log['status'] = 'ok'
    except Exception as ex:
        log['status'] = 'error'; log['error'] = f"{type(ex).__name__}: {ex}"[:200]
    log['secs'] = round(time.time() - t0, 1)
    return log

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--csv', default='puzzles_head.csv')
    ap.add_argument('--out', default='results.jsonl')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--exclude', default=None, help='jsonl of prior run; skip its puzzle ids')
    args = ap.parse_args()

    seen = set()
    if args.exclude:
        seen = {json.loads(l)['id'] for l in open(args.exclude)}
    rows = [r for r in csv.DictReader(open(args.csv))
            if int(r['Popularity']) >= 90 and int(r['NbPlays']) >= 1000
            and 800 <= int(r['Rating']) <= 2200 and r['PuzzleId'] not in seen]
    # stratify by rating quartile
    random.Random(args.seed).shuffle(rows)
    bands = {(800,1200):[], (1200,1600):[], (1600,2000):[], (2000,2201):[]}
    for r in rows:
        for (lo,hi),bucket in bands.items():
            if lo <= int(r['Rating']) < hi: bucket.append(r)
    per = args.n // 4
    sample = [r for b in bands.values() for r in b[:per]]
    print(f"pool={len(rows)} sample={len(sample)}", flush=True)

    done = 0
    with open(args.out, 'w') as f, cf.ThreadPoolExecutor(args.workers) as ex:
        for log in ex.map(run_puzzle, sample):
            f.write(json.dumps(log, default=str) + '\n'); f.flush()
            done += 1
            if done % 10 == 0:
                print(f"{done}/{len(sample)}", flush=True)
    print("DONE", flush=True)

if __name__ == '__main__':
    main()
