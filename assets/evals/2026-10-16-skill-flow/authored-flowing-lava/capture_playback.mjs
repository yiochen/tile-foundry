import { chromium } from 'playwright';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';
import { writeFile } from 'node:fs/promises';
const output=dirname(fileURLToPath(import.meta.url)), preview=join(output,'previews');
const browser=await chromium.launch({headless:true});
const observations=[];
for(const mobile of [false,true]){
 const label=mobile?'mobile':'desktop';
 const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1200,height:1000},deviceScaleFactor:1,recordVideo:{dir:join(preview,`video-${label}`),size:mobile?{width:390,height:844}:{width:1200,height:1000}}});
 const page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(join(preview,'playback.html')).href);
 await page.waitForFunction(()=>document.querySelector('#view').dataset.frame!==undefined);
 await page.locator('#offset').check();
 await page.screenshot({path:join(preview,`playback-${label}-offset.png`),fullPage:true});
 const samples=await page.evaluate(async()=>{
  const result=[],start=performance.now();
  while(performance.now()-start<2100){result.push({elapsedMs:performance.now()-start,frame:Number(document.querySelector('#view').dataset.frame)});await new Promise(resolve=>requestAnimationFrame(resolve));}
  return result;
 });
 await page.screenshot({path:join(preview,`playback-${label}-offset-later.png`),fullPage:true});
 await page.locator('#scale').selectOption('2');
 await page.screenshot({path:join(preview,`playback-${label}-offset-2x.png`),fullPage:true});
 observations.push({surface:label,viewport:await page.viewportSize(),pageErrors:errors,samples,observedFrameIndices:[...new Set(samples.map(x=>x.frame))],videoPath:await page.video().path()});
 await context.close();
}
await browser.close();
await writeFile(join(output,'playback-capture.json'),JSON.stringify({purpose:'Ungraded browser playback evidence',declaredFPS:12,observations},null,2)+'\n');
console.log(JSON.stringify(observations.map(({surface,pageErrors,observedFrameIndices,videoPath})=>({surface,pageErrors,observedFrameIndices,videoPath})),null,2));
