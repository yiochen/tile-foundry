#!/usr/bin/env node
/** Fresh direct controls: captures Three.js source, runs the frozen extractor, and prepares evidence. */
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir,copyFile,readdir,access} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';

const scriptDir=path.dirname(fileURLToPath(import.meta.url));
const [caseId,outputArg,...args]=process.argv.slice(2);
const allowed=['character-directions','dancing-player','animated-waves','animated-lava','authored-flowing-lava'];
if(!allowed.includes(caseId)||!outputArg)throw new Error('Usage: node tools/3d_controls_motion.mjs CASE OUTPUT_DIR --skill-root FROZEN_SKILL --runtime-root NODE_PROJECT [--python PYTHON]');
const options={caseId,output:path.resolve(outputArg),skillRoot:path.resolve(scriptDir,'../skills/build-overlap-tiles'),runtimeRoot:path.resolve(scriptDir,'..'),python:path.resolve(scriptDir,'../.venv/bin/python')};
for(let i=0;i<args.length;i+=2){if(!args[i+1])throw new Error('Missing option value');const key={'--skill-root':'skillRoot','--runtime-root':'runtimeRoot','--python':'python'}[args[i]];if(!key)throw new Error('Unknown option '+args[i]);options[key]=path.resolve(args[i+1]);}
const json=async(file,value)=>writeFile(file,JSON.stringify(value,null,2)+'\n');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const png=async(file,url)=>{if(!url.startsWith('data:image/png;base64,'))throw new Error('Expected PNG');await writeFile(file,Buffer.from(url.split(',')[1],'base64'));};
function command(program,argv){const r=spawnSync(program,argv,{encoding:'utf8'});if(r.status!==0)throw new Error(`${program} failed (${r.status}):\n${r.stdout}\n${r.stderr}`);return r.stdout.trim();}
await mkdir(options.output,{recursive:true});
const old=await readdir(options.output);if(old.some(n=>n!=='request.txt'))throw new Error('Case output must be empty apart from prepared request.txt; preserve earlier attempts');
const suite=JSON.parse(await readFile(path.join(options.skillRoot,'evals/cases.json'))),definition=suite.cases.find(c=>c.id===caseId);
const expectedRequest=definition.prompt.replaceAll('{{OUTPUT_DIR}}',options.output);
try{const request=(await readFile(path.join(options.output,'request.txt'),'utf8')).trimEnd();if(request!==expectedRequest)throw new Error('Prepared request differs from frozen case');}catch(error){if(error.code!=='ENOENT')throw error;await writeFile(path.join(options.output,'request.txt'),expectedRequest+'\n');}
const render=path.join(options.output,'render');await mkdir(render);
for(const folder of ['frames','frames-highres','masks','depth','floor-frames','scene'])await mkdir(path.join(render,folder));
const dependencyRequire=createRequire(path.join(options.runtimeRoot,'package.json')),{chromium}=dependencyRequire('playwright'),threeRoot=path.resolve(path.dirname(dependencyRequire.resolve('three')),'..');
const motionSceneFile=path.join(scriptDir,'3d_controls_motion_scene.js');
const characterSceneFile=path.join(options.skillRoot,'scripts/render_3d_scene.js');
const errors=[];
const server=createServer(async(req,res)=>{try{const url=new URL(req.url,'http://localhost');let bytes,type='text/javascript';if(url.pathname==='/'){type='text/html';bytes=Buffer.from('<!doctype html><title>Fresh direct 3D controls</title><script type="importmap">'+JSON.stringify({imports:{three:'/three/build/three.module.js','three/addons/':'/three/examples/jsm/'}})+'</script><script type="module" src="/motion_scene.js"></script>');}else if(url.pathname==='/motion_scene.js')bytes=await readFile(motionSceneFile);else if(url.pathname==='/character_scene.js')bytes=await readFile(characterSceneFile);else if(url.pathname.startsWith('/three/')){const requested=path.resolve(threeRoot,'.'+url.pathname.slice(6));if(!requested.startsWith(threeRoot+path.sep))throw new Error('Path escape');bytes=await readFile(requested);}else if(url.pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}else{res.writeHead(404);res.end();return;}res.writeHead(200,{'content-type':type});res.end(bytes);}catch(e){res.writeHead(500);res.end(String(e));}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));let browser,data;
try{
  browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:900,height:1000}});page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(`http://127.0.0.1:${server.address().port}`,{waitUntil:'networkidle'});await page.waitForFunction(()=>typeof window.renderMotionBundle==='function');
  data=await page.evaluate(opts=>window.renderMotionBundle(opts),{caseId,supersample:2});if(errors.length)throw new Error(errors.join('\n'));
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
for(const f of data.frames)for(const[key,folder]of[['color','frames'],['colorHi','frames-highres'],['mask','masks'],['depth','depth'],['floor','floor-frames']])await png(path.join(render,folder,f.id+'.png'),f[key]);
for(const[key,sheet]of Object.entries(data.sheets)){const stem=key==='color'?'reference':key==='floor'?'reference-on-floor':key==='mask'?'mask-sheet':'depth-sheet';await png(path.join(render,stem+'.png'),sheet.lo);await png(path.join(render,stem+'-2x.png'),sheet.hi);}
await png(path.join(render,'sheet.png'),data.sheets.color.hi);await png(path.join(render,'guide.png'),data.sheets.floor.hi);await png(path.join(render,'neutral.png'),data.neutral.color);await png(path.join(render,'neutral-2x.png'),data.neutral.colorHi);await png(path.join(render,'neutral-on-floor.png'),data.neutral.floor);
await json(path.join(render,'guide.json'),data.registration);await json(path.join(render,'result.json'),data.result);await json(path.join(render,'scene.json'),data.scene);await json(path.join(render,'scene','rig.json'),data.rig);await json(path.join(render,'scene','poses.json'),data.poses);
for(const[src,name]of[[motionSceneFile,'3d_controls_motion_scene.js'],[characterSceneFile,'character_scene.js'],[fileURLToPath(import.meta.url),'3d_controls_motion.mjs'],[path.join(scriptDir,'3d_controls_motion_pack.py'),'3d_controls_motion_pack.py'],[path.join(options.skillRoot,'scripts/extract_registered_sheet.py'),'extract_registered_sheet.py'],[path.join(options.skillRoot,'scripts/package.json'),'package.json']])await copyFile(src,path.join(render,'scene',name));
await json(path.join(render,'scene','case.json'),definition);
const capture={version:1,workflow:'fresh-direct-3d-control',caseId,createdAt:new Date().toISOString(),frame:[192,320],anchor:[96,248],cellSize:128,supersample:2,imageGenerationCalls:0,isImageModelCall:false,oldPNGsRead:false,perFrameFit:false,rootFit:false,crop:false,backgroundRemoval:false,rendererMaskApplied:false,renderEngine:'Three.js WebGLRenderer via Playwright Chromium',threeVersion:JSON.parse(await readFile(path.join(threeRoot,'package.json'))).version,browserErrors:errors,sourceFiles:{motionScene:{path:'scene/3d_controls_motion_scene.js',sha256:hash(await readFile(motionSceneFile))},characterScene:{path:'scene/character_scene.js',sha256:hash(await readFile(characterSceneFile))},runner:{path:'scene/3d_controls_motion.mjs',sha256:hash(await readFile(fileURLToPath(import.meta.url)))}},animationDesign:data.registration.animationDesign||{authorship:caseId==='dancing-player'?'authored-skeletal-joint-curves':'authored-neutral-turnaround',phaseSamples:data.frames.length,rootWorld:[0,0,0]},limitations:['Direct renderer control with authored procedural materials; no image model drew appearance or motion.','Known mathematical registration does not itself establish visual quality or natural motion.','Raster antialiasing may vary across GPU/Chromium implementations.']};
await json(path.join(render,'capture.json'),capture);await copyFile(path.join(render,'sheet.png'),path.join(options.output,'source-01.png'));
const extraction=[path.join(options.skillRoot,'scripts/extract_registered_sheet.py'),path.join(options.output,'source-01.png'),path.join(render,'guide.json'),path.join(options.output,'processed'),'--kind',definition.kind,'--min-alpha','0'];
const extractionLog=command(options.python,extraction);await writeFile(path.join(options.output,'extraction.stdout.txt'),extractionLog+'\n');await json(path.join(options.output,'commands.json'),{capture:['node',path.relative(options.runtimeRoot,fileURLToPath(import.meta.url)),caseId,path.relative(options.runtimeRoot,options.output),'--skill-root',path.relative(options.runtimeRoot,options.skillRoot),'--runtime-root','.','--python','.venv/bin/python'],extraction:[options.python,...extraction],pack:[options.python,path.join(scriptDir,'3d_controls_motion_pack.py'),options.output,options.skillRoot]});
command(options.python,[path.join(scriptDir,'3d_controls_motion_pack.py'),options.output,options.skillRoot]);
console.log(JSON.stringify({caseId,output:options.output,frames:data.frames.length,imageGenerationCalls:0,browserErrors:errors,sourceSHA256:hash(await readFile(path.join(options.output,'source-01.png')))},null,2));
