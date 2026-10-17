/** Editable procedural, skinned 3D reference; all registration is authored in world space. */
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export const FRAME = [192, 320];
export const ANCHOR = [96, 248];
export const CELL = 128;
export const DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
export const GUTTER = 32;
export const MODEL = {
  name: 'procedural-adventurer-v1', nominalStandingHeight: 160,
  palette: { skin: '#f2b77e', hair: '#362b2c', tunic: '#337dba', trim: '#a8d7ed',
    pants: '#354f69', boots: '#603d2c', belt: '#684934', buckle: '#e9be5d', eyes: '#202938' },
  rig: 'weighted segmented body; explicit bone hierarchy; static planted legs and periodic upper-body dance',
};

export function makeCamera() {
  // Screen x = 96 + 128*x; screen y = 248 + 128*z - 128*y.
  // Orthographic elevation is 45 degrees, followed by sqrt(2) vertical stretch.
  const verticalScale = CELL * Math.SQRT2;
  const camera = new THREE.OrthographicCamera(-ANCHOR[0] / CELL,
    (FRAME[0] - ANCHOR[0]) / CELL, ANCHOR[1] / verticalScale,
    -(FRAME[1] - ANCHOR[1]) / verticalScale, .1, 20);
  camera.position.set(0, 6, 6); camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
  return camera;
}

function project(camera, p) {
  const q = new THREE.Vector3(...p).project(camera);
  return [(q.x + 1) * FRAME[0] / 2, (1 - q.y) * FRAME[1] / 2];
}

