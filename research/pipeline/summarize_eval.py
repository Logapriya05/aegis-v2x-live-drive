"""Compare TwinTrust-AP with the fixed-policy baseline on recorded evaluation runs (collect.py).

usage: summarize_eval.py TWINTRUST.jsonl FIXED.jsonl OUT.json

Per condition and overall: mean objective J (lower is better) and its parts, twin correctness R,
edge synchronisations per second and beam failures. The uncertainty of the J difference is a
block bootstrap over 10 s blocks (100 cycles), because consecutive cycles are strongly correlated.
Both modes use the same seed per condition, but their traffic diverges once actions differ, so
the comparison is between two runs of the same scenario, not a cycle-by-cycle pairing.
"""
import json, random, sys, collections

BLOCK, BOOT = 100, 2000
KEYS = ['J', 'L', 'E', 'O', 'F', 'R']

def load(p):
    by = collections.defaultdict(list)
    for l in open(p):
        r = json.loads(l); by[r['cond']].append(r)
    for rs in by.values(): rs.sort(key=lambda r: r['i'])
    return by

def stats(rs):
    n = len(rs); out = {k: sum(r[k] for r in rs) / n for k in KEYS}
    out['sync_per_s'] = sum(r['syncN'] for r in rs) / (n / 10)
    out['beam_failures'] = sum(r['F'] for r in rs); out['mean_H'] = sum(r['H'] for r in rs) / n; out['cycles'] = n
    return out

def blocks(rs): return [[r['J'] for r in rs[i:i + BLOCK]] for i in range(0, len(rs) - BLOCK + 1, BLOCK)]

def boot_diff(bt, bf, rng):
    """95% CI of mean J(twintrust) - mean J(fixed), resampling 10 s blocks within each run."""
    ds = []
    for _ in range(BOOT):
        a = [x for _ in bt for x in rng.choice(bt)]; b = [x for _ in bf for x in rng.choice(bf)]
        ds.append(sum(a) / len(a) - sum(b) / len(b))
    ds.sort(); return ds[int(.025 * BOOT)], ds[int(.975 * BOOT)]

tt, fx = load(sys.argv[1]), load(sys.argv[2]); rng = random.Random(7)
res = {'conditions': {}, 'note': __doc__.strip().splitlines()[0]}
allbt, allbf = [], []
print(f"{'condition':15} {'J TT':>7} {'J fix':>7} {'dJ':>7} {'95% CI':>17} {'R TT':>5} {'R fix':>5} {'sync/s TT':>9} {'fix':>5} {'beamF':>5}")
for c in tt:
    if c not in fx: continue
    a, b = stats(tt[c]), stats(fx[c]); bt, bf = blocks(tt[c]), blocks(fx[c]); allbt += bt; allbf += bf
    lo, hi = boot_diff(bt, bf, rng); d = a['J'] - b['J']
    res['conditions'][c] = {'twintrust': a, 'fixed': b, 'dJ': d, 'dJ_ci95': [lo, hi], 'significant': hi < 0 or lo > 0}
    print(f"{c:15} {a['J']:7.4f} {b['J']:7.4f} {d:7.4f} [{lo:7.4f},{hi:7.4f}] {a['R']:5.2f} {b['R']:5.2f} {a['sync_per_s']:9.2f} {b['sync_per_s']:5.2f} {a['beam_failures']:5d}")
A = stats([r for c in res['conditions'] for r in tt[c]]); B = stats([r for c in res['conditions'] for r in fx[c]])
lo, hi = boot_diff(allbt, allbf, rng)
res['overall'] = {'twintrust': A, 'fixed': B, 'dJ': A['J'] - B['J'], 'dJ_ci95': [lo, hi], 'significant': hi < 0 or lo > 0}
print(f"{'OVERALL':15} {A['J']:7.4f} {B['J']:7.4f} {A['J'] - B['J']:7.4f} [{lo:7.4f},{hi:7.4f}] {A['R']:5.2f} {B['R']:5.2f} {A['sync_per_s']:9.2f} {B['sync_per_s']:5.2f} {A['beam_failures']:5d}")
print('parts overall (TT vs fixed):', {k: (round(A[k], 4), round(B[k], 4)) for k in KEYS})
json.dump(res, open(sys.argv[3], 'w'), indent=1)
