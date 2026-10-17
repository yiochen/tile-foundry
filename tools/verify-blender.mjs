import assert from 'node:assert/strict';

export async function verifyBlender(page,root,port) {
  await page.setViewportSize({width:1440,height:1150});
  await page.goto(`http://127.0.0.1:${port}/?view=blender`,{waitUntil:'networkidle'});
  await page.locator('[data-blender-ready="true"]').waitFor();
  const player=page.locator('.blender-lab [data-player-source="runtime"]').first();
  await player.locator('canvas[data-ready="true"]').waitFor();
  assert.equal(await player.getAttribute('data-frame-count'),'24');
  const seek=player.getByLabel('Sprite progress');
  await seek.focus();await seek.press('End');
  await page.waitForFunction(()=>document.querySelector('.blender-lab .eval-player canvas').dataset.frame==='23');
  await player.getByLabel('Play sprite sequence').click();
  await page.waitForFunction(()=>Number(document.querySelector('.blender-lab .eval-player canvas').dataset.frame)<5);
  await player.getByLabel('Pause sprite sequence').click();
  await seek.focus();await seek.press('Home');
  await page.waitForFunction(()=>document.querySelector('.blender-lab .eval-player canvas').dataset.frame==='0');
  await page.getByLabel('Ground anchor',{exact:true}).check();
  assert.equal(await player.locator('canvas').getAttribute('data-anchor'),'96,248');
  await page.screenshot({path:root+'docs/preview-blender-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Inspect the animated 3D model'}).click();
  await page.locator('.blender-model[data-model-ready="true"]').waitFor({timeout:30000});
  await page.locator('.blender-model').screenshot({path:root+'docs/preview-blender-model.png'});
  await page.getByRole('button',{name:'Close 3D inspection'}).click();
  await page.getByText('Blender MCP screenshots · before, after and animation validation',{exact:true}).click();
  assert.equal(await page.locator('.blender-source').first().locator('figure').count(),3);
  await page.getByText('Blender MCP screenshots · before, after and animation validation',{exact:true}).click();
  for(const width of [390,320]) {
    await page.setViewportSize({width,height:844});
    await page.evaluate(()=>new Promise(requestAnimationFrame));
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`Blender ${width}px overflow`);
    if(width===390)await page.screenshot({path:root+'docs/preview-blender-mobile.png',fullPage:true});
  }
  return {check:'Blender prototype: 24-frame scrub and loop, fixed root, animated GLB, MCP evidence, desktop and mobile',ok:true};
}