export function createCharacter() {
  const group = new THREE.Group(); group.name = MODEL.name;
  const bones = []; const named = {};
  function bone(name, parent, position) {
    const b = new THREE.Bone(); b.name = name; b.position.set(...position);
    parent ? parent.add(b) : group.add(b); bones.push(b); named[name] = b; return b;
  }
  const root = bone('ground-root', null, [0, 0, 0]);
  const hips = bone('hips', root, [0, .54, 0]);
  const spine = bone('spine', hips, [0, 0, 0]);
  const chest = bone('chest', spine, [0, .26, 0]);
  const neck = bone('neck', chest, [0, .12, 0]);
  const head = bone('head', neck, [0, .14, 0]);
  for (const [side, sign] of [['left', -1], ['right', 1]]) {
    const shoulder = bone(`${side}-shoulder`, chest, [sign * .20, .055, 0]);
    const elbow = bone(`${side}-elbow`, shoulder, [sign * .07, -.205, .015]);
    bone(`${side}-wrist`, elbow, [sign * .035, -.19, .025]);
    const thigh = bone(`${side}-thigh`, hips, [sign * .105, -.01, 0]);
    const knee = bone(`${side}-knee`, thigh, [sign * .015, -.245, 0]);
    bone(`${side}-ankle`, knee, [0, -.245, 0]);
  }
  group.updateMatrixWorld(true);
  const index = Object.fromEntries(bones.map((b, i) => [b.name, i]));
  const geometries = []; const materials = []; const parts = [];
  function addPart(name, geometry, colorName, boneName, position, scale = [1, 1, 1], rotation = null, blend = null) {
    geometry.scale(...scale); if (rotation) geometry.applyQuaternion(new THREE.Quaternion().setFromEuler(new THREE.Euler(...rotation)));
    geometry.translate(...position);
    const verts = geometry.getAttribute('position'); const skinI = []; const skinW = [];
    for (let i = 0; i < verts.count; i++) {
      let w = 0;
      if (blend) w = THREE.MathUtils.clamp((verts.getY(i) - blend[2]) / (blend[3] - blend[2]), 0, 1);
      skinI.push(index[boneName], blend ? index[blend[0]] : 0, 0, 0);
      skinW.push(1 - w, w, 0, 0);
    }
    geometry.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(skinI, 4));
    geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinW, 4));
    // Uniform attributes allow deterministic merge without UV layout assumptions.
    geometries.push(geometry); materials.push(new THREE.MeshStandardMaterial({color: MODEL.palette[colorName], roughness: .88, metalness: 0, flatShading: false}));
    parts.push({name, material: colorName, bone: boneName, position, scale, vertexCount: verts.count});
  }
  const sphere = () => new THREE.SphereGeometry(1, 48, 24);
  const box = () => new THREE.BoxGeometry(1, 1, 1, 2, 2, 2);
  function limb(name, from, to, radius, color, parentBone) {
    const a = new THREE.Vector3(...from), b = new THREE.Vector3(...to);
    const g = new THREE.CapsuleGeometry(radius, Math.max(.002, a.distanceTo(b) - radius * 2), 6, 12);
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
    g.applyQuaternion(q); addPart(name, g, color, parentBone, a.clone().add(b).multiplyScalar(.5).toArray());
  }
  addPart('tunic', sphere(), 'tunic', 'spine', [0, .735, 0], [.185, .235, .12], null, ['chest', null, .61, .9]);
  addPart('tunic-hem', box(), 'tunic', 'hips', [0, .555, 0], [.345, .09, .23]);
  addPart('belt', box(), 'belt', 'hips', [0, .595, .005], [.356, .045, .245]);
  addPart('belt-buckle', box(), 'buckle', 'hips', [0, .595, .138], [.052, .042, .025]);
  addPart('collar', sphere(), 'trim', 'neck', [0, .925, 0], [.093, .055, .095]);
  addPart('neck-skin', sphere(), 'skin', 'neck', [0, .957, 0], [.064, .072, .063]);
  // Highest projected point is the fixed authored crown (0, 1.25, 0).
  // The ellipsoid's projected radius is sqrt(ry^2+rz^2), independent of yaw.
  const hairGeometry = new THREE.SphereGeometry(1, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2);
  const hairPositions=hairGeometry.getAttribute('position');
  let hairProjectedRadius=-Infinity;
  for(let i=0;i<hairPositions.count;i++) hairProjectedRadius=Math.max(hairProjectedRadius,hairPositions.getY(i)*.12-hairPositions.getZ(i)*.14);
  const headCenter = 1.25 - .04 - hairProjectedRadius;
  addPart('head', sphere(), 'skin', 'head', [0, headCenter, 0], [.132, .143, .132]);
  // Hair cap's y-z maximum is exactly the nominal 1.25 world-unit crown.
  addPart('hair-cap', hairGeometry, 'hair', 'head', [0, headCenter + .04, 0], [.14, .12, .14]);
  for (const [side, s] of [['left', -1], ['right', 1]]) {
    addPart(`${side}-ear`, sphere(), 'skin', 'head', [s * .132, headCenter, .004], [.031, .049, .035]);
    addPart(`${side}-eye`, sphere(), 'eyes', 'head', [s * .054, headCenter + .006, .131], [.016, .021, .011]);
    addPart(`${side}-brow`, box(), 'hair', 'head', [s * .055, headCenter + .045, .129], [.048, .012, .014]);
    const sh = [s * .20, .855, 0], el = [s * .27, .65, .015], wr = [s * .305, .46, .04];
    limb(`${side}-sleeve`, sh, el, .067, 'tunic', `${side}-shoulder`);
    limb(`${side}-forearm`, el, wr, .045, 'skin', `${side}-elbow`);
    addPart(`${side}-hand`, sphere(), 'skin', `${side}-wrist`, [s * .305, .443, .04], [.051, .062, .046]);
    limb(`${side}-trousers-upper`, [s * .105, .53, 0], [s * .12, .285, 0], .072, 'pants', `${side}-thigh`);
    limb(`${side}-trousers-lower`, [s * .12, .285, 0], [s * .12, .04, 0], .058, 'pants', `${side}-knee`);
    // Soles are authored on y=0, with shoe length allowed below the projected root.
    addPart(`${side}-boot`, box(), 'boots', `${side}-ankle`, [s * .12, .055, .045], [.137, .11, .235]);
    addPart(`${side}-boot-cuff`, box(), 'belt', `${side}-ankle`, [s * .12, .135, .002], [.138, .065, .132]);
  }
  addPart('nose', sphere(), 'skin', 'head', [0, headCenter - .023, .135], [.024, .027, .034]);
  const mesh = new THREE.SkinnedMesh(mergeGeometries(geometries, true), materials); mesh.name = 'adventurer-skinned-body';
  group.add(mesh); const skeleton = new THREE.Skeleton(bones); mesh.bind(skeleton);
  const rest = Object.fromEntries(bones.map(b => [b.name, {position: b.position.toArray(), quaternion: b.quaternion.toArray()}]));
  return {group, mesh, bones, named, skeleton, rest, parts};
}

