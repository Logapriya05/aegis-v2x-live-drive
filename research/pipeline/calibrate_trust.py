"""Platt calibration of the Calibrated Twin Trust Estimator.

Her estimator outputs T = sigmoid(raw / tau), raw = w4*q - w1*e - w2*u - w3*a (weights and tau from configs/model.yaml).
Calibration keeps raw unchanged and fits T_cal = sigmoid(a*raw + b), so that T_cal matches the observed probability
that a digital-twin object is correct (within 1 m of where the ego's LiDAR sees it) on the next cycle.
The uncalibrated estimator is the special case a = 1/tau, b = 0.

usage: calibrate_trust.py RECORDS.jsonl OUT.json
"""
import json, math, sys

TAU = 0.8
recs = [json.loads(l) for l in open(sys.argv[1])]
by = {}
for r in recs: by.setdefault(r['cond'], []).append(r)
pairs = {'train': [], 'test': []}
for cond, rs in by.items():
    rs.sort(key=lambda r: r['i'])
    for k in range(len(rs) - 1):
        nxt = rs[k + 1]['correct']
        if nxt is None: continue
        raw = (0.20 * rs[k]['q'] - 0.35 * rs[k]['e'] - 0.25 * rs[k]['u'] - 0.20 * rs[k]['a'])
        pairs['train' if rs[k]['i'] < 1000 else 'test'].append((raw, nxt))

def fit(data, iters=50):
    """Logistic regression of the (fractional) next-cycle correctness on raw, by Newton's method."""
    a, b = 1 / TAU, 0.0
    for _ in range(iters):
        ga = gb = haa = hab = hbb = 0.0
        for x, y in data:
            p = 1 / (1 + math.exp(-(a * x + b))); w = p * (1 - p)
            ga += (p - y) * x; gb += (p - y); haa += w * x * x; hab += w * x; hbb += w
        det = haa * hbb - hab * hab
        if abs(det) < 1e-12: break
        da = (hbb * ga - hab * gb) / det; db = (haa * gb - hab * ga) / det
        a -= da; b -= db
        if abs(da) + abs(db) < 1e-10: break
    return a, b

def ece(data, a, b, bins=((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.0001))):
    """Expected Calibration Error over the five bands in configs/model.yaml."""
    tot, out = len(data), []
    e = 0.0
    for lo, hi in bins:
        sel = [(1 / (1 + math.exp(-(a * x + b))), y) for x, y in data if lo <= 1 / (1 + math.exp(-(a * x + b))) < hi]
        if not sel: out.append([lo, min(hi, 1), 0, None, None]); continue
        conf = sum(p for p, _ in sel) / len(sel); acc = sum(y for _, y in sel) / len(sel)
        e += len(sel) / tot * abs(conf - acc); out.append([lo, min(hi, 1), len(sel), round(conf, 4), round(acc, 4)])
    return e, out

def nll(data, a, b):
    s = 0.0
    for x, y in data:
        p = min(max(1 / (1 + math.exp(-(a * x + b))), 1e-9), 1 - 1e-9); s -= y * math.log(p) + (1 - y) * math.log(1 - p)
    return s / len(data)

a, b = fit(pairs['train'])
eu, du = ece(pairs['test'], 1 / TAU, 0.0)
ec, dc = ece(pairs['test'], a, b)
Ts = [1 / (1 + math.exp(-(a * x + b))) for x, _ in pairs['test']]
res = {'a': a, 'b': b, 'fitted': True, 'source': f'Platt scaling on {len(pairs["train"])} recorded cycles (8 conditions), tested on {len(pairs["test"])} held-out cycles',
       'target': 'probability that a twin object is within 1.0 m of the LiDAR-observed position on the next cycle',
       'ece_uncalibrated': round(eu, 4), 'ece_calibrated': round(ec, 4), 'nll_uncalibrated': round(nll(pairs['test'], 1 / TAU, 0), 4), 'nll_calibrated': round(nll(pairs['test'], a, b), 4),
       'reliability_uncalibrated': du, 'reliability_calibrated': dc, 'T_range_test': [round(min(Ts), 3), round(max(Ts), 3)]}
json.dump(res, open(sys.argv[2], 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if not k.startswith('reliability')}, indent=1))
print('calibrated reliability (band, n, mean T, observed):'); [print('  ', r) for r in dc]
print('uncalibrated reliability:'); [print('  ', r) for r in du]
