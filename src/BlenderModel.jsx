import React, {useEffect, useRef, useState} from 'react';

// Load WebGL only on request; sprite playback also works without GPU support.
export default function BlenderModel({url,gridPitch=2.02}) {
  const host=useRef(null),[error,setError]=useState('');
  useEffect(()=>{
    let alive=true,cleanup=()=>{};
    (async()=>{
      const [THREE,{GLTFLoader},{OrbitControls}]=await Promise.all([
        import('three'),import('three/addons/loaders/GLTFLoader.js'),import('three/addons/controls/OrbitControls.js')]);
      if(!alive)return;
      const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
      renderer.outputColorSpace=THREE.SRGBColorSpace;
      renderer.toneMapping=THREE.ACESFilmicToneMapping;
      host.current.appendChild(renderer.domElement);
      renderer.domElement.setAttribute('aria-label','Interactive rigged Blender character. Drag to orbit; scroll to zoom.');
      const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(34,1,.1,100);
      camera.position.set(0,4.8,5.8);
      const controls=new OrbitControls(camera,renderer.domElement);
      controls.target.set(0,1.35,0);controls.enableDamping=true;
      controls.minDistance=2;controls.maxDistance=12;
      const ambient=new THREE.HemisphereLight(0xcbdfff,0x4c3021,2.1);scene.add(ambient);
      const key=new THREE.DirectionalLight(0xffe0b4,3.6);key.position.set(-3,5,4);scene.add(key);
      const rim=new THREE.DirectionalLight(0xffca87,2);rim.position.set(2,4,-3);scene.add(rim);
      const grid=new THREE.GridHelper(gridPitch*3,3,0x7d9876,0xcbd7c5);scene.add(grid);
      const observer=new ResizeObserver(entries=>{
        const width=entries[0].contentRect.width,height=440;
        renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();
      });observer.observe(host.current);
      let model,mixer,last=performance.now(),elapsed=0;
      const disposeModel=()=>model?.traverse(obj=>{
        obj.geometry?.dispose();
        for(const mat of (Array.isArray(obj.material)?obj.material:[obj.material]).filter(Boolean))mat.dispose();
      });
      cleanup=()=>{renderer.setAnimationLoop(null);observer.disconnect();controls.dispose();disposeModel();renderer.dispose();renderer.domElement.remove();};
      const gltf=await new GLTFLoader().loadAsync(url);
      model=gltf.scene;
      if(!alive){disposeModel();return;}
      scene.add(model);mixer=new THREE.AnimationMixer(model);
      if(gltf.animations.length)mixer.clipAction(gltf.animations[0]).play();
      renderer.setAnimationLoop(now=>{
        elapsed+=Math.min(.1,(now-last)/1000);last=now;
        mixer.setTime(Math.floor(elapsed*12)/12);controls.update();renderer.render(scene,camera);
      });
      host.current.dataset.modelReady='true';
    })().catch(e=>alive&&setError(`3D preview unavailable: ${e.message}. The Blender and GLB files are available below.`));
    return()=>{alive=false;cleanup();};
  },[url,gridPitch]);
  return <>{error&&<p role="alert">{error}</p>}<div className="blender-model" ref={host}/><p className="lab-scope">Drag to orbit, scroll to zoom. The GLB uses browser lighting, base materials and glTF skinning. The captured sprites and editable Blender scene retain the native materials, volume-preserving deformation and authored camera.</p></>;
}
