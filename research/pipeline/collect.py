"""Record TwinTrust-AP cycles from the live demo, headless and seeded (statistically repeatable, not bit-identical; see research/README.md).

usage: collect.py OUT.jsonl MODE [CAL_JSON] [POLICY_JSON] [SECONDS]
  Seeds: Math.random is replaced by a seeded generator per condition (SEED_OFF env adds an offset, used for a second batch).
  MODE = explore   : TwinTrust-AP with uniformly random FSDP actions (data for calibration / policy generation)
         twintrust : TwinTrust-AP with the given calibration and policy table
         fixed     : fixed-policy baseline (horizon 5, edge sync every 1 s)
         aoi       : age-of-information threshold baseline (horizon 5, sync when mean age > AOI_THR s, env, default 0.8)
  PRED env: twin motion predictor, 'gru' (default) or 'ctrv' (dead reckoning, for the ablation).
  FC_GHZ env: carrier frequency of the 3GPP V2V channel in GHz (default: the demo's 30 GHz).
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

import pathlib
PAGE = (pathlib.Path(__file__).resolve().parents[2] / 'index.html').as_uri()
THREE = os.environ.get('THREE_DIR')   # optional local copy of the three@0.128.0 npm package (offline runs); else the CDN is used
CHROME = os.environ.get('CHROME')     # optional browser executable; else Playwright's bundled Chromium
CONDITIONS = [(c['name'], c['faults'], c['ego_speed_mps'], c['seed_base'])  # catalogue: research/scenarios.json
              for c in json.load(open(pathlib.Path(__file__).resolve().parents[1] / 'scenarios.json'))['conditions']]
SEED_JS = """(()=>{let s=%d>>>0;Math.random=function(){s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}})()"""

async def run(out, mode, cal, pol, secs, conds):
    async with async_playwright() as pw:
        b = await pw.chromium.launch(**({'executable_path': CHROME} if CHROME else {}), args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        f = open(out, 'w'); summary = []
        for name, faults, spd, seed in conds:
            ctx = await b.new_context(viewport={'width': 1280, 'height': 800}); await ctx.add_init_script(SEED_JS % (seed * 7919 + (0 if mode == 'explore' else 100003) + int(os.environ.get('SEED_OFF', '0'))))
            pg = await ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            if THREE:
                await pg.route('**/three.min.js', lambda r: r.fulfill(path=THREE + '/build/three.min.js'))
                async def ex(r): await r.fulfill(path=THREE + '/examples/js/' + r.request.url.split('examples/js/')[1])
                await pg.route('**/examples/js/**', ex); await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
            await pg.goto(PAGE); await pg.wait_for_timeout(2500)
            recs = await pg.evaluate("""([mode,cal,pol,faults,spd,secs,aoiThr,pred,fc])=>{const A=__aegis;A.TTAP_CFG.PRED=pred;if(fc)A.CH.FC=fc;window.__noRender=true;document.getElementById('start').hidden=true;
              if(cal)Object.assign(A.TTAP_CFG.CAL,cal);if(pol){A.TTAP_CFG.POLICY=pol.policy}
              A.ttap.mode=(mode==='fixed'||mode==='aoi')?mode:'twintrust';if(mode==='aoi')A.TTAP_CFG.AOI.thrS=aoiThr;A.ttap.explore=mode==='explore';
              A.fastForward(3,null);for(const f of faults)A.toggleFault(f);
              const auto=()=>{const k=A.keys,v=A.ego.v,c=A.crit;k.down=c.ttc<2.5&&v>2;k.up=!k.down&&v<spd};
              window.__ttapRecord=[];A.fastForward(secs,auto);const r=window.__ttapRecord;window.__ttapRecord=null;return r}""", [mode, cal, pol, faults, spd, secs, float(os.environ.get('AOI_THR', '0.8')), os.environ.get('PRED', 'gru'), float(os.environ.get('FC_GHZ', '0'))])
            for i, r in enumerate(recs):
                r['cond'] = name; r['i'] = i; f.write(json.dumps(r) + '\n')
            summary.append((name, len(recs), errs[:1])); await ctx.close()
        f.close(); await b.close(); print(json.dumps(summary))

out, mode = sys.argv[1], sys.argv[2]
cal = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and sys.argv[3] != '-' else None
pol = json.load(open(sys.argv[4])) if len(sys.argv) > 4 and sys.argv[4] != '-' else None
secs = float(sys.argv[5]) if len(sys.argv) > 5 else 150
asyncio.run(run(out, mode, cal, pol, secs, CONDITIONS))
