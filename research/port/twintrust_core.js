/* ================= TwinTrust-AP core (exact JavaScript port) =================
   Source of truth: Vaishnavi's Python implementation, branch feature/vaishnavi-ai-architect-ml-designer
   of the Aegis-V2X repository (copied into research/aegis_ai/ of this repository):
     ai/trust_estimator/model.py   compute_trust_from_evidence      T = sigmoid((w4*q - w1*e - w2*u - w3*a) / tau)
     ai/criticality/model.py       compute_criticality_from_evidence C = sum(alpha_i * f_i), sum(alpha_i) = 1
     ai/twintrust_ap/gdca.py       robust_spread, compute_authority_from_dimensional_evidence  A = exp(-0.5 z^2)
     ai/twintrust_ap/tahs.py       TAHS.select_horizon              H = Hmin + (Hmax-Hmin)*sigmoid(beta*T - gamma*C + delta*A)
   Every function below is checked against outputs of the Python originals (research/tests/test_parity.cjs).
   Calibration (Platt scaling of T) and the FSDP policy table are added on top, not by editing these functions. */
const TT = (() => {
  const TRUST_W = [0.35, 0.25, 0.20, 0.20];          // configs/model.yaml trust_estimator.feature_weights (w1..w4)
  const TRUST_TAU = 0.8;                              // configs/model.yaml trust_estimator.calibration_temperature
  const CRIT_W = [0.25, 0.25, 0.15, 0.20, 0.15];      // configs/model.yaml criticality_estimator.feature_weights
  const EPS = 1e-9, MAD_TO_SIGMA = 1.4826;            // gdca.py _EPS, _MAD_TO_SIGMA
  const fin = x => typeof x === 'number' && Number.isFinite(x);
  const need = (x, n) => { if (!fin(x)) throw new Error(`${n} must be a finite number, got ${x}`) };
  const needSeq = (s, n) => { if (!Array.isArray(s) || !s.every(fin)) throw new Error(`${n} must be a sequence of finite numbers`) };

  // ai/trust_estimator/model.py: compute_trust_from_evidence (uncalibrated, exactly as written)
  function trustFromEvidence(e, u, a, q) {
    need(e, 'prediction_error'); need(q, 'comm_quality'); need(a, 'sync_age_penalty'); need(u, 'prediction_uncertainty');
    const [w1, w2, w3, w4] = TRUST_W;
    const raw = w4 * q - w1 * e - w2 * u - w3 * a;
    const T = 1 / (1 + Math.exp(-raw / TRUST_TAU));
    if (!(T >= 0 && T <= 1)) throw new Error('trust outside [0,1]');
    return T;
  }
  const trustRawScore = (e, u, a, q) => TRUST_W[3] * q - TRUST_W[0] * e - TRUST_W[1] * u - TRUST_W[2] * a;

  // ai/criticality/model.py: compute_criticality_from_evidence
  function criticalityFromEvidence(relSpeed, blockage, syncAge, chanDeg, density) {
    const f = [relSpeed, blockage, syncAge, chanDeg, density];
    ['relative_speed', 'blockage_probability', 'sync_age', 'channel_degradation', 'traffic_density'].forEach((n, i) => need(f[i], n));
    return f.reduce((s, v, i) => s + CRIT_W[i] * v, 0);
  }

  // ai/twintrust_ap/gdca.py
  function median(values) { const o = [...values].sort((x, y) => x - y), n = o.length, m = n >> 1; return n % 2 ? o[m] : (o[m - 1] + o[m]) / 2 }
  function robustSpread(recent) {
    needSeq(recent, 'recent_values'); if (recent.length < 2) throw new Error('residual_level_and_spread requires at least 2 samples');
    const level = median(recent); return MAD_TO_SIGMA * median(recent.map(v => Math.abs(v - level)));
  }
  function authorityFromEvidence(residualNorm, uncertainty) {
    need(residualNorm, 'residual_norm'); need(uncertainty, 'uncertainty');
    if (residualNorm < 0 || uncertainty < 0) throw new Error('residual_norm and uncertainty must be >= 0');
    const z = residualNorm / (uncertainty + EPS); return Math.exp(-0.5 * z * z);
  }
  function authorityFromDimensionalEvidence(residuals, spreads) {
    needSeq(residuals, 'residuals'); needSeq(spreads, 'spreads');
    if (residuals.length !== spreads.length) throw new Error('residuals and spreads must have the same number of dimensions');
    if (spreads.some(s => s < 0)) throw new Error("each dimension's spread must be >= 0");
    const z = residuals.map((r, i) => r / (spreads[i] + EPS));
    const zc = Math.sqrt(z.reduce((s, v) => s + v * v, 0) / z.length);
    return authorityFromEvidence(zc, 1.0);
  }

  // ai/twintrust_ap/tahs.py: TAHS.select_horizon (parameters passed in; defaults = configs/model.yaml)
  const TAHS_SPEC = { hMin: 1, hMax: 10, beta: 1.0, gamma: 1.0, delta: 1.0, disc: [1, 2, 3, 5, 8, 10] };
  function selectHorizon(T, C, A = 0, p = TAHS_SPEC) {
    if (!(T >= 0 && T <= 1)) throw new Error(`trust must be in [0, 1], got ${T}`);
    if (!(C >= 0 && C <= 1)) throw new Error(`criticality must be in [0, 1], got ${C}`);
    if (!(A >= 0 && A <= 1)) throw new Error(`authority must be in [0, 1], got ${A}`);
    const arg = p.beta * T - p.gamma * C + p.delta * A + (p.bias || 0);
    const hc = p.hMin + (p.hMax - p.hMin) / (1 + Math.exp(-arg));
    // Python min(disc, key=|h-hc|) returns the FIRST minimum on ties; reduce with strict < does the same
    return p.disc.reduce((best, h) => Math.abs(h - hc) < Math.abs(best - hc) ? h : best, p.disc[0]);
  }
  return { TRUST_W, TRUST_TAU, CRIT_W, TAHS_SPEC, trustFromEvidence, trustRawScore, criticalityFromEvidence, robustSpread, authorityFromEvidence, authorityFromDimensionalEvidence, selectHorizon, median };
})();
if (typeof module !== 'undefined') module.exports = TT;
