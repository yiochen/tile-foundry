#!/usr/bin/env node
/** Inspect a self-contained prepare_review.py candidate player at native registration. */
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
const packet=path.resolve(process.argv[2]||'');
if(!process.argv[2])throw new Error('Usage: node tools/inspect_review_playback.mjs REVIEW_PACKET_DIR');
const output=path.join(packet,'browser');await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const errors=[];
try{
  const page=await browser.newPage({viewport:{width:1400,height:1200}});
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(pathToFileURL(path.join(packet,'playback.html')).href);
  await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.frame!==undefined);
  const samples=await page.evaluate(async()=>{
    const out=[],start=performance.now();
    await new Promise(resolve=>{function next(now){out.push({elapsedMs:now-start,frame:Number(document.querySelector('canvas').dataset.frame)});if(now-start>2100)resolve();else requestAnimationFrame(next);}requestAnimationFrame(next);});
    return out;
  });
  const visited=[...new Set(samples.map(s=>s.frame))],wraps=samples.slice(1).filter((s,i)=>s.frame<samples[i].frame).length;
  const seek=async index=>{
    await page.evaluate(index=>{const seek=document.querySelector('#seek');seek.value=index;seek.dispatchEvent(new Event('input'));},index);
    await page.waitForFunction(index=>document.querySelector('canvas').dataset.frame===String(index),index);
  };
  for(let index=0;index<12;index++){
    await seek(index);
    await page.locator('canvas').screenshot({path:path.join(output,`native-${String(index).padStart(2,'0')}.png`)});
  }
  await page.locator('#offset').check();
  for(const index of [0,5,11]){
    await seek(index);
    await page.locator('canvas').screenshot({path:path.join(output,`offset-${String(index).padStart(2,'0')}.png`)});
  }
  await page.locator('#dark').check();await page.selectOption('#scale','2');await seek(0);
  await page.locator('canvas').screenshot({path:path.join(output,'dark-2x.png')});
  await page.setViewportSize({width:390,height:844});await page.selectOption('#scale','1');
  await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  const report={kind:'candidate-browser-playback',input:'../playback.html',fps:12,visitedFrames:visited,wraps,samples,browserErrors:errors,
    note:'Actual candidate sprites at stored roots. No control/reference animation substituted. Screenshots include all 12 phases and phase-offset neighbors.'};
  await writeFile(path.join(output,'inspection.json'),JSON.stringify(report,null,2)+'\n');
  if(errors.length||visited.length!==12||wraps<1)throw new Error('Candidate playback did not complete cleanly');
  console.log(JSON.stringify({packet,visited:visited.length,wraps,errors}));
}finally{await browser.close();}
