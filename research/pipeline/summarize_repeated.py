"""Repeated-run comparison of TwinTrust-AP with the fixed policy and the age-of-information baseline.

usage: [MODES=b1,fixed,aoi,...] summarize_repeated.py OUT.json SET_1 [SET_2 ...]
  each SET is a file prefix; the script reads SET_<mode>.jsonl for every mode (the first mode is the
  one compared with all others); collect.py runs with one SEED_OFF per set, 150 s per condition.
  Besides J and R it reports the cost parts L (information age), E (modelled energy) and
  O (synchronisation overhead), each normalised as in the J objective.

A seed set is one independent repetition: each mode is run on the same seeds, so a set gives one
paired difference per metric. The 95% confidence interval of a difference uses Student's t over
the sets (n - 1 degrees of freedom). Conditions are also reported per set mean, without an interval,
because per-condition differences were seen to change between seed sets.
"""
import collections
import json
import math
import statistics
import os
import sys

MODES = os.environ.get('MODES', 'b1,fixed,aoi,aoi02').split(',')
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}


def load(p):
    by = collections.defaultdict(list)
    for line in open(p):
        r = json.loads(line)
        by[r['cond']].append(r)
    return by


def nmean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else float('nan')


def metrics(rs):
    n = len(rs)
    return {'J': sum(r['J'] for r in rs) / n, 'R': sum(r['R'] for r in rs) / n,
            'R_v2v': nmean([r.get('correctV2V') for r in rs]), 'err_v2v_m': nmean([r.get('meanErrV2V') for r in rs]),
            'L': sum(r['L'] for r in rs) / n, 'E': sum(r['E'] for r in rs) / n, 'O': sum(r['O'] for r in rs) / n,
            'sync_per_s': sum(r['syncN'] for r in rs) / (n / 10),
            'beam_per_s': sum(r['beam'] for r in rs) / (n / 10), 'mean_H': sum(r['H'] for r in rs) / n}


def ci(vals):
    m = statistics.fmean(vals)
    if len(vals) < 2:
        return m, None
    h = T95[len(vals) - 1] * statistics.stdev(vals) / math.sqrt(len(vals))
    return m, [m - h, m + h]


out_path, sets = sys.argv[1], sys.argv[2:]
per_set, per_cond = [], collections.defaultdict(lambda: collections.defaultdict(list))
for s in sets:
    data = {m: load(f'{s}_{m}.jsonl') for m in MODES}
    conds = sorted(set.intersection(*(set(d) for d in data.values())))
    per_set.append({m: metrics([r for c in conds for r in data[m][c]]) for m in MODES})
    for c in conds:
        for m in MODES:
            per_cond[c][m].append(metrics(data[m][c]))

res = {'sets': sets, 'per_set': per_set, 'overall': {}, 'differences': {}, 'conditions': {}}
for m in MODES:
    res['overall'][m] = {k: ci([ps[m][k] for ps in per_set]) for k in per_set[0][m]}
for other in MODES[1:]:
    res['differences'][f'{MODES[0]}_minus_{other}'] = {
        k: ci([ps[MODES[0]][k] - ps[other][k] for ps in per_set]) for k in ('J', 'R', 'R_v2v', 'err_v2v_m', 'L', 'E', 'O', 'sync_per_s')}
for c, d in per_cond.items():
    res['conditions'][c] = {m: {k: statistics.fmean(x[k] for x in d[m]) for k in ('J', 'R', 'R_v2v', 'sync_per_s')}
                            for m in MODES}

print(f"{len(sets)} seed sets")
for m in MODES:
    o = res['overall'][m]
    print(f"{m:8} J {o['J'][0]:.4f}  R {o['R'][0]:.3f}  R_v2v {o['R_v2v'][0]:.3f}  err_v2v {o['err_v2v_m'][0]:.2f} m  L {o['L'][0]:.3f}  E {o['E'][0]:.3f}  O {o['O'][0]:.3f}  "
          f"sync/s {o['sync_per_s'][0]:5.1f}  beam/s {o['beam_per_s'][0]:4.2f}")
for k, d in res['differences'].items():
    print(k, {m: (round(v[0], 4), v[1] and [round(x, 4) for x in v[1]]) for m, v in d.items()})
print(f"{'condition':15}" + ''.join(f"{m + ' J':>9}{m + ' R':>8}" for m in MODES))
for c, d in sorted(res['conditions'].items()):
    print(f"{c:15}" + ''.join(f"{d[m]['J']:9.4f}{d[m]['R']:8.3f}" for m in MODES))
json.dump(res, open(out_path, 'w'), indent=1)
