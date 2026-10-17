import React, {useEffect, useState} from 'react';
import {SpritePlayer} from './EvalLab.jsx';
import BlenderModel from './BlenderModel.jsx';

const base=`${import.meta.env.BASE_URL}assets/`;
export default function BlenderLab({showAnchors}) {
  const [data,setData]=useState(null),[error,setError]=useState(''),[inspect,setInspect]=useState(false);
  useEffect(()=>{
    let alive=true;
    fetch(base+'blender-adventurer.json').then(r=>{if(!r.ok)throw Error('Could not load Blender experiment');return r.json();})
      .then(d=>alive&&setData(d)).catch(e=>alive&&setError(e.message));
    return()=>{alive=false;};
  },[]);
  if(error)return <p role="alert">{error}</p>;
  if(!data)return <p>Loading Blender character…</p>;
  return <section className="blender-lab" data-blender-ready="true">
    <div className="blender-intro"><span className="eyebrow">AUTHORED 3D · STYLE REFINEMENT EXPERIMENT</span>
      <h3>Dancing adventurer</h3><p>A shaped face and layered hair, tailored blue tunic, modeled hands and leather boots. The editable Blender character has {data.bones} bones and world-space foot controls. The loop uses 24 complete frames at 12 fps.</p>
    </div>
    <div className="blender-designs">{data.comparisons.map(c=><figure key={c.image}>
      <div><a href={base+c.image} target="_blank" rel="noreferrer"><img src={base+c.image} alt={c.title}/></a></div><figcaption><strong>{c.title}</strong><p>{c.note}</p></figcaption>
    </figure>)}</div>
    <h4>Direct Blender animation</h4><p className="lab-scope">Fixed 35° orthographic character camera, unchanged across frames. The ground root remains (96, 248) on a 128px logical grid. This character camera foreshortens the physical floor; the square-grid projection is shown above for comparison.</p>
    <SpritePlayer sprites={data.controlFrames} kind="animation" showAnchors={showAnchors}/>
    <details className="blender-source"><summary>Blender MCP screenshots · before, after and animation validation</summary><p>Captured through MCP’s look tool. Front, side and three-quarter views exposed the inward elbow bend. The corrected rig also has continuous elbow/knee skin, aligned wrists and stable foot transforms.</p>{data.validationImages.map(v=><figure key={v.image}><a href={base+v.image} target="_blank" rel="noreferrer"><img src={base+v.image} alt={v.label}/></a><figcaption>{v.label}</figcaption></figure>)}</details>
    <button className="secondary-button" aria-expanded={inspect} onClick={()=>setInspect(v=>!v)}>{inspect?'Close 3D inspection':'Inspect the animated 3D model'}</button>
    {inspect&&<BlenderModel url={base+data.model}/>}
    <h4>Imagegen · style refinement only</h4><p>{data.reskinNote}</p>
    {data.reskinFrames?.length>0&&<SpritePlayer sprites={data.reskinFrames} kind="animation" showAnchors={showAnchors}/>}
    {data.rawSequence&&<SpritePlayer sprites={data.rawSequence.frames} kind="animation" showAnchors={false} rawSequence={data.rawSequence}/>}
    <details className="blender-source"><summary>Original AI atlas · export rejected</summary><a href={base+data.reskinSource} target="_blank" rel="noreferrer"><img src={base+data.reskinSource} alt="Unchanged imagegen atlas showing enlarged poses and row drift"/></a></details>
    <details className="eval-prompt"><summary>Current single-frame imagegen prompt</summary><pre>{data.singlePrompt}</pre></details>
    <details className="eval-prompt"><summary>Earlier atlas prompt and processing evidence</summary><pre>{data.prompt}</pre><p>{data.processingNote}</p></details>
    <div className="eval-downloads">{data.downloads.map(d=><a key={d.path} href={base+d.path} download>{d.label} ↓</a>)}</div>
    <p className="lab-scope">A focused character prototype. The existing eval grades are retained; this experiment has not been scored as a fresh full-suite run. Source renders, model, rig, prompt and unaltered AI output are saved.</p>
  </section>;
}
