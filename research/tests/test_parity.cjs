// Parity test: the JavaScript port must reproduce the Python originals' outputs.
const TT = require(process.argv[2]);
const V = require(process.argv[3]);
let fails = 0, maxErr = { trust: 0, criticality: 0, gdca: 0, spread: 0 };
const chk = (k, a, b, tol = 1e-12) => { const d = Math.abs(a - b); if (d > maxErr[k]) maxErr[k] = d; if (!(d <= tol)) { fails++; if (fails < 10) console.log('MISMATCH', k, a, b) } };
for (const [e, u, a, q, T] of V.trust) chk('trust', TT.trustFromEvidence(e, u, a, q), T);
for (const r of V.criticality) chk('criticality', TT.criticalityFromEvidence(...r.slice(0, 5)), r[5]);
for (const [win, spreads] of V.spread) win.forEach((w, i) => chk('spread', TT.robustSpread(w), spreads[i]));
for (const [res, spreads, A] of V.gdca) chk('gdca', TT.authorityFromDimensionalEvidence(res, spreads), A);
let hm = 0; for (const [T, C, A, H] of V.tahs) { if (TT.selectHorizon(T, C, A) !== H) { hm++; fails++ } }
console.log(JSON.stringify({ cases: { trust: V.trust.length, criticality: V.criticality.length, gdca: V.gdca.length, spread: V.spread.length * 2, tahs: V.tahs.length }, maxAbsError: maxErr, tahsMismatches: hm, fails }));
process.exit(fails ? 1 : 0);
