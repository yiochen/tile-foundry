#!/usr/bin/env node
/** Self-contained direct modeled 3D controls for the nine static eval cases. */
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {readFile,writeFile,mkdir,readdir,copyFile,access} from 'node:fs/promises';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_CASES=path.resolve(HERE,'../skills/build-overlap-tiles/evals/cases.json');
const sha=b=>createHash('sha256').update(b).digest('hex');
const json=(file,data,compact=false)=>writeFile(file,JSON.stringify(data,null,compact?0:2)+'\n');
const png=(file,url)=>writeFile(file,Buffer.from(url.split(',')[1],'base64'));
export function parseArgs(argv){
  const [caseId,output,...rest]=argv;if(!caseId||!output)throw Error('Usage: node tools/3d_controls_static.mjs CASE_ID OUTPUT_DIR [--runtime-root DIR] [--suite FILE] [--scale 2]');
  const opts={caseId,output:path.resolve(output),runtimeRoot:path.resolve(HERE,'..'),suite:DEFAULT_CASES,supersample:2};
  for(let i=0;i<rest.length;i+=2){if(rest[i+1]===undefined)throw Error('Missing option value');if(rest[i]==='--scale')opts.supersample=Number(rest[i+1]);else if(rest[i]==='--runtime-root')opts.runtimeRoot=path.resolve(rest[i+1]);else if(rest[i]==='--suite')opts.suite=path.resolve(rest[i+1]);else throw Error('Unknown option '+rest[i]);}
  if(![1,2,3,4].includes(opts.supersample))throw Error('Scale must be 1..4');return opts;
}
export async function run(options){
  const suite=JSON.parse(await readFile(options.suite)),entry=suite.cases.find(c=>c.id===options.caseId);if(!entry)throw Error('Unknown case');
  try{const files=await readdir(options.output);if(files.some(f=>f!=='request.txt'))throw Error('Output is not empty (request.txt is allowed); retain previous attempts');}catch(e){if(e.code!=='ENOENT')throw e;}
  const dependency=createRequire(path.join(options.runtimeRoot,'package.json')),{chromium}=dependency('playwright'),threeRoot=path.resolve(path.dirname(dependency.resolve('three')),'..');
  const names=['3d_controls_static.mjs','3d_controls_static_scene.js','3d_controls_static_rig.js'];
  const server=createServer(async(req,res)=>{try{const url=new URL(req.url,'http://localhost');let data,type='text/javascript';
    if(url.pathname==='/'){type='text/html';data='<!doctype html><title>Fresh direct static 3D controls</title><script type="importmap">'+JSON.stringify({imports:{three:'/three/build/three.module.js','three/addons/':'/three/examples/jsm/'}})+'</script><script type="module" src="/3d_controls_static_scene.js"></script>';}
    else if(names.includes(url.pathname.slice(1)))data=await readFile(path.join(HERE,url.pathname.slice(1)));
    else if(url.pathname.startsWith('/three/')){const f=path.resolve(threeRoot,'.'+url.pathname.slice(6));if(!f.startsWith(threeRoot+path.sep))throw Error('Path escape');data=await readFile(f);}
    else if(url.pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}else{res.writeHead(404);res.end();return;}res.writeHead(200,{'content-type':type});res.end(data);
  }catch(e){res.writeHead(500);res.end(String(e));}});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));let browser;
  try{
    browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader']});
    const page=await browser.newPage({viewport:{width:800,height:800}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    await page.goto(`http://127.0.0.1:${server.address().port}`,{waitUntil:'networkidle'});await page.waitForFunction(()=>typeof window.renderStatic==='function');
    const renderOptions={caseId:entry.id,expected:entry.expected,supersample:options.supersample};
    const data=await page.evaluate(o=>window.renderStatic(o),renderOptions);if(errors.length)throw Error(errors.join('\n'));
    for(const dir of ['', 'sprites','render','render/highres','render/depth-pieces','scene','previews'])await mkdir(path.join(options.output,dir),{recursive:true});
    const byId=Object.fromEntries(data.captures.map(c=>[c.id,c]));
    for(const c of data.captures){await png(path.join(options.output,'render',c.id+'.png'),c.color);await png(path.join(options.output,'render/highres',c.id+'.png'),c.high);}
    const layered=entry.kind==='layered';const selected=layered?['stool','character']:['whole'];
    const sourceRecords=[];
    for(let i=0;i<selected.length;i++){
      const id=selected[i],c=byId[id],source=`source-${String(i+1).padStart(2,'0')}.png`,recipe=`generation-${String(i+1).padStart(2,'0')}.json`;
      await png(path.join(options.output,source),c.high);await png(path.join(options.output,'sprites',id+'.png'),c.color);
      sourceRecords.push({image:source,recipe,role:'whole-asset'});
    }
    await json(path.join(options.output,'guide.json'),data.registration);await json(path.join(options.output,'scene/model.json'),data.scene,true);
    await json(path.join(options.output,'scene/case.json'),entry);
    await json(path.join(options.output,'scene/render-options.json'),renderOptions);
    for(const name of names)await copyFile(path.join(HERE,name),path.join(options.output,'scene',name));
    await copyFile(path.join(HERE,'3d_controls_static_previews.py'),path.join(options.output,'scene','3d_controls_static_previews.py'));
    let tileTools=path.join(HERE,'tile_tools.py');
    try{await access(tileTools);}catch{tileTools=path.resolve(HERE,'../skills/build-overlap-tiles/scripts/tile_tools.py');}
    await copyFile(tileTools,path.join(options.output,'scene','tile_tools.py'));
    await json(path.join(options.output,'scene/package.json'),{name:'fresh-direct-static-3d-control',private:true,type:'module',dependencies:{three:JSON.parse(await readFile(path.join(threeRoot,'package.json'))).version,playwright:dependency('playwright/package.json').version}});
    const groundMetadata={footprint:entry.expected.footprint,occupiedCells:entry.expected.occupiedCells};
    const sprites=selected.map(id=>{const b=byId[id].bounds;return{id:id==='whole'?entry.id:id,image:`sprites/${id}.png`,size:entry.expected.size,anchor:entry.expected.anchor,...groundMetadata,elevationPx:entry.expected.layerElevationPx?.[id]??entry.expected.elevationPx,artRect:b?[b[0],b[1],b[2]-b[0],b[3]-b[1]]:null,
      registration:{method:'authored-3d-projection',guide:'guide.json',sourceImage:sourceRecords[selected.indexOf(id)].image,sourceScale:options.supersample,noPerObjectFit:true},
      ...(entry.expected.baseSize?{baseSize:entry.expected.baseSize}:{}),...(entry.expected.groundClearancePx?{groundClearancePx:entry.expected.groundClearancePx}:{}),
      ...(layered?{role:id}:{}),...(id==='character'?{supportElevationPx:48,supportElevationBakedIntoArt:true,attachmentPoint:[96,220.48],attachmentWorld:[0,.375,.16],anchorMode:'projected-ground-under-support',nominalStandingHeightPx:160}:{})};});
    const result={version:2,kind:entry.kind,projection:'top-down-oblique-square-grid',cellSize:128,groundAnchorAlignment:'center',workflow:'fresh-direct-modeled-3d-control',sprites,
      ...(entry.expected.supportCells?{supportCells:entry.expected.supportCells}:{}),...(entry.expected.overheadCells?{overheadCells:entry.expected.overheadCells}:{}),
      ...(entry.expected.depthPiecesRequired?{depthPieces:['arch-rear','arch-front'].map((id,i)=>({id,image:`render/${id}.png`,size:entry.expected.size,anchor:entry.expected.anchor,drawOrder:i*2,worldZInterval:i===0?[-.5,0]:[0,.5],geometrySource:'scene/model.json',derivation:'Independently modeled and rendered world-depth half; no raster slicing'}))}:{}),
      processing:{operation:'supersampled render capture',wholeCanvasUniformScale:1/options.supersample,perFrameFit:false,cameraFit:false,rootFit:false,crop:false,colorKey:false,silhouetteMask:false},
      provenance:{imageGenerationCalls:0,artwork:'Fresh authored Three.js geometry and procedural 3D materials',editableScene:'scene/model.json',runnableSource:'scene/3d_controls_static.mjs'}};
    await json(path.join(options.output,'result.json'),result);
    const inputRefs=['scene/render-options.json','scene/3d_controls_static_scene.js','scene/3d_controls_static_rig.js'];
    for(const record of sourceRecords){const sourceBytes=await readFile(path.join(options.output,record.image)),references=[...inputRefs];
      const hashes={},roles={};for(const ref of references){hashes[ref]=sha(await readFile(path.join(options.output,ref)));roles[ref]='Actual authored renderer input: render parameters or editable geometry/camera/rig source; no image-model/style reference call';}
      await json(path.join(options.output,record.recipe),{prompt:`Direct modeled Three.js control for ${entry.id}. Render the requested ${layered?(record.image==='source-01.png'?'complete stool only':'seated character only'):'subject'} with fixed authored camera, no image generation. Case request: ${entry.prompt.replace('{{OUTPUT_DIR}}',options.output)}`,tool:'Three.js WebGLRenderer via Playwright Chromium; authored procedural model',transparentBackground:entry.kind!=='floor',sourceSHA256:sha(sourceBytes),references,referenceSHA256:hashes,referenceRoles:roles,imageGenerationCalls:0,generationCalls:0,sourceRole:'Untouched supersampled direct render capture',caseRequest:entry.prompt.replace('{{OUTPUT_DIR}}',options.output),renderParameters:{supersample:options.supersample,cellSize:128,frame:entry.expected.size,anchor:entry.expected.anchor},...(layered&&record.image==='source-02.png'?{supportGeometry:'Complete stool-layer geometry in the same authored 3D scene',supportPreview:'render/stool.png',supportPreviewRole:'Separately captured support reference; no raster input or image call'}:{}),processing:'Uniform whole-canvas supersampling resolves native runtime PNG; no fitting, clipping, masks or chroma key'});
    }
    await json(path.join(options.output,'submission.json'),{caseId:entry.id,outputDirectory:options.output,userPrompt:entry.prompt.replace('{{OUTPUT_DIR}}',options.output),sources:sourceRecords,guide:'guide.json',guideSHA256:sha(await readFile(path.join(options.output,'guide.json'))),result:'result.json'});
    const sourceFiles=[];for(const n of names)sourceFiles.push({path:'scene/'+n,sha256:sha(await readFile(path.join(options.output,'scene',n)))});
    await json(path.join(options.output,'capture.json'),{version:1,workflow:'fresh-direct-modeled-3d-control',caseId:entry.id,renderEngine:'Three.js WebGLRenderer via Playwright Chromium',threeVersion:JSON.parse(await readFile(path.join(threeRoot,'package.json'))).version,playwrightVersion:dependency('playwright/package.json').version,chromiumVersion:browser.version(),supersample:options.supersample,frame:entry.expected.size,anchor:entry.expected.anchor,sourceFiles,imageGenerationCalls:0,noOldRasterReuse:true,renderRecipe:`node scene/3d_controls_static.mjs ${entry.id} NEW_OUTPUT_DIR --suite scene/suite.json --runtime-root RUNTIME_ROOT --scale ${options.supersample}`,limitations:['Raster edge coverage can vary with antialiasing and browser/driver.','Authored registration is deterministic geometry; independent visual review is still required.','Renderer references are model/camera inputs, not image-generation calls.'],browserErrors:errors});
    await json(path.join(options.output,'scene/suite.json'),{version:suite.version,cases:[entry]});
    await writeFile(path.join(options.output,'scene/README.md'),`# Fresh direct 3D control: ${entry.id}\n\nThe editable ObjectLoader scene is model.json. The complete deterministic modeled builder is 3d_controls_static_scene.js and the seated weighted rig is 3d_controls_static_rig.js. No prior raster was reused and no AI call was made.\n\nFrom this bundle directory after installing runtime dependencies:\n\n\`\`\`sh\nnode scene/3d_controls_static.mjs ${entry.id} /absolute/new-output --suite scene/suite.json --runtime-root /absolute/npm-runtime --scale ${options.supersample}\n\`\`\`\n\nThe fixed affine mapping is screenX=anchorX+128*x, screenY=anchorY+128*z-128*y; the flat floor uses a true top-down camera. Art bounds never determine registration.\n`);
    return{caseId:entry.id,output:options.output,sprites:sprites.length,captures:data.captures.length,bounds:byId.whole.bounds,browserErrors:errors};
  }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){try{console.log(JSON.stringify(await run(parseArgs(process.argv.slice(2)))));}catch(e){console.error(e.stack||String(e));process.exitCode=1;}}
