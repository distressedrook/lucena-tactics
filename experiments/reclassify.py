"""Offline v2 reclassification of run-1 results — no engine calls.

Everything the v2 classifier needs was logged as data (fen, S, M, s_pv,
refutation, threats). Re-annotate with v2 primitives, re-classify, report.
Caveat: s_pv was logged truncated to 8 plies, refutation to 6 — mates deeper
than that in the S-line are invisible here (the held-out run has full lines).
"""
import json, collections, sys, chess
from pipeline import annotate_line, predset, classify

rows = [json.loads(l) for l in open('results.jsonl')]
ok = [r for r in rows if r['status'] == 'ok']

def band(r):
    x = r['rating']
    return "800-1200" if x < 1200 else "1200-1600" if x < 1600 else "1600-2000" if x < 2000 else "2000+"

out, by_band = [], collections.defaultdict(list)
for r in ok:
    fen, S, M = r['fen'], r['S'], r['M']
    s_ann = annotate_line(fen, r['s_pv'])
    b = chess.Board(fen); b.push_san(M)
    m_refut_ann = annotate_line(b.fen(), r['refutation'])
    m_ann = annotate_line(fen, [M] + r['refutation'])
    cls, ev = classify(fen, S, M, s_ann, m_ann, m_refut_ann, None,
                       r.get('threat_S'), r.get('threat_M'))
    diff = predset(s_ann) - predset(m_ann)
    complete = bool(diff) and cls != 'other'
    out.append({**r, 'class2': cls, 'evidence2': ev, 'complete2': complete})
    by_band[band(r)].append((r['complete'], complete))

print("== v1 -> v2 completeness (offline reclassification of run 1) ==")
tot1 = tot2 = n = 0
for bd in ["800-1200", "1200-1600", "1600-2000", "2000+"]:
    pairs = by_band[bd]
    c1, c2 = sum(p[0] for p in pairs), sum(p[1] for p in pairs)
    tot1 += c1; tot2 += c2; n += len(pairs)
    print("  %-10s n=%-3d  %3.0f%% -> %3.0f%%" % (bd, len(pairs), 100*c1/len(pairs), 100*c2/len(pairs)))
print("  %-10s n=%-3d  %3.0f%% -> %3.0f%%" % ("TOTAL", n, 100*tot1/n, 100*tot2/n))

print("\n== v2 class distribution ==")
print(dict(collections.Counter(r['class2'] for r in out)))

print("\n== v2 classifier vs lichess themes ==")
m = collections.defaultdict(collections.Counter)
thememap = {'hangingPiece': 'hung', 'fork': 'missed_tactic', 'mate': 'missed_mate',
            'mateIn1': 'missed_mate', 'mateIn2': 'missed_mate', 'mateIn3': 'missed_mate',
            'pin': 'missed_tactic', 'discoveredAttack': 'missed_tactic',
            'promotion': 'missed_promotion', 'advancedPawn': 'missed_promotion'}
agree = disagree = 0
for r in out:
    expected = {thememap[t] for t in r['themes'].split() if t in thememap}
    for t in r['themes'].split():
        if t in thememap:
            m[thememap[t]][r['class2']] += 1
    if expected:
        agree += r['class2'] in expected; disagree += r['class2'] not in expected
for k, v in sorted(m.items()):
    print("  theme→%-16s classified as: %s" % (k, dict(v.most_common(4))))
print("theme agreement (where a theme maps): %d/%d = %.0f%%" % (agree, agree+disagree, 100*agree/max(1, agree+disagree)))

print("\n== remaining v2 others ==")
for r in out:
    if r['class2'] == 'other':
        print("[%s r%d] S=%s M=%s themes=%s diff=%s" % (r['id'], r['rating'], r['S'], r['M'],
              ' '.join(r['themes'].split()[:4]), sorted(r['diff'])))

json.dump(out, open('results_v2.json', 'w'), default=str)
