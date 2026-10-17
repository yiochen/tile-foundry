import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

export async function verifyPlaybackClock(page){
  // A frame timestamp can precede the performance.now() call that schedules it.
  // Drive RAF independently to cover that boundary and the complete 12 fps loop.
  await page.getByRole('slider',{name:'Sprite progress',exact:true}).press('Home');
  // Initialize Playwright's polling with native RAF before temporarily replacing it.
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.ready==='true');
  await page.evaluate(()=>{
    const originalRequest=window.requestAnimationFrame,originalCancel=window.cancelAnimationFrame;
    const clock={callbacks:new Map(),nextId:1,firstRequest:null};
    window.requestAnimationFrame=callback=>{
      clock.firstRequest??=performance.now();
      const id=clock.nextId++;clock.callbacks.set(id,callback);return id;
    };
    window.cancelAnimationFrame=id=>clock.callbacks.delete(id);
    clock.restore=()=>{
      window.requestAnimationFrame=originalRequest;window.cancelAnimationFrame=originalCancel;
      delete window.evalPlaybackClock;
    };
    window.evalPlaybackClock=clock;
    document.querySelector('button[aria-label="Play sprite sequence"]').click();
  });
  try{
    await page.waitForFunction(()=>window.evalPlaybackClock.callbacks.size>0,{},{polling:10});
    for(const [elapsed,frame] of [[0,0],[84,1],[917,11],[1000,0]]){
      await page.evaluate(elapsed=>{
        const clock=window.evalPlaybackClock,callbacks=[...clock.callbacks.values()];
        clock.callbacks.clear();
        callbacks.forEach(callback=>callback(clock.firstRequest-16+elapsed));
      },elapsed);
      await page.waitForFunction(frame=>{
        const canvas=document.querySelector('.eval-sprite-preview');
        return canvas?.dataset.ready==='true'&&canvas.dataset.frame===String(frame);
      },frame,{polling:10});
      assert.equal(await page.getByRole('slider',{name:'Sprite progress',exact:true}).inputValue(),String(frame));
    }
    await page.evaluate(()=>document.querySelector('button[aria-label="Pause sprite sequence"]').click());
    await page.waitForFunction(()=>window.evalPlaybackClock.callbacks.size===0,{},{polling:10});
    assert.equal(await page.locator('.eval-player').getAttribute('data-playing'),'false');
  }finally{await page.evaluate(()=>window.evalPlaybackClock.restore());}
}

