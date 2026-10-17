#!/usr/bin/env node
/** Portable headless Three.js reference rendering; no model calls or asset fitting. */
import {realpathSync} from 'node:fs';
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {readFile,writeFile,mkdir,access,copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

export function parseArgs(argv) {
  const [mode,output,...args]=argv;
  if(!['dance','directions'].includes(mode)||!output) throw new Error('Usage: node render_3d.mjs dance|directions OUTPUT_DIR [--scale 2] [--runtime-root DIR]');
  const options={mode,output:path.resolve(output),supersample:2,runtimeRoot:null};
  for(let i=0;i<args.length;i+=2) {
    if(!args[i+1]) throw new Error(`Missing value for ${args[i]}`);
    if(['--scale','--supersample'].includes(args[i]))options.supersample=Number(args[i+1]);
    else if(args[i]==='--runtime-root')options.runtimeRoot=path.resolve(args[i+1]);
    else throw new Error(`Unknown option ${args[i]}`);
  }
  if(![1,2,3,4].includes(options.supersample))throw new Error('Supersample must be integer 1..4');
  return options;
}
export function projection([x,y,z]) { return [96+128*x,248+128*z-128*y]; }
function sha256(bytes) {return createHash('sha256').update(bytes).digest('hex');}
async function writeJSON(file,value){await writeFile(file,JSON.stringify(value,null,2)+'\n');}
async function writePNG(file,url){if(!url.startsWith('data:image/png;base64,'))throw new Error('Expected PNG data URL');await writeFile(file,Buffer.from(url.split(',')[1],'base64'));}
export async function run(options) {
  const scriptDir=path.dirname(fileURLToPath(import.meta.url));
  const dependencyRequire=createRequire(options.runtimeRoot?path.join(options.runtimeRoot,'package.json'):import.meta.url);
  const {chromium}=dependencyRequire('playwright');
  const threePackage=dependencyRequire.resolve('three');
  const threeRoot=path.resolve(path.dirname(threePackage),'..');
  try{await access(options.output);throw new Error('Output directory already exists; choose a new run directory');}catch(error){if(error.code!=='ENOENT')throw error;}
  const sceneFile=path.join(scriptDir,'render_3d_scene.js');
  const errors=[];
  const server=createServer(async(req,res)=>{
    try{
      const url=new URL(req.url,'http://localhost');let bytes,type='text/javascript';
      if(url.pathname==='/'){
        type='text/html';bytes=Buffer.from('<!doctype html><title>3D reference renderer</title><script type="importmap">'+JSON.stringify({imports:{three:'/three/build/three.module.js','three/addons/':'/three/examples/jsm/'}})+'</script><script type="module" src="/scene.js"></script>');
      }else if(url.pathname==='/scene.js')bytes=await readFile(sceneFile);
      else if(url.pathname.startsWith('/three/')){
        const requested=path.resolve(threeRoot,'.'+url.pathname.slice('/three'.length));
        if(!requested.startsWith(threeRoot+path.sep))throw new Error('Path escapes dependency root');
        bytes=await readFile(requested);
      }else if(url.pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}
      else {res.writeHead(404);res.end();return;}
      res.writeHead(200,{'content-type':type});res.end(bytes);
    }catch(error){res.writeHead(500);res.end(String(error));}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try{
    browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader']});
    const page=await browser.newPage({viewport:{width:800,height:800}});
    page.on('pageerror',error=>errors.push(error.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    await page.goto(`http://127.0.0.1:${server.address().port}`,{waitUntil:'networkidle'});
    await page.waitForFunction(()=>typeof window.renderBundle==='function');
    const data=await page.evaluate(opts=>window.renderBundle(opts),{mode:options.mode,supersample:options.supersample});
    if(errors.length)throw new Error(errors.join('\n'));
    await mkdir(options.output,{recursive:true});
    for(const folder of ['frames','frames-highres','masks','depth','floor-frames','scene'])await mkdir(path.join(options.output,folder));
    for(const f of data.frames){
      for(const [key,folder]of [['color','frames'],['colorHi','frames-highres'],['mask','masks'],['depth','depth'],['floor','floor-frames']])await writePNG(path.join(options.output,folder,f.id+'.png'),f[key]);
    }
    for(const [key,sheet]of Object.entries(data.sheets)){
      const stem=key==='color'?'reference':key==='floor'?'reference-on-floor':key==='mask'?'mask-sheet':'depth-sheet';
      await writePNG(path.join(options.output,stem+'.png'),sheet.lo);await writePNG(path.join(options.output,`${stem}-${options.supersample}x.png`),sheet.hi);
    }
    await writePNG(path.join(options.output,'sheet.png'),data.sheets.color.hi);
    await writePNG(path.join(options.output,'guide.png'),data.sheets.floor.hi);
    await writePNG(path.join(options.output,'neutral.png'),data.neutral.color);
    await writePNG(path.join(options.output,`neutral-${options.supersample}x.png`),data.neutral.colorHi);
    await writePNG(path.join(options.output,'neutral-on-floor.png'),data.neutral.floor);
    await writeJSON(path.join(options.output,'guide.json'),data.registration);
    await writeJSON(path.join(options.output,'result.json'),data.result);
    await writeJSON(path.join(options.output,'scene.json'),data.scene);
    await writeJSON(path.join(options.output,'scene','rig.json'),data.rig);
    await writeJSON(path.join(options.output,'scene','poses.json'),data.poses);
    await copyFile(sceneFile,path.join(options.output,'scene','render_3d_scene.js'));
    await copyFile(fileURLToPath(import.meta.url),path.join(options.output,'scene','render_3d.mjs'));
    await copyFile(path.join(scriptDir,'package.json'),path.join(options.output,'scene','package.json'));
    const sourceCode=await readFile(sceneFile),runnerCode=await readFile(fileURLToPath(import.meta.url));
    await writeJSON(path.join(options.output,'capture.json'),{version:1,workflow:'rigged-3d-reference-capture',mode:options.mode,
      frame:[192,320],anchor:[96,248],supersample:options.supersample,fps:options.mode==='dance'?12:null,
      renderEngine:'Three.js WebGLRenderer via Playwright Chromium',threeRevision:JSON.parse(await readFile(path.join(threeRoot,'package.json'))).version,
      editableScene:'scene.json',rig:'scene/rig.json',poses:'scene/poses.json',
      sourceCode:'scene/render_3d_scene.js',sourceCodeSHA256:sha256(sourceCode),runnerSHA256:sha256(runnerCode),
      sourceSheets:{floorFree:'sheet.png',floorRegistration:'guide.png'},
      perFrameFit:false,rootFit:false,crop:false,backgroundRemoval:false,imageGenerationCalls:0,
      limitations:['The 3D capture is registered by construction; an image-model reskin can alter its silhouette, root, pose or panel layout.',
        'The procedural adventurer is a reference design, not an imported production character.',
        'Depth grayscale uses near=6, far=10; the mask is exact color-pass alpha, not a guessed color key.']});
    return {output:options.output,mode:options.mode,frames:data.frames.length,frame:[192,320],anchor:[96,248],neutralProjectedCrownHeight:data.registration.neutralProjectedCrownHeight,
      source:path.join(options.output,'sheet.png'),floorSource:path.join(options.output,'guide.png'),browserErrors:errors};
  }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
}
if(process.argv[1]&&realpathSync(process.argv[1])===realpathSync(fileURLToPath(import.meta.url))) {
  try{console.log(JSON.stringify(await run(parseArgs(process.argv.slice(2))),null,2));}
  catch(error){console.error(error.stack||String(error));process.exitCode=1;}
}
