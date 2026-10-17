/** Fresh modeled static controls. All shapes are actual Three.js geometry. */
import * as THREE from 'three';
import {createCharacter, setPose, MODEL} from './3d_controls_static_rig.js';

export const CASES = ['seamless-square-floor','lava-tile','full-cell-raised-object','partial-cell-tall-object','floating-object','large-object-2x2','large-object-3x2','disjoint-support-arch','seated-character-separated'];
const CELL = 128;
const TAU = Math.PI * 2;
const palette = {stone:'#8c9284',stoneDark:'#626d64',stoneLight:'#b1b3a1',iron:'#263943',wood:'#91603b',woodDark:'#5c3c29',gold:'#d7a341'};
const material = (color, extra={}) => new THREE.MeshStandardMaterial({color,roughness:.82,metalness:0,...extra});
const mats = Object.fromEntries(Object.entries(palette).map(([k,c])=>[k,material(c)]));
function group(name,parent) { const g=new THREE.Group(); g.name=name;parent?.add(g);return g; }
function mesh(name,geo,mat,parent,position=[0,0,0]) {const m=new THREE.Mesh(geo,mat);m.name=name;m.position.set(...position);parent.add(m);return m;}
function box(name,size,pos,mat,parent) {return mesh(name,new THREE.BoxGeometry(...size),mat,parent,pos);}
function cylinder(name,radius,height,pos,mat,parent,segments=24) {return mesh(name,new THREE.CylinderGeometry(radius,radius,height,segments),mat,parent,pos);}
function beam(name,a,b,r,mat,parent) {const av=new THREE.Vector3(...a),bv=new THREE.Vector3(...b);const m=cylinder(name,r,av.distanceTo(bv),av.clone().add(bv).multiplyScalar(.5).toArray(),mat,parent,12);m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),bv.sub(av).normalize());return m;}
function plane(name,w,h,y,mat,parent) {const m=mesh(name,new THREE.PlaneGeometry(w,h),mat,parent,[0,y,0]);m.rotation.x=-Math.PI/2;return m;}
function triSurface(name,verts,mat,parent) {const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));geo.computeVertexNormals();return mesh(name,geo,mat,parent);}