export function setPose(character, mode, index, count = mode === 'dance' ? 12 : 8) {
  const {group, named, bones, rest} = character;
  group.rotation.set(0, 0, 0);
  for (const b of bones) { b.position.fromArray(rest[b.name].position); b.quaternion.fromArray(rest[b.name].quaternion); }
  if (mode === 'dance') {
    const t = index / count * Math.PI * 2;
    // Root/legs remain fixed. The upper-body joints use periodic curves, so the
    // interval from frame 11 through frame 0 has the same phase spacing.
    named.spine.rotation.z = .10 * Math.sin(t);
    named.chest.rotation.y = .16 * Math.sin(t);
    named.head.rotation.z = -.045 * Math.sin(t);
    named['left-shoulder'].rotation.z = -1.1 - .85 * Math.sin(t);
    named['right-shoulder'].rotation.z = 1.1 + .85 * Math.sin(t + Math.PI);
    named['left-shoulder'].rotation.x = .26 * Math.cos(t);
    named['right-shoulder'].rotation.x = -.26 * Math.cos(t);
    // Fixed additional elbow flexion leaves brushwork room inside every panel.
    // This authored rig curve never measures a frame or fits a model output.
    named['left-elbow'].rotation.z = -1.9 - .15 * Math.sin(t + .7);
    named['right-elbow'].rotation.z = 1.9 + .15 * Math.sin(t + Math.PI + .7);
  } else if (mode === 'directions') {
    // Character's front is +Z (S); compass N points toward negative Z.
    group.rotation.y = Math.PI - index * Math.PI / 4;
    named['left-shoulder'].rotation.z = -.09;
    named['right-shoulder'].rotation.z = .09;
  } else if (mode !== 'neutral') throw new Error(`Unknown pose mode ${mode}`);
  group.updateMatrixWorld(true); character.skeleton.update();
}

function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function copyCanvas(source, w, h) {
  const c = canvas(w, h), ctx = c.getContext('2d'); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(source, 0, 0, w, h); return c;
}
function alphaMask(source) {
  const c = copyCanvas(source, source.width, source.height), ctx = c.getContext('2d'), p = ctx.getImageData(0, 0, c.width, c.height);
  for (let i = 0; i < p.data.length; i += 4) { const a = p.data[i + 3]; p.data[i] = p.data[i + 1] = p.data[i + 2] = a; p.data[i + 3] = 255; }
  ctx.putImageData(p, 0, 0); return c;
}
function alphaBounds(c) {
  const a = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let x0 = c.width, y0 = c.height, x1 = -1, y1 = -1, count = 0;
  for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) if (a[(y*c.width+x)*4+3] > 1) {
    x0 = Math.min(x0,x); y0 = Math.min(y0,y); x1 = Math.max(x1,x); y1 = Math.max(y1,y); count++;
  }
  return {rect: count ? [x0, y0, x1 + 1, y1 + 1] : null, alphaPixels: count,
    touchesFrame: count > 0 && (x0 === 0 || y0 === 0 || x1 === c.width - 1 || y1 === c.height - 1)};
}
function projectedVertices(character, camera) {
  const {mesh} = character; const attribute = mesh.geometry.getAttribute('position');
  const v = new THREE.Vector3(); let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for (let i=0;i<attribute.count;i++) {
    v.fromBufferAttribute(attribute,i); mesh.applyBoneTransform(i,v); v.applyMatrix4(mesh.matrixWorld); const p=project(camera,v.toArray());
    minX=Math.min(minX,p[0]); minY=Math.min(minY,p[1]); maxX=Math.max(maxX,p[0]); maxY=Math.max(maxY,p[1]);
  }
  return [minX,minY,maxX,maxY];
}

