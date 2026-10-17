/** Browser playback evidence; frame PNGs are never changed. */
import {createRequire} from 'node:module';
import {pathToFileURL, fileURLToPath} from 'node:url';
import path from 'node:path';
import {writeFile} from 'node:fs/promises';
const root = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(root, '../../../../package.json'));
const {chromium} = require('playwright');
const browser = await chromium.launch({headless:true, args:['--no-sandbox']});
const observations=[];
try {
  for(const label of ['reskin','direct3d']) {
    const page = await browser.newPage({viewport:{width:1000,height:1000}, deviceScaleFactor:1});
    const errors=[];
    page.on('pageerror', e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(root, `previews/${label}-playback.html`)).href);
    await page.waitForFunction(()=>document.querySelector('canvas').dataset.frame!==undefined);
    const samples=[];
    for(let i=0;i<18;i++) {
      samples.push(await page.locator('canvas').getAttribute('data-frame'));
      await page.waitForTimeout(83);
    }
    await page.locator('#seek').fill('11');
    await page.locator('#seek').dispatchEvent('input');
    await page.screenshot({path:path.join(root,`previews/${label}-desktop-last-frame.png`),fullPage:true});
    for(const scale of ['1','2']) for(const dark of [false,true]) {
      await page.locator('#scale').selectOption(scale);
      await page.locator('#dark').setChecked(dark);
      await page.locator('#seek').fill('0');
      await page.locator('#seek').dispatchEvent('input');
      await page.screenshot({path:path.join(root,`previews/${label}-browser-${dark?'dark':'light'}-${scale}x.png`),fullPage:true});
    }
    await page.setViewportSize({width:390,height:844});
    await page.locator('#scale').selectOption('1');
    await page.locator('#dark').setChecked(false);
    await page.screenshot({path:path.join(root,`previews/${label}-mobile.png`),fullPage:true});
    observations.push({label, framesObservedDuringPlayback:samples, uniqueFramesObserved:[...new Set(samples)], browserErrors:errors, storedFps:12, screenshotScales:[1,2], mobileViewport:[390,844]});
    await page.close();
  }
} finally { await browser.close(); }
await writeFile(path.join(root,'playback-observations.json'), JSON.stringify({version:1,visualGrade:null,observations},null,2)+'\n');
console.log(JSON.stringify(observations,null,2));