function surfaceShader(kind,face='top') {
  // Periodic analytic materials are evaluated on the 3D surface; no image is reused.
  return new THREE.ShaderMaterial({side:THREE.DoubleSide,vertexShader:`varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`precision highp float;varying vec2 vUv;const float T=6.28318530718;
    float hash(vec2 p){return fract(sin(dot(mod(p,4.),vec2(127.1,311.7)))*43758.5453);}
    void main(){vec2 q=vUv;vec3 c;
    ${kind==='moss' ? `vec2 p=q*4.;float row=floor(p.y);p.x+=mod(row,2.)*.5;vec2 id=floor(p);vec2 f=fract(p);float edge=min(min(f.x,1.-f.x),min(f.y,1.-f.y));float noise=.5+.5*sin(T*(q.x*11.+q.y*7.))*.5+.25*cos(T*(q.x*9.-q.y*13.));float moss=.5+.5*sin(T*q.x*3.+sin(T*q.y*2.))*cos(T*q.y*4.);vec3 rock=mix(vec3(.27,.31,.27),vec3(.53,.55,.43),hash(id));rock+=.045*noise;vec3 seam=mix(vec3(.12,.18,.09),vec3(.27,.37,.13),moss);c=mix(seam,rock,smoothstep(.025,.08,edge));c=mix(c,vec3(.30,.40,.16),smoothstep(.68,.92,moss)*.45);` : kind==='lava' ? `float n=sin(T*q.x*2.+.62*sin(T*q.y*3.))+cos(T*q.y*2.+.55*sin(T*q.x*3.));float seam=1.-smoothstep(.14,.40,abs(n));float fine=.5+.5*sin(T*(q.x*17.+q.y*11.));vec3 crust=mix(vec3(.14,.055,.035),vec3(.31,.105,.045),fine*.4);vec3 melt=mix(vec3(1.,.24,.015),vec3(1.,.74,.08),seam);c=mix(crust,melt,seam);${face==='side'?'c*=.78;':''}` : `float grain=.5+.5*sin(T*(q.x*19.+q.y*7.))*cos(T*q.y*23.);c=vec3(.49,.52,.47)+.045*grain;${face==='side'?'c*=.72;':''}`}
    gl_FragColor=vec4(c,1.);#include <colorspace_fragment>}`.replace('1.);#include','1.);\n#include')});
}

function makeCamera(frame,anchor,flat=false) {
  const verticalScale=flat?CELL:CELL*Math.SQRT2;
  const camera=new THREE.OrthographicCamera(-anchor[0]/CELL,(frame[0]-anchor[0])/CELL,anchor[1]/verticalScale,-(frame[1]-anchor[1])/verticalScale,.1,30);
  camera.name=flat?'true-top-down-floor-camera':'fixed-affine-square-ground-camera';
  if(flat){camera.position.set(0,8,0);camera.up.set(0,0,-1);}else camera.position.set(0,8,8);
  camera.lookAt(0,0,0);camera.updateProjectionMatrix();camera.updateMatrixWorld(true);return camera;
}
function project(camera,point,frame) {const p=new THREE.Vector3(...point).project(camera);return[(p.x+1)*frame[0]/2,(1-p.y)*frame[1]/2];}

function makeLantern(parent) {
  box('48px-square-ground-base',[.375,.06,.375],[0,.03,0],mats.stoneDark,parent);
  box('base-plaque',[.29,.035,.29],[0,.0775,0],mats.stone,parent);
  cylinder('iron-post',.033,.82,[0,.505,0],mats.iron,parent);
  cylinder('collar-lower',.055,.04,[0,.19,0],mats.gold,parent);
  cylinder('collar-upper',.052,.035,[0,.87,0],mats.gold,parent);
  box('lantern-bottom',[.25,.035,.25],[0,.925,0],mats.iron,parent);
  const glass=material('#ffd57b',{emissive:'#d57122',emissiveIntensity:.7,roughness:.35});
  box('warm-glass',[.19,.205,.19],[0,1.0425,0],glass,parent);
  for(const x of [-.104,.104])for(const z of [-.104,.104])box('cage-bar',[.018,.225,.018],[x,1.0375,z],mats.iron,parent);
  box('lantern-top-cap',[.265,.025,.265],[0,1.1575,0],mats.iron,parent);
  const roof=mesh('pyramidal-roof',new THREE.ConeGeometry(.205,.08,4),mats.iron,parent,[0,1.21,0]);roof.rotation.y=Math.PI/4;
}
function makeOrb(parent) {
  // Under this affine camera a sphere projects height 2*r*sqrt(2)*128.
  const r=.25/Math.SQRT2,cy=.625;
  mesh('treasure-orb',new THREE.SphereGeometry(r,64,32),material('#2dbea1',{metalness:.34,roughness:.22,emissive:'#12464b',emissiveIntensity:.3}),parent,[0,cy,0]);
  for(const a of [0,Math.PI/3,Math.PI*2/3]){const m=mesh('gold-meridian',new THREE.TorusGeometry(r-.004,.004,8,72),mats.gold,parent,[0,cy,0]);m.rotation.y=a;}
  const ring=mesh('gold-equator',new THREE.TorusGeometry(r-.004,.004,8,72),mats.gold,parent,[0,cy,0]);ring.rotation.x=Math.PI/2;
  mesh('front-jewel',new THREE.OctahedronGeometry(.033,0),material('#ffe39a',{metalness:.55,roughness:.24}),parent,[0,cy,.165]);
}
function makeFountain(parent) {
  box('2x2-complete-foundation',[2,.09,2],[0,.045,0],mats.stoneDark,parent);
  box('inset-basin-bottom',[1.9,.10,1.9],[0,.14,0],mats.stone,parent);
  for(const z of [-.9,.9])box('basin-rim-x',[1.9,.22,.10],[0,.25,z],mats.stoneLight,parent);
  for(const x of [-.9,.9])box('basin-rim-z',[.10,.22,1.70],[x,.25,0],mats.stoneLight,parent);
  plane('basin-water',1.70,1.70,.245,material('#348d9e',{metalness:.15,roughness:.22}),parent);
  cylinder('central-pedestal',.13,.45,[0,.47,0],mats.stone,parent);
  const profile=[[.08,0],[.12,.02],[.23,.06],[.37,.14],[.43,.21],[.44,.25],[.39,.25],[.36,.18],[.22,.11],[.08,.09]].map(p=>new THREE.Vector2(...p));
  mesh('upper-carved-bowl',new THREE.LatheGeometry(profile,64),mats.stoneLight,parent,[0,.56,0]);
  cylinder('upper-water',.37,.012,[0,.785,0],material('#4ba8b8',{metalness:.18,roughness:.19}),parent,64);
  cylinder('spout',.045,.20,[0,.90,0],mats.stone,parent);
  const water=material('#75d4dc',{roughness:.21,metalness:.15});
  for(let k=0;k<6;k++){const a=k*TAU/6;const points=[];for(let j=0;j<=20;j++){const t=j/20;const rr=.06+.53*t;points.push(new THREE.Vector3(Math.cos(a)*rr,.96-.64*t*t,Math.sin(a)*rr));}mesh('water-arc',new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points),24,.009,6,false),water,parent);}
}
function makeGreenhouse(parent) {
  box('3x2-ground-foundation',[3,.08,2],[0,.04,0],mats.stoneDark,parent);
  box('interior-soil',[2.87,.025,1.87],[0,.0925,0],material('#645b3b'),parent);
  const glass=material('#8dc7bb',{transparent:true,opacity:.30,roughness:.20,metalness:.10,side:THREE.DoubleSide,depthWrite:false});
  const frameMat=material('#d8dac1',{metalness:.25,roughness:.45});
  const side=box('complete-glass-wall',[2.96,.54,.006],[0,.35,-.995],glass,parent);box('front-glass-wall',[2.96,.54,.006],[0,.35,.995],glass,parent);
  for(const x of [-1.49,1.49]) {
    triSurface('glass-gable', [x,.08,-1,x,.62,-1,x,1,0,x,.08,-1,x,1,0,x,.08,1,x,.08,1,x,1,0,x,.62,1],glass,parent);
  }
  for(const z of [-1,1]){
    triSurface('pitched-glass-roof',[-1.49,.62,z,1.49,.62,z,1.49,1,0,-1.49,.62,z,1.49,1,0,-1.49,1,0],glass,parent);
    for(const y of [.10,.36,.62])beam('horizontal-wall-frame',[-1.5,y,z],[1.5,y,z],.014,frameMat,parent);
  }
  beam('ridge',[-1.5,1,0],[1.5,1,0],.018,frameMat,parent);
  for(const x of [-1.49,-.75,0,.75,1.49])for(const z of [-1,1]){
    beam('wall-upright',[x,.08,z],[x,.62,z],.015,frameMat,parent);
    beam('roof-rafter',[x,.62,z],[x,1,0],.016,frameMat,parent);
  }
  // Planters and individually modeled leaves make the requested greenhouse readable.
  for(const z of [-.56,.56]){
    box('wooden-growing-bed',[2.55,.13,.46],[0,.17,z],mats.woodDark,parent);
    for(let j=-3;j<=3;j++){
      const x=j*.34;beam('plant-stem',[x,.24,z],[x,.45,z],.009,material('#426b35'),parent);
      for(const sign of [-1,1]){const leaf=mesh('plant-leaf',new THREE.SphereGeometry(1,12,8),material(sign<0?'#688f42':'#86a654'),parent,[x+sign*.045,.38,z]);leaf.scale.set(.075,.025,.038);leaf.rotation.z=sign*.5;}
    }
  }
  for(const x of [-.32,.32])beam('front-door-jamb',[x,.08,1.012],[x,.62,1.012],.016,frameMat,parent);
  beam('door-head',[-.32,.62,1.012],[.32,.62,1.012],.017,frameMat,parent);
  mesh('door-handle',new THREE.SphereGeometry(.018,12,8),mats.gold,parent,[.25,.34,1.03]);
}

function archShape() {
  const s=new THREE.Shape();s.moveTo(-1.5,.75);s.lineTo(-1.5,1.25);s.lineTo(1.5,1.25);s.lineTo(1.5,.75);s.lineTo(.5,.75);
  for(let j=0;j<=32;j++){const a=j*Math.PI/32;s.lineTo(.5*Math.cos(a),.75+.28*Math.sin(a));}
  s.lineTo(-1.5,.75);return s;
}
function makeArchHalf(parent,z0,z1,name) {
  const g=group(name,parent),height=.75;
  for(const x of [-1,1]){
    box('pillar-ground-cell',[1,height,z1-z0],[x,height/2,(z0+z1)/2],mats.stone,g);
    for(let y=.15;y<height;y+=.15)box('masonry-horizontal-joint',[1.001,.008,z1-z0+.001],[x,y,(z0+z1)/2],mats.stoneDark,g);
    box('pillar-base',[1,.065,z1-z0],[x,.0325,(z0+z1)/2],mats.stoneDark,g);
  }
  const geo=new THREE.ExtrudeGeometry(archShape(),{depth:z1-z0,bevelEnabled:false,curveSegments:32});
  mesh('independent-overhead-span',geo,mats.stoneLight,g,[0,0,z0]);
  // Radial voussoir seams are physical thin stone bars on outer faces.
  for(let j=1;j<8;j++){
    const a=j*Math.PI/8;const inner=[.5*Math.cos(a),.75+.28*Math.sin(a)],outer=[.80*Math.cos(a),1.25];
    for(const z of [z0,z1])beam('voussoir-joint',[inner[0],inner[1],z],[outer[0],outer[1],z],.004,mats.stoneDark,g);
  }
  return g;
}
function makeStool(parent) {
  box('complete-wood-seat',[.55,.06,.44],[0,.345,0],mats.wood,parent);
  for(const x of [-.20,.20])for(const z of [-.15,.15])box('stool-leg',[.055,.315,.055],[x,.1575,z],mats.woodDark,parent);
  for(const z of [-.15,.15])box('stool-crossbrace',[.44,.033,.035],[0,.14,z],mats.wood,parent);
  for(const x of [-.20,.20])box('stool-depth-brace',[.035,.033,.34],[x,.17,0],mats.wood,parent);
  for(const x of [-.16,0,.16])box('seat-plank-line',[.006,.001,.42],[x,.3755,0],mats.woodDark,parent);
}
function makeSeatedCharacter(parent) {
  const c=createCharacter();setPose(c,'neutral',0);
  // Preserve the existing character anatomy, weights and dimensions. Pose the
  // hips and leg bones into a seated configuration, with the pelvis on y=.375.
  c.named.hips.position.y=.457;
  for(const side of ['left','right']){
    c.named[side+'-thigh'].rotation.x=-.85;
    c.named[side+'-knee'].rotation.x=.85;
    c.named[side+'-shoulder'].rotation.x=-.67;
    c.named[side+'-shoulder'].rotation.z=(side==='left'?-.10:.10);
    c.named[side+'-elbow'].rotation.x=-.20;
  }
  c.group.position.z=.16;
  c.group.updateMatrixWorld(true);c.skeleton.update();parent.add(c.group);return c;
}

function canvas(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
function raster(renderer,frame,scale){const c=canvas(...frame);const ctx=c.getContext('2d');ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(renderer.domElement,0,0,...frame);return c;}
function bounds(c){const a=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let l=c.width,t=c.height,r=-1,b=-1;for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++)if(a[(y*c.width+x)*4+3]>0){l=Math.min(l,x);t=Math.min(t,y);r=Math.max(r,x);b=Math.max(b,y);}return r<0?null:[l,t,r+1,b+1];}

export async function renderStatic({caseId,expected,supersample=2}) {
  if(!CASES.includes(caseId))throw Error('Unsupported static case '+caseId);
  const frame=expected.size,anchor=expected.anchor,flat=caseId==='seamless-square-floor';
  const scene=new THREE.Scene(),camera=makeCamera(frame,anchor,flat);scene.add(camera);
  scene.add(new THREE.HemisphereLight('#edf5ff','#625846',2.4));
  const key=new THREE.DirectionalLight('#fff0d4',3.1);key.position.set(-3,6,4);scene.add(key);
  const fill=new THREE.DirectionalLight('#bedaff',.75);fill.position.set(3,2,-3);scene.add(fill);
  const subject=group('subject',scene);let rear=null,front=null,stool=null,character=null,rig=null;
  if(flat)plane('periodic-mossy-stone-floor',1,1,0,surfaceShader('moss'),subject);
  if(caseId==='lava-tile'||caseId==='full-cell-raised-object'){
    const lava=caseId==='lava-tile',h=lava?.25:.5;
    const top=surfaceShader(lava?'lava':'stone'),side=surfaceShader(lava?'lava':'stone','side');
    box(lava?'full-square-raised-lava':'full-square-stone-plinth',[1,h,1],[0,h/2,0],[side,side,top,side,side,side],subject);
    if(!lava){for(const y of [.065,.43])box('carved-front-line',[1,.012,.001],[0,y,.5005],mats.stoneDark,subject);for(const z of [-.32,0,.32])box('top-stone-joint',[1,.001,.006],[0,.5005,z],mats.stoneDark,subject);}
  }
  if(caseId==='partial-cell-tall-object')makeLantern(subject);
  if(caseId==='floating-object')makeOrb(subject);
  if(caseId==='large-object-2x2')makeFountain(subject);
  if(caseId==='large-object-3x2')makeGreenhouse(subject);
  if(caseId==='disjoint-support-arch'){rear=makeArchHalf(subject,-.5,0,'rear-depth-half');front=makeArchHalf(subject,0,.5,'front-depth-half');}
  if(caseId==='seated-character-separated'){stool=group('stool-layer',subject);makeStool(stool);character=group('character-layer',subject);rig=makeSeatedCharacter(character);}
  const floorMat=new THREE.MeshBasicMaterial({color:'#d68bd8',side:THREE.DoubleSide});
  const floor=plane('separate-registration-floor',expected.footprint[0]/128,expected.footprint[1]/128,-.0001,floorMat,scene);floor.visible=false;
  const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(1);renderer.setSize(frame[0]*supersample,frame[1]*supersample,false);renderer.setClearColor(0,0);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
  const captures=[];
  function capture(id,{withFloor=false,depth=false}={}) {
    floor.visible=withFloor;
    if(depth)scene.overrideMaterial=new THREE.MeshDepthMaterial({depthPacking:THREE.BasicDepthPacking});
    const depthCamera=camera.clone();depthCamera.near=8;depthCamera.far=15;depthCamera.updateProjectionMatrix();
    renderer.render(scene,depth?depthCamera:camera);scene.overrideMaterial=null;floor.visible=false;
    const hi=canvas(renderer.domElement.width,renderer.domElement.height);hi.getContext('2d').drawImage(renderer.domElement,0,0);
    const lo=raster(renderer,frame,supersample);const rect=bounds(lo);
    if(!flat&&rect&&(rect[0]===0||rect[1]===0||rect[2]===frame[0]||rect[3]===frame[1]))throw Error(id+' touches frame; no clipping recovery allowed');
    captures.push({id,color:lo.toDataURL(),high:hi.toDataURL(),bounds:rect});return lo;
  }
  const whole=capture('whole');capture('on-floor',{withFloor:true});capture('depth',{depth:true});
  subject.visible=false;floor.visible=true;capture('floor-registration',{withFloor:true});subject.visible=true;
  if(stool){character.visible=false;capture('stool');stool.visible=false;character.visible=true;capture('character');stool.visible=true;
    // Actual render of the same scene with both complete groups; no differencing.
    capture('recomposed-3d');
  }
  if(rear){front.visible=false;capture('arch-rear');rear.visible=false;front.visible=true;capture('arch-front');rear.visible=true;
    const actor=createCharacter();setPose(actor,'neutral',0);actor.group.scale.setScalar(.52);scene.add(actor.group);
    for(const [id,z]of [['passage-behind',-.8],['passage-center',0],['passage-foreground',.8]]){
      actor.group.position.set(0,0,z);actor.group.updateMatrixWorld(true);actor.skeleton.update();capture(id,{withFloor:true});
      subject.visible=false;capture(id.replace('passage-','actor-'));subject.visible=true;
    }
    scene.remove(actor.group);
  }
  // Compact scene serialization preserves mesh geometry, materials, lights and
  // camera. JSON is not repeatedly pretty-printed, and no masks force silhouettes.
  const editableScene=scene.toJSON();
  const registration={version:2,cellSize:CELL,anchor,frame,projection:'top-down-oblique-square-grid',heightAxis:[0,-1],elevationScale:1,captureScale:supersample,sourceSize:frame.map(v=>v*supersample),sourcePixelsPerRuntimePixel:supersample,kind:'modeled-3d-static-control',assetKind:stool?'layered':flat?'floor':'object',caseId,
    projectionFormula:{screenX:`${anchor[0]} + 128*x`,screenY:flat?`${anchor[1]} + 128*z`:`${anchor[1]} + 128*z - 128*y`},
    floorCorners:[[-expected.footprint[0]/256,0,-expected.footprint[1]/256],[expected.footprint[0]/256,0,-expected.footprint[1]/256],[expected.footprint[0]/256,0,expected.footprint[1]/256],[-expected.footprint[0]/256,0,expected.footprint[1]/256]].map(p=>({world:p,screen:project(camera,p,frame)})),
    camera:{type:camera.type,matrixWorld:camera.matrixWorld.toArray(),matrixWorldInverse:camera.matrixWorldInverse.toArray(),projectionMatrix:camera.projectionMatrix.toArray(),near:camera.near,far:camera.far},
    noFitting:true,nominalHeightPx:expected.elevationPx,footprint:expected.footprint,occupiedCells:expected.occupiedCells,elevationPx:expected.elevationPx,
    ...(expected.baseSize?{baseSize:expected.baseSize}:{}),...(expected.supportCells?{supportCells:expected.supportCells}:{}),...(expected.overheadCells?{overheadCells:expected.overheadCells}:{}),
    ...(stool?{supportElevationPx:48,supportElevationBakedIntoArt:true,attachmentWorld:[0,.375,.16],attachmentPoint:[96,220.48],characterModel:MODEL,posedBones:rig.bones.map(b=>({name:b.name,position:b.position.toArray(),quaternion:b.quaternion.toArray()})),anatomyStandingHeightPx:160}:{}),
    controls:{cameraFit:false,rootFit:false,silhouetteMask:false,clipping:false,backgroundRemoval:false,imageGenerationCalls:0},sourceAuthority:'Fresh authored Three.js modeled geometry; no AI artwork or old source raster reuse'};
  renderer.dispose();return{captures,registration,scene:editableScene};
}
if(typeof window!=='undefined')window.renderStatic=renderStatic;
