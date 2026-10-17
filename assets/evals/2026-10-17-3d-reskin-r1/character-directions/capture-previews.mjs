import {createRequire} from 'node:module';
import {writeFile} from 'node:fs/promises';
const require=createRequire('/Users/yiouchen/.codex/worktrees/1834/tile-foundry/package.json');
const {chromium}=require('playwright');
const root='/Users/yiouchen/.codex/worktrees/1834/tile-foundry/assets/evals/2026-10-17-3d-reskin-r1/character-directions';
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const errors=[];
const captures=[];
try{
 for(const [name,size] of [['desktop',{width:1280,height:1000}],['mobile',{width:390,height:844}]]){
  const page=await browser.newPage({viewport:size,deviceScaleFactor:1});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('file://'+root+'/previews/index.html',{waitUntil:'load'});
  await page.locator('img').evaluateAll(images=>Promise.all(images.map(image=>image.decode())));
  await page.screenshot({path:root+'/previews/screenshot-'+name+'.png',fullPage:true});
  if(name==='mobile'){
   await page.locator('h2').nth(1).scrollIntoViewIfNeeded();
   await page.screenshot({path:root+'/previews/screenshot-mobile-ai-viewport.png'});
  }
  captures.push({viewport:name,size,imageCount:await page.locator('img').count(),horizontalOverflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),pageHeight:await page.evaluate(()=>document.documentElement.scrollHeight)});
  await page.close();
 }
 await writeFile(root+'/previews/browser-capture.json',JSON.stringify({renderEngine:'Playwright Chromium',captures,errors},null,2)+'\n');
 console.log(JSON.stringify({captures,errors},null,2));
}finally{await browser.close();}