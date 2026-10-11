import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

// Replay real generated eval artifacts in a browser, using their stored anchors.
export async function verifySkillEvals(browser,root) {
  const run='2026-10-11-skill-v1';
  const dir=root+`assets/evals/${run}/`;
  const result=JSON.parse(await readFile(dir+'dancing-player-retry/processed-recovered/result.json','utf8'));
  const sourceUri=async path=>'data:image/png;base64,'+(await readFile(path)).toString('base64');
  const floor=await sourceUri(dir+'lava-tile/tile.png');
  const frames=await Promise.all(result.frames.map(async f=>({...f,url:await sourceUri(dir+'dancing-player-retry/processed-recovered/'+f.image)})));
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  try {
    await page.bringToFront();
    await page.setContent(`<html><head><style>
      *{box-sizing:border-box}body{margin:0;padding:24px;background:#f4f6ef;color:#21352d;font:15px system-ui}h1{font-size:25px}p{line-height:1.5;color:#637268}.cases{display:flex;gap:24px;flex-wrap:wrap}article{padding:20px;border:1px solid #cbd5c7;border-radius:12px;background:#fff;max-width:100%}.lava{width:430px}.lava img{display:block;width:100%;max-width:384px}.playback{display:flex;gap:12px;flex-wrap:wrap}canvas{display:block;width:256px;max-width:100%;height:auto;border-radius:6px}.panel{max-width:100%}h2{font-size:20px}.label{font-size:12px}b{color:#b72e74}@media(max-width:600px){body{padding:14px}article{padding:14px}.playback{gap:16px}}
      </style></head><body><h1>Tile skill — fresh eval artifacts</h1><p>One floor and a six-frame dance. The pink cross is the stored ground anchor.</p><div class="cases"><article class="lava"><h2>Lava floor</h2><p>128 × 128 · opaque square · 3 × 3 repeat</p><img id="lava" alt="Real generated lava tile repeated three by three"/></article><article><h2>Dancing player</h2><p>Six distinct poses · 8 fps · anchor <b>96, 248</b></p><div class="playback"><div class="panel"><canvas id="light" width="256" height="384"></canvas><p class="label">Light ground</p></div><div class="panel"><canvas id="dark" width="256" height="384"></canvas><p class="label">Dark ground</p></div></div><p id="frame">Loading</p><p>Separate panels recovered at transparent separators. Mixed edges are approximate; the wrap is abrupt.</p></article></div></body></html>`);
    await page.evaluate(async ({floor,frames})=>{
      const imgs=await Promise.all(frames.map(async f=>{const i=new Image();i.src=f.url;await i.decode();return i;}));
      const tile=new Image();tile.src=floor;await tile.decode();
      const repeat=document.createElement('canvas');repeat.width=384;repeat.height=384;
      const r=repeat.getContext('2d');for(let y=0;y<3;y++)for(let x=0;x<3;x++)r.drawImage(tile,x*128,y*128);
      document.getElementById('lava').src=repeat.toDataURL();
      window.seenFrames=new Set();
      // Advance sequentially so timer throttling cannot repeatedly sample only
      // every other pose from a wall-clock frame calculation.
      function draw(i){
        window.seenFrames.add(i);
        for(const name of ['light','dark']){
          const c=document.getElementById(name),ctx=c.getContext('2d');
          ctx.fillStyle=name==='dark'?'#18222e':'#f4f6ef';ctx.fillRect(0,0,256,384);
          ctx.fillStyle=name==='dark'?'#283543':'#dfe5dc';ctx.fillRect(64,200,128,128);
          ctx.strokeStyle='#6b7f70';ctx.strokeRect(64.5,200.5,127,127);
          ctx.drawImage(imgs[i],128-frames[i].anchor[0],264-frames[i].anchor[1]);
          ctx.strokeStyle='#b72e74';ctx.beginPath();ctx.moveTo(120,264);ctx.lineTo(136,264);ctx.moveTo(128,256);ctx.lineTo(128,272);ctx.stroke();
          c.dataset.frame=String(i);
        }
        document.getElementById('frame').textContent=`Frame ${i+1} / ${frames.length}`;
        setTimeout(()=>draw((i+1)%frames.length),frames[i].durationMs);
      }
      draw(0);
    },{floor,frames});
    await page.waitForFunction(()=>window.seenFrames?.size===6);
    assert.equal(await page.locator('canvas[data-frame]').count(),2);
    await page.screenshot({path:root+`docs/evals/${run}/preview-desktop.png`,fullPage:true});
    for(const width of [390,320]){
      await page.setViewportSize({width,height:844});
      await page.evaluate(()=>new Promise(requestAnimationFrame));
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`Eval preview overflow at ${width}`);
      if(width===390)await page.screenshot({path:root+`docs/evals/${run}/preview-mobile.png`,fullPage:true});
    }
    return {check:'fresh skill eval floor repeat and six anchored dance frames, light/dark playback, desktop/mobile',ok:true};
  } finally {await page.close();}
}
