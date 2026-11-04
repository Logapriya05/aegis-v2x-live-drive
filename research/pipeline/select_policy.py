"""Constrained closed-loop selection of the FSDP policy table.

Objective (configs/model.yaml): minimise J = 0.25 L + 0.20 E + 0.20 O + 0.20 F - 0.15 R,
but only among tables whose twin correctness R is at least the fixed baseline's
(horizon 5, edge synchronisation every 1 s): overall, and in every condition within TOL.

Why closed-loop: per-state averages from random-action exploration cannot show the
constraint, because a single action's effect on twin accuracy depends on the actions
that follow it. So each candidate table is run as a whole policy in the simulation
(collect.py, mode twintrust) on SELECTION seeds (SEED_OFF=777, 90 s per condition),
and the chosen table is then evaluated once on the separate evaluation seeds.

usage: select_policy.py FIXED.jsonl CANDIDATE_1.jsonl [CANDIDATE_2.jsonl ...] > report
       (candidate name = the part of the file name after 's_', e.g. s_c5.jsonl -> c5)
writes search_result.json
"""
import collections
import json
import sys

TOL = 0.01


def load(p):
    by = collections.defaultdict(list)
    for line in open(p):
        r = json.loads(line)
        by[r['cond']].append(r)
    return by


def mean(v):
    return sum(v) / len(v)


fx = load(sys.argv[1])
fR = {c: mean([r['R'] for r in rs]) for c, rs in fx.items()}
fJ = mean([r['J'] for rs in fx.values() for r in rs])
fRall = mean([r['R'] for rs in fx.values() for r in rs])
fS = mean([r['syncN'] for rs in fx.values() for r in rs]) * 10
print(f"fixed      J {fJ:.4f}  R {fRall:.3f}  sync/s {fS:.1f}")
out = {}
for p in sys.argv[2:]:
    by = load(p)
    name = p.split('s_')[-1].split('.')[0]
    J = mean([r['J'] for rs in by.values() for r in rs])
    R = mean([r['R'] for rs in by.values() for r in rs])
    S = mean([r['syncN'] for rs in by.values() for r in rs]) * 10
    worst = min(mean([r['R'] for r in rs]) - fR[c] for c, rs in by.items())
    feas = R >= fRall - 1e-9 and worst >= -TOL
    out[name] = dict(J=J, R=R, sync_per_s=S, worst_condition_R_gap=worst, feasible=feas)
    print(f"{name:10} J {J:.4f}  R {R:.3f}  sync/s {S:5.1f}  worst-cond R gap {worst:+.3f}  "
          f"{'FEASIBLE' if feas else 'infeasible'}")
best = min((k for k, v in out.items() if v['feasible']), key=lambda k: out[k]['J'], default=None)
print('selected:', best)
json.dump({'fixed': dict(J=fJ, R=fRall, sync_per_s=fS, R_by_condition=fR), 'candidates': out,
           'selected': best, 'tolerance': TOL}, open('search_result.json', 'w'), indent=1)
