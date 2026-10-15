import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

export async function verifyEvalGallery(page,root,port){
  const gallery=JSON.parse(await readFile(root+'public/assets/eval-gallery.json','utf8'));
  assert.equal(gallery.cases.length,13);
  assert.equal(gallery.archivedCases.length,0);
  assert.ok(gallery.cases.every(c=>c.latest&&c.latest.sources.length&&c.latest.report),'Every case needs actual source and grade artifacts');
  const url=`http://127.0.0.1:${port}`;
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(url+'/?view=evals',{waitUntil:'networkidle'});
  await page.locator('[data-evals-ready="true"]').waitFor();
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
  assert.equal(await page.locator('[data-eval-case]').count(),13);
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
  await page.getByLabel('Ground anchor',{exact:true}).check();
  await page.getByLabel('Eval sprite',{exact:true}).selectOption('7');
  await page.waitForFunction(()=>document.querySelector('.eval-sprite-preview')?.dataset.frame==='7');
  await page.screenshot({path:root+'docs/preview-evals-desktop.png',fullPage:true});
  await page.locator('[data-eval-case="dancing-player"]').click();
  await page.reload({waitUntil:'networkidle'});
  await page.locator('[data-eval-selected="dancing-player"]').waitFor();
  for(const width of [390,320]){
    await page.setViewportSize({width,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,`Eval ${width}px overflow`);
    await page.locator('[data-eval-case="floating-object"]').click();
    await page.locator('.eval-sprite-preview[data-ready="true"]').waitFor();
    if(width===390)await page.screenshot({path:root+'docs/preview-evals-mobile.png',fullPage:true});
  }
  await page.getByRole('button',{name:'Animations',exact:true}).click();
  await page.locator('[data-evals-ready="true"]').waitFor();
  assert.equal(await page.locator('[data-eval-case]').count(),3);
  assert.equal(await page.locator('.eval-result').count(),1);
  assert.equal(await page.getByRole('button',{name:'Evals',exact:true}).count(),1);
  return {check:'13 cases: registered original SVG overlay and opacity, LLM assessments, original grade history, non-gating diagnostics, exact prompts and sources, registered sprites, failures, direction stepping, deep link, current animations, desktop/mobile',ok:true};
}
