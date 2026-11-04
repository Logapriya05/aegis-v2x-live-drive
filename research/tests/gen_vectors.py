"""Generate parity vectors by calling Vaishnavi's own Phase 4/5 functions (unchanged)."""
import json, random, sys
sys.path.insert(0, sys.argv[1])  # path to the extracted feature/vaishnavi-ai-architect-ml-designer tree
from ai.trust_estimator.model import TwinTrustEstimator
from ai.criticality.model import CriticalityEstimator
from ai.twintrust_ap import gdca
from ai.twintrust_ap.tahs import TAHS, TAHSParams

rng = random.Random(20261104)
te, ce = TwinTrustEstimator(), CriticalityEstimator()
tahs = TAHS(TAHSParams(horizon_min=1, horizon_max=10, beta=1.0, gamma=1.0, delta=1.0, horizon_discretization=(1, 2, 3, 5, 8, 10)))
out = {"trust": [], "criticality": [], "gdca": [], "tahs": [], "spread": []}
for _ in range(2000):
    e, u, a, q = (rng.random() for _ in range(4))
    out["trust"].append([e, u, a, q, te.compute_trust_from_evidence(e, u, a, q)])
    f = [rng.random() for _ in range(5)]
    out["criticality"].append(f + [ce.compute_criticality_from_evidence(*f)])
    n = rng.choice([2, 3, 5, 8])
    win = [[rng.gauss(0, rng.choice([0.05, 0.5, 2.0])) for _ in range(n)] for _ in range(2)]
    if rng.random() < 0.1: win[0] = [1.0] * n            # constant window -> zero spread case
    spreads = [gdca.robust_spread(w) for w in win]
    res = [rng.gauss(0, 1.5) for _ in range(2)]
    out["spread"].append([win, spreads])
    out["gdca"].append([res, spreads, gdca.compute_authority_from_dimensional_evidence(res, spreads)])
    T, C, A = rng.random(), rng.random(), rng.random()
    out["tahs"].append([T, C, A, tahs.select_horizon(T, C, A)])
json.dump(out, open(sys.argv[2], "w"))
print("vectors written:", {k: len(v) for k, v in out.items()})
