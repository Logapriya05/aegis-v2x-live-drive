"""Offline generation of the FSDP policy table (the Phase 5 blocker in ai/twintrust_ap/fsdp.py).

Data: TwinTrust-AP cycles recorded from the live demo with uniformly random actions (collect.py, mode=explore).
For every cycle we know the state (calibrated trust bin x criticality bin), the action taken, and the per-cycle
objective J = 0.25 L + 0.20 E + 0.20 O + 0.20 F - 0.15 R (configs/model.yaml objective_function).
The cost of an action is the mean J over HORIZON cycles starting with the action's own cycle (its effect lasts beyond one cycle;
because later actions are also random, this is an unbiased comparison between actions in the same state).
Policy: for each of the 9 states, the action with the lowest mean cost, if every action has >= MIN_N samples.
States without enough data fall back to the design rule in 04_Novel_Algorithm_Design (marked 'design_prior').

usage: generate_fsdp_policy.py RECORDS.jsonl OUT.json
"""
import json, math, sys, collections

HORIZON, MIN_N = 10, 40
ACTIONS = ['synchronize', 'predict', 'beam_switch', 'reduce_horizon', 'increase_horizon', 'maintain_state']
BINS = ['low', 'medium', 'high']
# 04_Novel_Algorithm_Design, TAHS operating principle, used only where data is insufficient:
DESIGN_PRIOR = {('high', 'low'): 'increase_horizon', ('high', 'medium'): 'maintain_state', ('high', 'high'): 'predict',
                ('medium', 'low'): 'maintain_state', ('medium', 'medium'): 'predict', ('medium', 'high'): 'synchronize',
                ('low', 'low'): 'synchronize', ('low', 'medium'): 'synchronize', ('low', 'high'): 'synchronize'}

recs = [json.loads(l) for l in open(sys.argv[1])]
by = collections.defaultdict(list)
for r in recs: by[r['cond']].append(r)
cost = collections.defaultdict(list)
for rs in by.values():
    rs.sort(key=lambda r: r['i'])
    for k in range(len(rs) - HORIZON):
        r = rs[k]
        if r['state'] == 'fixed': continue
        cost[(r['state'], r['action'])].append(sum(x['J'] for x in rs[k:k + HORIZON]) / HORIZON)  # includes the action's own cycle (its overhead is booked there)

table, detail = {b: {} for b in BINS}, {}
for tb in BINS:
    for cb in BINS:
        st = f'{tb}/{cb}'
        stats = {a: (sum(cost[(st, a)]) / len(cost[(st, a)]) if cost[(st, a)] else None, len(cost[(st, a)]),
                     (lambda v: (math.sqrt(sum((x - sum(v) / len(v)) ** 2 for x in v) / (len(v) - 1)) / math.sqrt(len(v))) if len(v) > 1 else None)(cost[(st, a)]))
                 for a in ACTIONS}
        if all(n >= MIN_N for _, n, _ in stats.values()):
            ranked = sorted(ACTIONS, key=lambda a: stats[a][0]); best = ranked[0]
            m1, n1, se1 = stats[best]; m2, n2, se2 = stats[ranked[1]]
            z = (m2 - m1) / math.sqrt(se1 ** 2 + se2 ** 2) if se1 and se2 else None
            table[tb][cb] = best
            detail[st] = {'source': 'optimised', 'action': best, 'runner_up': ranked[1], 'z_margin': round(z, 2) if z is not None else None,
                          'mean_cost': {a: (round(stats[a][0], 5), stats[a][1]) for a in ACTIONS}}
        else:
            table[tb][cb] = DESIGN_PRIOR[(tb, cb)]
            detail[st] = {'source': 'design_prior', 'action': table[tb][cb], 'samples': {a: stats[a][1] for a in ACTIONS}}
json.dump({'policy': table, 'detail': detail, 'horizon_cycles': HORIZON, 'min_samples': MIN_N, 'records': len(recs)}, open(sys.argv[2], 'w'), indent=1)
for st, d in detail.items():
    print(st.ljust(14), d['source'].ljust(13), d['action'].ljust(17), ('runner-up ' + d['runner_up'] + f" (z={d['z_margin']})") if d['source'] == 'optimised' else d.get('samples'))