export async function verifyEvalGallery(page,root,port){
  const gallery=JSON.parse(await readFile(root+'public/assets/eval-gallery.json','utf8'));
  const suite=JSON.parse(await readFile(root+'skills/build-overlap-tiles/evals/cases.json','utf8'));
  assert.equal(gallery.cases.length,suite.cases.length);
  assert.equal(gallery.archivedCases.length,0);
  assert.ok(gallery.cases.every(c=>c.latest&&c.latest.sources.length&&c.latest.report),'Every case needs actual source and grade artifacts');
  const url=`http://127.0.0.1:${port}`;
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(url+'/?view=evals',{waitUntil:'networkidle'});
  await page.locator('[data-evals-ready="true"]').waitFor();
  await page.locator('[data-eval-case="authored-flowing-lava"]').click();
  await page.locator('.eval-player[data-frame-count="12"]').waitFor();
  await verifyPlaybackClock(page);
  const floor = gallery.cases.find(c=>c.id==='seamless-square-floor');
  assert.equal(floor.latest.policy,'llm-visual-v1');
  assert.ok(floor.trials.length>=2);
  assert.notEqual(floor.latest.report,floor.trials[0].report);
  await page.locator('[data-eval-case="seamless-square-floor"]').click();
  await page.locator('[data-eval-policy="llm-visual-v1"]').waitFor();
  assert.equal(await page.locator('.eval-diagnostics').count(),1);
  assert.ok((await page.locator('.eval-diagnostics summary').innerText()).includes('do not affect grade'));
  await page.getByLabel('Eval attempt',{exact:true}).selectOption(floor.trials[0].id);
  await page.locator('[data-eval-policy="original"]').waitFor();
  assert.equal(await page.getByRole('link',{name:'Full eval report',exact:false}).getAttribute('href'),'/assets/'+floor.trials[0].report);
  await page.getByLabel('Eval attempt',{exact:true}).selectOption(floor.latest.id);
  await page.locator('[data-eval-policy="llm-visual-v1"]').waitFor();
  await page.locator('[data-eval-case="partial-cell-tall-object"]').click();
  const lantern = gallery.cases.find(c=>c.id==='partial-cell-tall-object');
  assert.equal(lantern.latest.guideOverlay.heightPx,160);
  assert.deepEqual(lantern.latest.guideOverlay.anchor,[96,248]);
  await page.locator('.eval-sprite-preview[data-ready="true"]').waitFor();
  const originalPreview = await page.locator('.eval-sprite-preview').evaluate(c=>({
    pixels:c.toDataURL(),size:[c.width,c.height],anchor:c.dataset.anchor}));
  await page.getByLabel('SVG guide overlay',{exact:true}).check();
  await page.locator('.eval-sprite-preview[data-guide-overlay="true"]').waitFor();
  const overlaid = await page.locator('.eval-sprite-preview').evaluate(c=>({
    pixels:c.toDataURL(),size:[c.width,c.height],anchor:c.dataset.anchor,guideAnchor:c.dataset.guideAnchor}));
  assert.notEqual(overlaid.pixels,originalPreview.pixels);
  assert.deepEqual(overlaid.size,originalPreview.size);
  assert.equal(overlaid.anchor,originalPreview.anchor);
  assert.equal(overlaid.guideAnchor,'96,248');
  assert.equal(await page.getByRole('link',{name:'Original SVG',exact:false}).getAttribute('href'),'/assets/'+lantern.latest.guideOverlay.image);
  await page.getByLabel('SVG overlay opacity',{exact:true}).press('ArrowLeft');
  await page.locator('.eval-sprite-preview[data-guide-opacity="60"]').waitFor();
  await page.locator('.eval-overlay-comparison').screenshot({path:root+'docs/preview-eval-lantern-overlay.png'});
  await page.reload({waitUntil:'networkidle'});
  await page.locator('.eval-sprite-preview[data-guide-overlay="true"]').waitFor();
  await page.setViewportSize({width:390,height:844});
  await page.locator('.eval-overlay-comparison').scrollIntoViewIfNeeded();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'SVG overlay mobile overflow');
  await page.locator('.eval-overlay-comparison').screenshot({path:root+'docs/preview-eval-lantern-overlay-mobile.png'});
  await page.getByLabel('SVG guide overlay',{exact:true}).uncheck();
  await page.locator('.eval-sprite-preview[data-guide-overlay="false"]').waitFor();
  assert.equal(await page.locator('.eval-sprite-preview').evaluate(c=>c.toDataURL()),originalPreview.pixels);
  await page.setViewportSize({width:1440,height:1000});
  assert.equal(await page.locator('[data-eval-case]').count(),gallery.cases.length);
  for(const entry of gallery.cases){
    await page.locator(`[data-eval-case="${entry.id}"]`).click();
    await page.locator(`[data-eval-selected="${entry.id}"]`).waitFor();
    assert.equal((await page.locator('.eval-user-prompt pre').innerText()).trim(),entry.latest.prompt.trim());
    assert.equal(await page.locator('.eval-result').getAttribute('data-eval-trial'),entry.latest.id);
    assert.ok((await page.locator('.eval-result-heading').innerText()).includes(entry.latest.runId));
    assert.equal(await page.getByRole('link',{name:'Full eval report',exact:false}).getAttribute('href'),'/assets/'+entry.latest.report);
    const original=page.getByAltText('Original generation 1',{exact:true});
    await original.scrollIntoViewIfNeeded();
    await page.waitForFunction(()=>document.querySelector('img[alt="Original generation 1"]')?.naturalWidth>0);
    await page.locator('.eval-prompt').first().locator('summary').click();
    assert.equal(await page.locator('.eval-prompt pre').first().innerText(),entry.latest.sources[0].prompt);
    const report=await page.request.get(url+'/assets/'+entry.latest.report);
    assert.ok(report.ok());assert.equal((await report.json()).status,entry.latest.status);
    if(entry.latest.sprites.length){
      await page.locator('.eval-sprite-preview[data-ready="true"]').waitFor();
      assert.equal(await page.locator('.eval-sprite-preview').getAttribute('data-anchor'),entry.latest.sprites[0].anchor.join(','));
    }else{
      assert.ok((await page.locator('.eval-result').innerText()).includes('No processed sprites were delivered'));
    }
  }
  await page.locator('[data-eval-case="character-directions"]').click();
  const directionsPlayer=gallery.cases.find(c=>c.id==='character-directions').trials.findLast(t=>t.sprites.length===8);
  assert.ok(directionsPlayer,'Preserved direction player fixture');
  await page.getByLabel('Eval attempt',{exact:true}).selectOption(directionsPlayer.id);
  await page.getByLabel('Ground anchor',{exact:true}).check();
  const progress=page.getByRole('slider',{name:'Sprite progress',exact:true});
  await progress.scrollIntoViewIfNeeded();
  const track=await progress.boundingBox();
  await page.mouse.move(track.x+8,track.y+track.height/2);
  await page.mouse.down();
  await page.mouse.move(track.x+track.width-8,track.y+track.height/2,{steps:12});
  await page.mouse.up();
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame==='7');
  assert.equal(await progress.inputValue(),'7');
  assert.equal(await page.locator('.eval-player').getAttribute('data-playing'),'false');
  assert.equal(await page.locator('.eval-sprite-preview').getAttribute('data-anchor'),'96,248');
  await page.getByRole('button',{name:'Play sprite sequence',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame==='0');
  await page.getByRole('button',{name:'Pause sprite sequence',exact:true}).click();
  const held=await progress.inputValue();
  await page.waitForTimeout(200);
  assert.equal(await progress.inputValue(),held,'Pause must hold the selected frame');
  await progress.press('End');
  await page.getByRole('button',{name:'Next sprite',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame==='0');
  await page.getByRole('button',{name:'Previous sprite',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame==='7');
  await page.getByLabel('Eval sprite',{exact:true}).selectOption('7');
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame==='7');
  await page.locator('.eval-player').screenshot({path:root+'docs/preview-eval-player-desktop.png'});
  await page.screenshot({path:root+'docs/preview-evals-desktop.png',fullPage:true});
  await page.locator('[data-eval-case="seated-character-separated"]').click();
  await page.locator('.eval-player[data-player-source="raw"][data-frame-count="2"]').waitFor();
  await page.getByRole('slider',{name:'Sprite progress',exact:true}).press('End');
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame==='1');
  await page.locator('[data-eval-case="dancing-player"]').click();
  const rawDance=gallery.cases.find(c=>c.id==='dancing-player').trials.findLast(t=>t.previewSequence?.frames.length===12);
  assert.ok(rawDance,'Preserved raw dance fixture');
  await page.getByLabel('Eval attempt',{exact:true}).selectOption(rawDance.id);
  await page.locator('.eval-player[data-player-source="raw"][data-frame-count="12"]').waitFor();
  assert.ok((await page.locator('.eval-player-note').innerText()).includes('not normalized runtime sprites'));
  await page.getByRole('slider',{name:'Sprite progress',exact:true}).press('End');
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame==='11');
  await page.locator('.eval-player').screenshot({path:root+'docs/preview-eval-raw-player-desktop.png'});
  await page.reload({waitUntil:'networkidle'});
  await page.locator('[data-eval-selected="dancing-player"]').waitFor();
  await page.locator('.eval-sprite-preview[data-ready="true"][data-frame="0"]').waitFor();
  for(const width of [390,320]){
    await page.setViewportSize({width,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,`Eval ${width}px overflow`);
    await page.locator('[data-eval-case="floating-object"]').click();
    await page.locator('.eval-sprite-preview[data-ready="true"]').waitFor();
    if(width===390)await page.screenshot({path:root+'docs/preview-evals-mobile.png',fullPage:true});
  }
  await page.getByRole('button',{name:'Animations',exact:true}).click();
  await page.locator('[data-evals-ready="true"]').waitFor();
  const animations=gallery.cases.filter(c=>c.kind==='animation');
  assert.equal(await page.locator('[data-eval-case]').count(),animations.length);
  assert.equal(await page.locator('.eval-result').count(),1);
  assert.equal(await page.getByRole('button',{name:'Evals',exact:true}).count(),1);
  for(const {id} of animations){
    const entry=gallery.cases.find(c=>c.id===id);
    const runtime=entry.latest.sprites.length>0;
    if(runtime)assert.equal(entry.latest.sprites.length,12);
    else{
      assert.equal(entry.latest.previewSequence.isProcessedSprite,false);
      assert.equal(entry.latest.previewSequence.frames.length,12);
    }
    await page.locator(`[data-eval-case="${id}"]`).click();
    await page.locator(`.eval-player[data-player-source="${runtime?'runtime':'raw'}"][data-frame-count="12"]`).waitFor();
    await page.getByRole('slider',{name:'Sprite progress',exact:true}).press('End');
    await page.locator('.eval-sprite-preview[data-ready="true"][data-frame="11"]').waitFor();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`Raw player overflow: ${id}`);
    await page.getByRole('button',{name:'Play sprite sequence',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame!=='11');
    await page.getByRole('button',{name:'Pause sprite sequence',exact:true}).click();
  }
  const touchContext=await page.context().browser().newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});
  try{
    const touch=await touchContext.newPage();
    await touch.goto(url+'/?view=evals&case=character-directions',{waitUntil:'networkidle'});
    await touch.getByLabel('Eval attempt',{exact:true}).selectOption(directionsPlayer.id);
    const slider=touch.getByRole('slider',{name:'Sprite progress',exact:true});
    await slider.scrollIntoViewIfNeeded();
    const rect=await slider.boundingBox(),session=await touchContext.newCDPSession(touch);
    await session.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:rect.x+8,y:rect.y+rect.height/2}]});
    for(let step=1;step<=8;step++)await session.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:rect.x+8+(rect.width-16)*step/8,y:rect.y+rect.height/2}]});
    await session.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await touch.locator('.eval-sprite-preview[data-ready="true"][data-frame="7"]').waitFor();
    assert.equal(await slider.inputValue(),'7');
    assert.equal(await touch.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await touch.locator('.eval-player').screenshot({path:root+'docs/preview-eval-player-mobile.png'});
  }finally{await touchContext.close();}
  return {check:`${gallery.cases.length} cases: early RAF timestamp regression, 12 fps player, mouse/touch scrubbing, runtime and preserved raw playback, SVG overlay, LLM assessments, history, exact prompts/sources, desktop/mobile`,ok:true};
}
