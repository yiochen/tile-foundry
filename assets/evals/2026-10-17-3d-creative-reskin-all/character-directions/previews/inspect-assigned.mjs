import path from 'node:path';
import {mkdir, writeFile, readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
const root=path.resolve('assets/evals/2026-10-17-3d-creative-reskin-all');
const cases=['character-directions','dancing-player','animated-waves','animated-lava','authored-flowing-lava'];
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
try {
 for(const id of cases){
  const dir=path.join(root,id,'previews'),out=path.join(dir,'browser');await mkdir(out,{recursive:true});
  const result=JSON.parse(await readFile(path.join(root,id,'result.json'),'utf8'));
  const sourceOnly=!result.sprites.length,errors=[];
  const page=await browser.newPage({viewport:{width:1400,height:1200}});page.on('pageerror',e=>errors.push(e.message));
  const filename=id==='character-directions'?'directions.html':sourceOnly?'source-playback.html':'playback.html';
  await page.goto(pathToFileURL(path.join(dir,filename)).href);
  const report={kind:sourceOnly?'display-only-source-browser-inspection':'runtime-artifact-browser-inspection',sourceOnly,input:filename,browserErrors:errors};
  if(id==='character-directions'){
   await page.waitForFunction(()=>Array.from(document.images).length===8&&Array.from(document.images).every(im=>im.complete&&im.naturalWidth===192));
   await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
   report.displayedDirections=8;
  }else{
   await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.frame!==undefined);
   const samples=await page.evaluate(async()=>{
    const out=[],start=performance.now();
    await new Promise(resolve=>{function next(now){out.push({elapsedMs:now-start,frame:Number(document.querySelector('canvas').dataset.frame)});if(now-start>2100)resolve();else requestAnimationFrame(next);}requestAnimationFrame(next);});return out;
   });
   report.fps=12;report.samples=samples;report.visitedFrames=[...new Set(samples.map(s=>s.frame))];report.wraps=samples.slice(1).filter((s,i)=>s.frame<samples[i].frame).length;
   const seek=async i=>{await page.evaluate(i=>{const e=document.querySelector('#seek');e.value=i;e.dispatchEvent(new Event('input'));},i);await page.waitForFunction(i=>document.querySelector('canvas').dataset.frame===String(i),i);};
   for(let i=0;i<12;i++){await seek(i);await page.locator('canvas').screenshot({path:path.join(out,`native-${String(i).padStart(2,'0')}.png`)});}
   if(id==='authored-flowing-lava'){await page.locator('#offset').check();for(const i of [0,5,11]){await seek(i);await page.locator('canvas').screenshot({path:path.join(out,`offset-${String(i).padStart(2,'0')}.png`)});}}
   await page.locator('#dark').check();await page.selectOption('#scale','2');await seek(0);await page.locator('canvas').screenshot({path:path.join(out,'dark-2x.png')});
   await page.selectOption('#scale','1');await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
   if(sourceOnly){await page.locator('summary').click();await page.locator('#atlas').screenshot({path:path.join(out,'complete-untouched-source.png')});await page.locator('summary').click();}
   if(report.visitedFrames.length!==12||report.wraps<1)throw new Error(id+' did not display all frames and loop');
  }
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  if(errors.length)throw new Error(id+' browser error: '+errors.join('; '));
  await writeFile(path.join(out,'inspection.json'),JSON.stringify(report,null,2)+'\n');
  await page.close();console.log(JSON.stringify({caseId:id,sourceOnly,frames:report.visitedFrames?.length??8,wraps:report.wraps??null,browserErrors:errors}));
 }
}finally{await browser.close();}
