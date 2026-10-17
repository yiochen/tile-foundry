/** Editable procedural, skinned 3D reference; all registration is authored in world space. */
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export const FRAME = [192, 320];
export const ANCHOR = [96, 248];
export const CELL = 128;
export const DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
export const GUTTER = 32;
export const MODEL = {
  name: 'procedural-seated-adventurer-static-control-v1', nominalStandingHeight: 160,
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
    addPart(`${side}-boot`, box(), 'boots', `${side}-ankle`, [s * .12, .055, .03], [.137, .11, .15]);
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
