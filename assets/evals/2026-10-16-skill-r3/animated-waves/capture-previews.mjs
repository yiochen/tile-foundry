import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const output=path.dirname(fileURLToPath(import.meta.url));
const browser=await chromium.launch({headless:true});
const errors=[];
for (const [label,viewport] of [['desktop',{width:1180,height:1100}],['mobile',{width:390,height:844}]]) {
  const page=await browser.newPage({viewport,deviceScaleFactor:1});
  page.on('pageerror',error=>errors.push({label,error:String(error)}));
  await page.goto('file://'+output+'/previews/playback.html');
  await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.frame !== undefined);
  await page.locator('#play').click();
  await page.locator('#seek').fill('0');
  await page.screenshot({path:output+'/previews/playback-'+label+'-phase00.png',fullPage:true});
  await page.locator('#offset').check();
  await page.locator('#dark').check();
  await page.locator('#seek').fill('11');
  await page.screenshot({path:output+'/previews/playback-'+label+'-phase11-offset-dark.png',fullPage:true});
  if (label==='desktop') {
    await page.locator('#scale').selectOption('2');
    await page.screenshot({path:output+'/previews/playback-desktop-2x.png',fullPage:true});
    await page.locator('#scale').selectOption('1');
    await page.locator('#offset').uncheck();
    await page.locator('#dark').uncheck();
    await page.locator('#seek').fill('0');
    await page.locator('#play').click();
    const phases=[];
    for(let i=0;i<16;i++) { phases.push(await page.locator('canvas').getAttribute('data-frame')); await page.waitForTimeout(67); }
    await page.evaluate(values=>document.body.dataset.observedPhases=JSON.stringify(values),phases);
    const fs=await import('node:fs/promises');
    await fs.writeFile(output+'/browser-playback-observations.json',JSON.stringify({requestedFps:12,phaseSamplesEveryMs:67,observedPhases:phases,pageErrors:errors},null,2)+'\n');
  }
  await page.close();
}
await browser.close();
console.log(JSON.stringify({screenshots:5,pageErrors:errors}));