export async function renderBundle({mode, supersample=2}) {
  if (!['dance','directions'].includes(mode)) throw new Error('Mode must be dance or directions');
  if (![1,2,3,4].includes(supersample)) throw new Error('Supersample must be integer 1..4');
  const camera = makeCamera(); const scene = new THREE.Scene(); camera.name='fixed-registration-camera'; scene.add(camera);
  scene.add(new THREE.HemisphereLight(0xe9f3ff, 0x716663, 2.6));
  const light = new THREE.DirectionalLight(0xfff2d7, 3.4); light.position.set(-3, 6, 4); scene.add(light);
  const fill = new THREE.DirectionalLight(0xb5d9ff, .8); fill.position.set(3, 2, -3); scene.add(fill);
  const character = createCharacter(); scene.add(character.group);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(1,1), new THREE.MeshBasicMaterial({color:0xff00ff,side:THREE.DoubleSide}));
  floor.name='registration-floor'; floor.rotation.x=-Math.PI/2; floor.position.y=-.0001; floor.visible=false; scene.add(floor);
  const renderer = new THREE.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});
  renderer.setPixelRatio(1); renderer.setSize(FRAME[0]*supersample,FRAME[1]*supersample,false);
  renderer.setClearColor(0x000000,0); renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1;
  document.body.appendChild(renderer.domElement);
  function capture(withFloor=false, depth=false) {
    floor.visible=withFloor; scene.overrideMaterial=depth ? new THREE.MeshDepthMaterial({depthPacking:THREE.BasicDepthPacking}) : null;
    const depthCamera = camera.clone(); depthCamera.near=6; depthCamera.far=10; depthCamera.updateProjectionMatrix();
    renderer.render(scene,depth ? depthCamera : camera);
    const hi=copyCanvas(renderer.domElement,FRAME[0]*supersample,FRAME[1]*supersample);
    const lo=copyCanvas(hi,...FRAME); scene.overrideMaterial=null; floor.visible=false;
    return {hi,lo};
  }
  const count=mode==='dance'?12:8, columns=4, rows=Math.ceil(count/columns);
  const size=[columns*FRAME[0]+(columns-1)*GUTTER,rows*FRAME[1]+(rows-1)*GUTTER];
  const sheets=Object.fromEntries(['color','floor','mask','depth'].map(k=>[k,canvas(size[0]*supersample,size[1]*supersample)]));
  const frames=[], cells=[], poses=[];
  setPose(character,'neutral',0); const neutral=capture(false); const neutralFloor=capture(true);
  const neutralBounds=projectedVertices(character,camera);
  const editableScene=scene.toJSON();
  for(let i=0;i<count;i++) {
    setPose(character,mode,i,count);
    const color=capture(false), floorView=capture(true), depth=capture(false,true), mask={hi:alphaMask(color.hi),lo:alphaMask(color.lo)};
    const x=(i%columns)*(FRAME[0]+GUTTER),y=Math.floor(i/columns)*(FRAME[1]+GUTTER);
    for(const [k,value] of [['color',color],['floor',floorView],['depth',depth],['mask',mask]]) sheets[k].getContext('2d').drawImage(value.hi,x*supersample,y*supersample);
    const bounds=alphaBounds(color.lo), projectedBounds=projectedVertices(character,camera);
    if(bounds.touchesFrame) throw new Error(`Pose ${i} touches frame boundary; enlarge explicit frame before rendering`);
    const id=`frame-${String(i).padStart(2,'0')}`;
    frames.push({id,color:color.lo.toDataURL(),colorHi:color.hi.toDataURL(),mask:mask.lo.toDataURL(),depth:depth.lo.toDataURL(),floor:floorView.lo.toDataURL()});
    cells.push({index:i,rect:[x,y,x+FRAME[0],y+FRAME[1]],anchor:[...ANCHOR],floorRect:[32,184,160,312],
      ...(mode==='directions'?{direction:DIRECTIONS[i]}:{}),...(mode==='dance'?{durationMs:1000/12}:{}),
      alphaBounds:bounds.rect,projectedBounds});
    poses.push({index:i,phase:mode==='dance'?i/count:null,direction:mode==='directions'?DIRECTIONS[i]:null,
      rootWorld:[0,0,0],rootProjected:project(camera,[0,0,0]),modelMatrix:character.group.matrixWorld.toArray(),
      bones:character.bones.map(b=>({name:b.name,position:b.position.toArray(),quaternion:b.quaternion.toArray(),matrixWorld:b.matrixWorld.toArray()})),
      feet:['left-ankle','right-ankle'].map(name=>{const p=character.named[name].getWorldPosition(new THREE.Vector3());return{name,world:p.toArray(),screen:project(camera,p.toArray())};})});
  }
  const floorCorners=[[-.5,0,-.5],[.5,0,-.5],[.5,0,.5],[-.5,0,.5]].map(p=>({world:p,screen:project(camera,p)}));
  const registration={version:1,kind:'rendered-3d-sheet',assetKind:mode==='dance'?'animation':'directions',workflow:'rigged-3d-projection-reference',mode,size:size.map(v=>v*supersample),frame:FRAME,
    cellSize:CELL,anchor:ANCHOR,columns,rows,gutter:GUTTER*supersample,captureScale:supersample,order:'row-major',
    cells:cells.map(c=>({...c,rect:c.rect.map(v=>v*supersample),floorRect:c.floorRect.map(v=>v*supersample)})),
    runtimeSheetSize:size,runtimeGutter:GUTTER,runtimeFloorRect:[32,184,160,312],
    authoredRenders:[{role:'neutral-standing',image:'neutral.png'},{role:'rigged-reference',image:'sheet.png'},{role:'floor-registration',image:'guide.png'},{role:'neutral-standing-on-floor',image:'neutral-on-floor.png'}],
    nominalStandingHeight:160,elevationPx:160,occupiedCells:[[0,0]],...(mode==='dance'?{fps:12}:{}),
    projection:'top-down-oblique-square-grid',projectionFormula:{screenX:'96 + 128*x',screenY:'248 + 128*z - 128*y'},
    sourcePixelsPerRuntimePixel:supersample,sourceSize:size.map(v=>v*supersample),
    sourceRole:'floor-free rendered 3D color; auxiliary floor reference is separate',
    geometryAuthority:'authored 3D camera/model/rig; reskin output requires independent verification',
    floorCorners,neutralProjectedBounds:neutralBounds,neutralProjectedCrownHeight:ANCHOR[1]-neutralBounds[1],
    depthPass:{format:'opaque normalized grayscale over object alpha',packing:'THREE.BasicDepthPacking',near:6,far:10},
    maskPass:{format:'opaque grayscale; intensity equals object-color alpha; black is empty'},
    fitting:{perFrame:false,perDirection:false,camera:'fixed',root:'fixed',modelScale:'fixed'}};
  const result={version:2,kind:mode==='dance'?'animation':'directions',workflow:'rigged-3d-reference-capture',
    projection:registration.projection,cellSize:CELL,groundAnchorAlignment:'center',...(mode==='dance'?{fps:12}:{}),
    sprites:cells.map(c=>({id:`${mode}-${String(c.index).padStart(2,'0')}`,index:c.index,image:`frames/frame-${String(c.index).padStart(2,'0')}.png`,size:FRAME,anchor:ANCHOR,
      footprint:[128,128],occupiedCells:[[0,0]],elevationPx:160,artRect:[c.alphaBounds[0],c.alphaBounds[1],c.alphaBounds[2]-c.alphaBounds[0],c.alphaBounds[3]-c.alphaBounds[1]],
      registration:{method:'authored-3d-camera',guide:'guide.json',sourceFrame:c.index},
      ...(mode==='dance'?{durationMs:1000/12}:{direction:c.direction})})),
    provenance:{artwork:'procedural Three.js mesh, material and rig',imageGeneration:false},
    noPostCaptureNormalization:true,visualReviewRequired:'Reskin geometry, identity, motion and style require independent review'};
  const output={frames,sheets:Object.fromEntries(Object.entries(sheets).map(([k,c])=>[k,{hi:c.toDataURL(),lo:copyCanvas(c,...size).toDataURL()}])),
    neutral:{color:neutral.lo.toDataURL(),colorHi:neutral.hi.toDataURL(),floor:neutralFloor.lo.toDataURL()},registration,result,
    scene:editableScene,rig:{model:MODEL,rest:character.rest,parts:character.parts,boneCount:character.bones.length,
      skinVertexCount:character.mesh.geometry.getAttribute('position').count,
      camera:{type:camera.type,matrixWorld:camera.matrixWorld.toArray(),matrixWorldInverse:camera.matrixWorldInverse.toArray(),projectionMatrix:camera.projectionMatrix.toArray(),near:camera.near,far:camera.far}},poses};
  renderer.dispose();return output;
}
if(typeof window!=='undefined')window.renderBundle=renderBundle;
