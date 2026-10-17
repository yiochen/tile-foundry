import {chromium} from 'playwright';
import {pathToFileURL} from 'node:url';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
const out=path.dirname(new URL(import.meta.url).pathname);
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const errors=[];
try{
 const page=await browser.newPage({viewport:{width:2000,height:1200}});
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(out,'previews/index.html')).href);
 await page.locator('img').evaluateAll(images=>Promise.all(images.map(im=>im.decode())));
 for(const scale of ['1','2']){
  await page.locator('#scale').selectOption(scale);
  await page.locator('#ai').screenshot({path:path.join(out,`previews/source-light-${scale}x.png`)});
  await page.locator('#theme').click();
  await page.locator('#ai').screenshot({path:path.join(out,`previews/source-dark-${scale}x.png`)});
  await page.locator('#theme').click();
 }
 await page.goto(pathToFileURL(path.join(out,'previews/control-playback.html')).href);
 await page.waitForFunction(()=>document.querySelector('canvas').dataset.frame!==undefined);
 const samples=await page.evaluate(async()=>{
  const a=[],start=performance.now();
  while(performance.now()-start<2200){a.push({elapsedMs:performance.now()-start,frame:Number(document.querySelector('canvas').dataset.frame)});await new Promise(r=>requestAnimationFrame(r));}
  return a;
 });
 await page.locator('#play').click();
 for(const scale of ['1','2']){
  await page.locator('#scale').selectOption(scale);
  for(const dark of [false,true]){
   await page.locator('#dark').setChecked(dark);
   for(const frame of [0,11]){
    await page.locator('#seek').fill(String(frame));await page.locator('#seek').dispatchEvent('input');
    await page.locator('canvas').screenshot({path:path.join(out,`previews/control-${dark?'dark':'light'}-${scale}x-frame-${String(frame).padStart(2,'0')}.png`)});
   }
  }
 }
 const mobile=await browser.newPage({viewport:{width:390,height:844},isMobile:true,deviceScaleFactor:1});
 mobile.on('pageerror',e=>errors.push(e.message));
 await mobile.goto(pathToFileURL(path.join(out,'previews/index.html')).href);
 await mobile.locator('img').evaluateAll(images=>Promise.all(images.map(im=>im.decode())));
 await mobile.screenshot({path:path.join(out,'previews/mobile.png'),fullPage:true});
 await writeFile(path.join(out,'previews/browser-receipt.json'),JSON.stringify({ungraded:true,browserVersion:browser.version(),playbackSamples:samples,browserErrors:errors,desktopViewport:[2000,1200],mobileViewport:[390,844],candidatePresentation:'Full untouched source only; no extracted candidate frames',controlFPS:12},null,2)+'\n');
 console.log(JSON.stringify({samples:samples.length,observedFrames:[...new Set(samples.map(s=>s.frame))],browserErrors:errors}));
}finally{await browser.close()}
