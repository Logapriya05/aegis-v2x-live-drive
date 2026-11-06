"""Record true road-user tracks from the live demo (headless, seeded) to train the GRU twin predictor.

usage: collect_tracks.py OUT.jsonl [SECONDS] [N_RUNS]
  Every 0.1 s of simulated time, the true state (x, z, vx, vz, heading) of every connected vehicle is
  written. Runs use their own seeds (900000 + run), separate from the calibration, selection and
  evaluation seeds, so the GRU is never trained on evaluation traffic. Ego speeds cycle 11 / 16 / 6 m/s.
"""
import asyncio, json, os, pathlib, sys
from playwright.async_api import async_playwright

PAGE = (pathlib.Path(__file__).resolve().parents[2] / 'index.html').as_uri()
THREE = os.environ.get('THREE_DIR')
SEED_JS = """(()=>{let s=%d>>>0;Math.random=function(){s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}})()"""

async def run(out, secs, runs):
    async with async_playwright() as pw:
        b = await pw.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        f = open(out, 'w')
        for k in range(runs):
            ctx = await b.new_context(viewport={'width': 1280, 'height': 800}); await ctx.add_init_script(SEED_JS % (900000 + k))
            pg = await ctx.new_page()
            if THREE:
                await pg.route('**/three.min.js', lambda r: r.fulfill(path=THREE + '/build/three.min.js'))
                async def ex(r): await r.fulfill(path=THREE + '/examples/js/' + r.request.url.split('examples/js/')[1])
                await pg.route('**/examples/js/**', ex); await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
            await pg.goto(PAGE); await pg.wait_for_timeout(2500)
            rows = await pg.evaluate("""([secs,spd])=>{const A=__aegis;window.__noRender=true;document.getElementById('start').hidden=true;A.fastForward(3,null);
              const auto=()=>{const k=A.keys,v=A.ego.v,c=A.crit;k.down=c.ttc<2.5&&v>2;k.up=!k.down&&v<spd};const R=[];
              for(let i=0;i<secs*10;i++){A.fastForward(.1,auto);const tt=+A.t.toFixed(2);
                for(const n of A.vehicles)if(n.connected)R.push([tt,n.id,+n.x.toFixed(3),+n.z.toFixed(3),+(n.vx||0).toFixed(3),+(n.vz||0).toFixed(3),+n.h.toFixed(4)])}
              return R}""", [secs, [11, 16, 6][k % 3]])
            for r in rows: f.write(json.dumps([k] + r) + '\n')
            print(k, len(rows), flush=True); await ctx.close()
        f.close(); await b.close()

asyncio.run(run(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 240, int(sys.argv[3]) if len(sys.argv) > 3 else 6))
