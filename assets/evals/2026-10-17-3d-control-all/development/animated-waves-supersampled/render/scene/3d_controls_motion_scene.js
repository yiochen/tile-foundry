/** Direct Three.js controls. Terrain appearance and motion are authored GLSL, never model output. */
import * as THREE from 'three';
import {makeCamera, renderBundle as renderCharacterBundle, FRAME, ANCHOR, CELL, GUTTER} from './character_scene.js';

const TAU = Math.PI * 2;
export const VERTEX_SHADER = `
varying vec3 localPosition;
void main() {
  localPosition = position;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;
export const FRAGMENT_SHADER = `
precision highp float;
uniform float phase;
uniform float water;
uniform float flowing;
uniform float front;
varying vec3 localPosition;
const float TAU = 6.283185307179586;
float field(vec2 p) {
  return .48*sin(TAU*(2.*p.x+p.y)) + .26*cos(TAU*(p.x-3.*p.y))
       + .17*sin(TAU*(5.*p.x+2.*p.y)) + .09*cos(TAU*(7.*p.y-p.x));
}
vec3 lava(vec2 p) {
  float f=abs(field(p));
  float crack=1.-smoothstep(.035,.16,f);
  float rim=1.-smoothstep(.10,.30,f);
  vec3 rock=mix(vec3(.10,.045,.065),vec3(.29,.075,.055),.5+.5*field(p+vec2(.3,.2)));
  vec3 color=mix(rock,vec3(.95,.22,.025),rim*.85);
  return mix(color,vec3(1.,.83,.19),crack);
}
vec3 ocean(vec2 p) {
  float swell=sin(TAU*(3.*p.y+p.x+.10*sin(TAU*p.x)))
             + .24*sin(TAU*(5.*p.x-2.*p.y));
  float foam=smoothstep(.79,1.13,swell);
  float shimmer=.5+.5*field(p*vec2(1.,2.));
  vec3 color=mix(vec3(.015,.20,.38),vec3(.025,.63,.74),.22+.58*shimmer);
  return mix(color,vec3(.70,.96,.94),foam*.90);
}
void main() {
  vec2 p=vec2(localPosition.x+.5,localPosition.z+.5);
  if(front>.5) {
    // This is the actual 32px front wall, with no bevel/rim or per-cell lighting gradient.
    p=vec2(localPosition.x+.5,localPosition.y*4.);
    float stripe=.5+.5*sin(TAU*(3.*p.x+.15*sin(TAU*p.y)));
    vec3 color=water>.5?mix(vec3(.015,.12,.25),vec3(.02,.32,.44),stripe)
                       :mix(vec3(.13,.035,.045),vec3(.46,.095,.03),pow(stripe,9.));
    gl_FragColor=vec4(color,1.);return;
  }
  // A 16px, C1 edge transition makes the exact boundary independent of phase.
  // It is an explicit authored design choice: strongest motion in the interior.
  float edge=min(min(p.x,1.-p.x),min(p.y,1.-p.y));
  float weight=smoothstep(0.,.125,edge);
  vec2 displacement=water>.5?vec2(0.,-phase):vec2(-phase,flowing>.5?-.0:-phase);
  vec3 stationary=water>.5?ocean(p):lava(p);
  vec3 moving=water>.5?ocean(p+displacement):lava(p+displacement);
  gl_FragColor=vec4(mix(stationary,moving,weight),1.);
}`;

function canvas(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
function copy(source,w=source.width,h=source.height){const c=canvas(w,h);const ctx=c.getContext('2d');ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(source,0,0,w,h);return c;}
function project(camera,p){const v=new THREE.Vector3(...p).project(camera);return[(v.x+1)*FRAME[0]/2,(1-v.y)*FRAME[1]/2];}
function alphaMask(source){const c=copy(source),ctx=c.getContext('2d'),a=ctx.getImageData(0,0,c.width,c.height);for(let i=0;i<a.data.length;i+=4){const v=a.data[i+3];a.data[i]=a.data[i+1]=a.data[i+2]=v;a.data[i+3]=255;}ctx.putImageData(a,0,0);return c;}
function bounds(c){const p=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let x0=c.width,y0=c.height,x1=-1,y1=-1;for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++)if(p[(y*c.width+x)*4+3]){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}if(x0===0||y0===0||x1===c.width-1||y1===c.height-1)throw new Error('Rendered terrain reaches frame boundary');return[x0,y0,x1+1,y1+1];}

export async function renderMotionBundle({caseId,supersample=2}) {
  if(caseId==='character-directions'||caseId==='dancing-player')return renderCharacterBundle({mode:caseId==='character-directions'?'directions':'dance',supersample});
  if(!['animated-waves','animated-lava','authored-flowing-lava'].includes(caseId))throw new Error('Unknown direct motion case');
  const camera=makeCamera(),scene=new THREE.Scene();camera.name='fixed-square-grid-camera';scene.add(camera);
  const water=caseId==='animated-waves',flowing=caseId==='authored-flowing-lava';
  const top=new THREE.ShaderMaterial({name:'authored-periodic-surface',uniforms:{phase:{value:0},water:{value:water?1:0},flowing:{value:flowing?1:0},front:{value:0}},vertexShader:VERTEX_SHADER,fragmentShader:FRAGMENT_SHADER});
  const wall=new THREE.ShaderMaterial({name:'fixed-front-wall',uniforms:{phase:{value:0},water:{value:water?1:0},flowing:{value:flowing?1:0},front:{value:1}},vertexShader:VERTEX_SHADER,fragmentShader:FRAGMENT_SHADER});
  // Explicit top and front meshes: y=.25 is 32px high; the root stays y=0.
  const surfaceGeometry=new THREE.PlaneGeometry(1,1,1,1);surfaceGeometry.rotateX(-Math.PI/2);surfaceGeometry.translate(0,.25,0);
  const surface=new THREE.Mesh(surfaceGeometry,top);surface.name='full-128px-square-surface';scene.add(surface);
  const wallGeometry=new THREE.PlaneGeometry(1,.25,1,1);wallGeometry.translate(0,.125,.5);
  const frontMesh=new THREE.Mesh(wallGeometry,wall);frontMesh.name='32px-visible-front-wall';scene.add(frontMesh);
  const floor=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({color:0xff00ff,side:THREE.DoubleSide}));floor.rotation.x=-Math.PI/2;floor.position.y=-.0001;floor.name='registration-floor';floor.visible=false;scene.add(floor);
  const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(1);renderer.setSize(FRAME[0]*supersample,FRAME[1]*supersample,false);renderer.setClearColor(0,0);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NoToneMapping;document.body.appendChild(renderer.domElement);
  function capture(withFloor=false,depth=false){floor.visible=withFloor;scene.overrideMaterial=depth?new THREE.MeshDepthMaterial({depthPacking:THREE.BasicDepthPacking}):null;const dc=camera.clone();dc.near=6;dc.far=10;dc.updateProjectionMatrix();renderer.render(scene,depth?dc:camera);const hi=copy(renderer.domElement),lo=copy(hi,...FRAME);scene.overrideMaterial=null;floor.visible=false;return{hi,lo};}
  const columns=4,rows=3,count=12,size=[columns*FRAME[0]+(columns-1)*GUTTER,rows*FRAME[1]+(rows-1)*GUTTER];
  const sheets=Object.fromEntries(['color','floor','mask','depth'].map(k=>[k,canvas(size[0]*supersample,size[1]*supersample)]));
  const frames=[],cells=[],poses=[];const neutral=capture(),neutralFloor=capture(true);const editableScene=scene.toJSON();
  for(let i=0;i<count;i++){
    top.uniforms.phase.value=i/count;const color=capture(),floorView=capture(true),depth=capture(false,true),mask={hi:alphaMask(color.hi),lo:alphaMask(color.lo)};
    const x=(i%columns)*(FRAME[0]+GUTTER),y=Math.floor(i/columns)*(FRAME[1]+GUTTER),id=`frame-${String(i).padStart(2,'0')}`;
    for(const[k,v]of[['color',color],['floor',floorView],['mask',mask],['depth',depth]])sheets[k].getContext('2d').drawImage(v.hi,x*supersample,y*supersample);
    frames.push({id,color:color.lo.toDataURL(),colorHi:color.hi.toDataURL(),floor:floorView.lo.toDataURL(),mask:mask.lo.toDataURL(),depth:depth.lo.toDataURL()});
    cells.push({index:i,rect:[x,y,x+FRAME[0],y+FRAME[1]],anchor:[...ANCHOR],floorRect:[32,184,160,312],durationMs:1000/12,alphaBounds:bounds(color.lo)});
    poses.push({index:i,phase:i/count,rootWorld:[0,0,0],rootProjected:project(camera,[0,0,0]),surfaceWorldY:.25,visibleWallPx:32,uniforms:{phase:i/count,water:water?1:0,flowing:flowing?1:0}});
  }
  const registration={version:1,kind:'rendered-3d-sheet',assetKind:'animation',workflow:'direct-3d-authored-shader-control',mode:caseId,size:size.map(v=>v*supersample),frame:FRAME,cellSize:CELL,anchor:ANCHOR,columns,rows,gutter:GUTTER*supersample,captureScale:supersample,order:'row-major',cells:cells.map(c=>({...c,rect:c.rect.map(v=>v*supersample),floorRect:c.floorRect.map(v=>v*supersample)})),runtimeSheetSize:size,runtimeGutter:GUTTER,runtimeFloorRect:[32,184,160,312],authoredRenders:[{role:'rigged-reference',image:'sheet.png'},{role:'floor-registration',image:'guide.png'}],elevationPx:32,occupiedCells:[[0,0]],fps:12,projection:'top-down-oblique-square-grid',projectionFormula:{screenX:'96 + 128*x',screenY:'248 + 128*z - 128*y'},sourcePixelsPerRuntimePixel:supersample,sourceSize:size.map(v=>v*supersample),fitting:{perFrame:false,camera:'fixed',root:'fixed',modelScale:'fixed'},floorCorners:[[-.5,0,-.5],[.5,0,-.5],[.5,0,.5],[-.5,0,.5]].map(p=>({world:p,screen:project(camera,p)})),surfaceCorners:[[-.5,.25,-.5],[.5,.25,-.5],[.5,.25,.5],[-.5,.25,.5]].map(p=>({world:p,screen:project(camera,p)})),animationDesign:{authorship:'authored-GLSL-periodic-surface-motion',periodFrames:12,fps:12,endpointDuplicated:false,stationaryEdgeBlendPx:16,boundaryReferencePhase:0,translationPerCycle:water?[0,-1]:flowing?[-1,0]:[-1,-1],note:'Analytic periodic materials; no generated texture or model-drawn phases. Phase-invariant boundaries trade edge motion for offset-neighbor continuity.'}};
  const result={version:2,kind:'animation',projection:registration.projection,cellSize:CELL,groundAnchorAlignment:'center',fps:12,sprites:cells.map(c=>({id:`frame-${String(c.index).padStart(2,'0')}`,index:c.index,image:`frames/frame-${String(c.index).padStart(2,'0')}.png`,size:FRAME,anchor:ANCHOR,footprint:[128,128],occupiedCells:[[0,0]],elevationPx:32,durationMs:1000/12,artRect:[c.alphaBounds[0],c.alphaBounds[1],c.alphaBounds[2]-c.alphaBounds[0],c.alphaBounds[3]-c.alphaBounds[1]]}))};
  const output={frames,sheets:Object.fromEntries(Object.entries(sheets).map(([k,c])=>[k,{hi:c.toDataURL(),lo:copy(c,...size).toDataURL()}])),neutral:{color:neutral.lo.toDataURL(),colorHi:neutral.hi.toDataURL(),floor:neutralFloor.lo.toDataURL()},registration,result,scene:editableScene,rig:{model:{name:caseId,geometry:'1x1 world-unit top at y=.25 plus full front plane z=.5 from y=0..25',nominalHeightPx:32},camera:{type:camera.type,matrixWorld:camera.matrixWorld.toArray(),matrixWorldInverse:camera.matrixWorldInverse.toArray(),projectionMatrix:camera.projectionMatrix.toArray(),near:camera.near,far:camera.far}},poses};
  renderer.dispose();return output;
}
window.renderMotionBundle=renderMotionBundle;
