#!/usr/bin/env node
/** Exercise the delivered playback in actual desktop/mobile browsers and retain screenshots/telemetry. */
import path from 'node:path';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
const [caseArg,runtimeArg='.']=process.argv.slice(2);if(!caseArg)throw new Error('Usage: node tools/3d_controls_motion_inspect.mjs CASE_DIR [NODE_PROJECT]');
const base=path.resolve(caseArg),req=createRequire(path.join(path.resolve(runtimeArg),'package.json')),{chromium}=req('playwright');
const server=createServer(async(request,response)=>{try{const url=new URL(request.url,'http://localhost'),requested=path.resolve(base,'.'+decodeURIComponent(url.pathname));if(!requested.startsWith(base+path.sep))throw new Error('Path escape');const bytes=await readFile(requested);response.writeHead(200,{'content-type':requested.endsWith('.html')?'text/html':requested.endsWith('.png')?'image/png':'application/json'});response.end(bytes);}catch{response.writeHead(404);response.end();}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));let browser;const errors=[];
try{
  browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox','--disable-dev-shm-usage']});
  const page=await browser.newPage({viewport:{width:1360,height:1050}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/previews/playback.html`,{waitUntil:'networkidle'});await page.waitForFunction(()=>window.motionPlayer&&document.getElementById('single').width>1);
  const telemetry=await page.evaluate(async()=>{window.motionPlayer.setFrame(0);window.motionPlayer.play();const samples=[],start=performance.now();await new Promise(resolve=>{function sample(){samples.push({elapsedMs:performance.now()-start,frame:window.motionPlayer.frame});if(performance.now()-start>2100)resolve();else requestAnimationFrame(sample);}requestAnimationFrame(sample);});return samples;});
  for(const frame of [0,5,11]){await page.evaluate(n=>window.motionPlayer.setFrame(n),frame);await page.screenshot({path:path.join(base,`previews/browser-desktop-frame-${String(frame).padStart(2,'0')}.png`),fullPage:true});}
  await page.selectOption('#scale','2');await page.selectOption('#bg','dark');await page.evaluate(()=>window.motionPlayer.setFrame(0));await page.screenshot({path:path.join(base,'previews/browser-desktop-dark-2x.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.selectOption('#scale','1');await page.screenshot({path:path.join(base,'previews/browser-mobile.png'),fullPage:true});
  const frames=[...new Set(telemetry.map(s=>s.frame))];const wraps=telemetry.slice(1).filter((s,i)=>s.frame<telemetry[i].frame).length;
  const report={caseDirectory:base,actualBrowser:'Playwright Chromium',desktop:[1360,1050],mobile:[390,844],browserErrors:errors,livePlayback:{durationMs:telemetry.at(-1).elapsedMs,visitedFrames:frames,wraps,expectedFps:12,samples:telemetry},evidence:['browser-desktop-frame-00.png','browser-desktop-frame-05.png','browser-desktop-frame-11.png','browser-desktop-dark-2x.png','browser-mobile.png'],note:'Actual live browser playback sampled for over two seconds. Screenshots complement review of all rendered phases and phase-offset neighbor rasters.'};
  await writeFile(path.join(base,'previews/browser-inspection.json'),JSON.stringify(report,null,2)+'\n');
  if(errors.length||frames.length<8||wraps<1)throw new Error('Browser playback verification failed');
  console.log(JSON.stringify({caseDirectory:base,errors,visitedFrames:frames.length,wraps},null,2));
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
