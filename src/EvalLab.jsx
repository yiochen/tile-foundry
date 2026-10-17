import React, {useEffect, useRef, useState} from 'react';

const base = `${import.meta.env.BASE_URL}assets/`;
const labels = {'not-run':'Not run',passed:'Passed',failed:'Failed',blocked:'Blocked',
  ungraded:'Awaiting review','needs-visual-review':'Needs visual review'};
const statusOf = entry => entry.latest?.status || 'not-run';
const statusLabel = status => labels[status] || status;
const imageCache = new Map();
function loadImage(path) {
  if(!imageCache.has(path))imageCache.set(path,new Promise((resolve,reject)=>{
    const image=new Image();image.onload=()=>resolve(image);
    image.onerror=()=>reject(Error('Could not load the recorded sprite.'));image.src=base+path;
  }));
  return imageCache.get(path);
}

function SpritePreview({sprites, active, compose, showAnchors, guide, showGuide, guideOpacity, raw=false}) {
  const ref = useRef(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    const canvas = ref.current;
    canvas.dataset.ready = 'false';
    setError('');
    const renderGuide = showGuide && guide;
    Promise.all([...sprites,...(renderGuide?[guide]:[])].map(asset=>loadImage(asset.image))).then(loaded => {
      if (!alive) return;
      const images = loaded.slice(0,sprites.length), guideImage = renderGuide&&loaded[sprites.length];
      if(guideImage&&(guideImage.width!==guide.size[0]||guideImage.height!==guide.size[1])){
        throw Error('The SVG dimensions differ from its recorded frame; overlay cannot be aligned safely.');
      }
      // Preserve complete registered frames around a shared root, without alpha fitting.
      const frames = sprites.map((s,i)=>{
        const rect=s.sourceRect,image=images[i];
        if(rect&&!(rect.length===4&&rect.every(Number.isInteger)&&rect[0]>=0&&rect[1]>=0&&rect[2]>rect[0]&&rect[3]>rect[1]&&rect[2]<=image.width&&rect[3]<=image.height)){
          throw Error('Source preview rectangle exceeds the original image.');
        }
        return {...s,size:rect?[rect[2]-rect[0],rect[3]-rect[1]]:[image.width,image.height]};
      });
      if(guide)frames.push(guide);
      const left = Math.min(...frames.map(s=>-s.anchor[0]));
      const top = Math.min(...frames.map(s=>-s.anchor[1]));
      const right = Math.max(...frames.map(s=>s.size[0]-s.anchor[0]));
      const bottom = Math.max(...frames.map(s=>s.size[1]-s.anchor[1]));
      const margin = 24, root = [margin-left,margin-top];
      canvas.width = Math.ceil(right-left+2*margin); canvas.height = Math.ceil(bottom-top+2*margin);
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#eef1e8'; ctx.fillRect(0,0,canvas.width,canvas.height);
      const footprint = sprites[active].footprint || [128,128];
      if(!raw){
        ctx.fillStyle = '#d6dfcd';
        ctx.fillRect(root[0]-footprint[0]/2,root[1]-footprint[1]/2,...footprint);
      }
      (compose ? sprites.map((_,i)=>i) : [active]).forEach(i=>{
        const frame=frames[i],x=root[0]-frame.anchor[0],y=root[1]-frame.anchor[1];
        if(frame.sourceRect){
          ctx.drawImage(images[i],frame.sourceRect[0],frame.sourceRect[1],...frame.size,x,y,...frame.size);
        }else ctx.drawImage(images[i],x,y);
      });
      if(guideImage){
        ctx.save();ctx.globalAlpha=guideOpacity/100;
        ctx.drawImage(guideImage,root[0]-guide.anchor[0],root[1]-guide.anchor[1]);ctx.restore();
      }
      if(showAnchors||guideImage){
        ctx.strokeStyle = '#c03d80';ctx.lineWidth = 1;
        ctx.beginPath();ctx.moveTo(root[0]-8,root[1]);ctx.lineTo(root[0]+8,root[1]);
        ctx.moveTo(root[0],root[1]-8);ctx.lineTo(root[0],root[1]+8);ctx.stroke();
      }
      canvas.dataset.ready = 'true';canvas.dataset.frame = String(active);
      canvas.dataset.anchor = sprites[active].anchor.join(',');
      canvas.dataset.guideOverlay = guideImage?'true':'false';
      canvas.dataset.guideOpacity = String(guideOpacity);
      canvas.dataset.guideAnchor = guide?.anchor.join(',')||'';
    }).catch(e=>alive&&setError(e.message));
    return () => {alive=false;};
  },[sprites,active,compose,showAnchors,guide,showGuide,guideOpacity,raw]);
  return <>{error&&<p role="alert">{error}</p>}<canvas ref={ref} className="eval-sprite-preview" aria-label={raw?'Unprocessed source sequence preview':'Recorded sprites at their stored ground anchor'}/></>;
}

function FrameThumbnail({sprite}) {
  const ref=useRef(null),[error,setError]=useState(false);
  useEffect(()=>{
    let alive=true;
    loadImage(sprite.image).then(image=>{
      if(!alive)return;
      const [x,y,right,bottom]=sprite.sourceRect,c=ref.current;
      c.width=right-x;c.height=bottom-y;c.getContext('2d').drawImage(image,x,y,c.width,c.height,0,0,c.width,c.height);
    }).catch(()=>alive&&setError(true));
    return()=>{alive=false;};
  },[sprite]);
  return error?<span>Preview unavailable</span>:<canvas ref={ref} aria-label={`Raw source frame ${sprite.index+1}`}/>;
}

function CheckList({title, checks}) {
  if(!checks.length)return null;
  return <details className="eval-checks"><summary>{title} · {checks.filter(c=>c.pass).length} / {checks.length} passed</summary>
    <ul>{checks.map((check,i)=><li key={i} className={check.pass===true?'check-pass':check.pass===false?'check-fail':'check-pending'}>
      <strong>{check.pass===true?'✓':check.pass===false?'×':'?'} {check.check.replaceAll('-',' ')}</strong>
      <p>{typeof check.detail==='string'?check.detail:JSON.stringify(check.detail)}</p>
    </li>)}</ul></details>;
}

function Diagnostics({checks=[]}) {
  if(!checks.length)return null;
  return <details className="eval-checks eval-diagnostics"><summary>Image diagnostics · {checks.length} · do not affect grade</summary>
    <ul>{checks.map((check,i)=><li key={i}><strong>{check.check.replaceAll('-',' ')}</strong>
      <p>{typeof check.detail==='string'?check.detail:JSON.stringify(check.detail)}</p></li>)}</ul>
  </details>;
}

function SpritePlayer({sprites, kind, showAnchors, guide, rawSequence}) {
  const raw=Boolean(rawSequence);
  const [frame,setFrame] = useState(0), [playing,setPlaying] = useState(false), [compose,setCompose] = useState(kind==='layered'&&!raw);
  const [showGuide,setShowGuide] = useState(()=>new URLSearchParams(window.location.search).get('overlay')==='svg');
  const [guideOpacity,setGuideOpacity] = useState(65);
  const toggleGuide = value => {
    setShowGuide(value);
    const url=new URL(window.location.href);
    if(value)url.searchParams.set('overlay','svg');else url.searchParams.delete('overlay');
    window.history.replaceState(null,'',url);
  };
  useEffect(() => {
    if(!playing||sprites.length<2)return;
    const first=frame;
    let animation,started;
    const tick=now=>{
      // Use RAF's clock throughout; its first timestamp may precede effect setup.
      started??=now;
      const index=(first+Math.floor(Math.max(0,now-started)*12/1000))%sprites.length;
      setFrame(previous=>previous===index?previous:index);
      animation=requestAnimationFrame(tick);
    };
    animation=requestAnimationFrame(tick);
    return()=>cancelAnimationFrame(animation);
    // Frame changes do not restart the clock; seeking always pauses playback.
  },[playing,sprites]);
  const seek=index=>{
    setPlaying(false);setCompose(false);setFrame(Math.max(0,Math.min(sprites.length-1,index)));
  };
  const label=sprites[frame].direction||sprites[frame].role;
  const hasControls=sprites.length>1||kind==='animation';
  return <div className="eval-player" data-player-source={raw?'raw':'runtime'} data-frame-count={sprites.length} data-playing={playing}>
      {raw&&<><h4>Raw source player</h4><p className="eval-player-note">{rawSequence.note}</p></>}
      <div className={'eval-overlay-comparison'+(guide?' has-svg-guide':'')}>
        {guide&&<div className="eval-overlay-controls">
          <label><input type="checkbox" checked={showGuide} onChange={e=>toggleGuide(e.target.checked)}/> SVG guide overlay</label>
          {showGuide&&<label>Opacity<input aria-label="SVG overlay opacity" type="range" min="10" max="100" step="5" value={guideOpacity} onChange={e=>setGuideOpacity(Number(e.target.value))}/><output>{guideOpacity}%</output></label>}
          <a href={base+guide.image} target="_blank" rel="noreferrer">Original SVG ↗</a>
        </div>}
        <div className="eval-render"><SpritePreview sprites={sprites} active={frame} compose={compose} showAnchors={showAnchors&&(!raw||rawSequence.alignment==='recorded-floor-center')} guide={guide} showGuide={showGuide} guideOpacity={guideOpacity} raw={raw}/></div>
        {guide&&showGuide&&<p className="eval-overlay-caption">Original SVG at the same ground center and cell scale.{guide.heightPx!=null&&` Guide height: ${guide.heightPx}px above the ground center.`}{guide.baseSize&&` Base: ${guide.baseSize.join(' × ')}px.`} The green square is the calibration floor; the cross marks the shared ground anchor.</p>}
      </div>
      {hasControls&&<div className="eval-player-timeline">
        <div className="eval-player-buttons">
          <button className="secondary-button" aria-label="Previous sprite" disabled={sprites.length<2} onClick={()=>seek((frame-1+sprites.length)%sprites.length)}>Previous</button>
          <button className="secondary-button" aria-label={playing?'Pause sprite sequence':'Play sprite sequence'} aria-pressed={playing} disabled={sprites.length<2} onClick={()=>{setCompose(false);setPlaying(p=>!p);}}>{playing?'Pause':'Play'}</button>
          <button className="secondary-button" aria-label="Next sprite" disabled={sprites.length<2} onClick={()=>seek((frame+1)%sprites.length)}>Next</button>
          <span>12 fps · looping</span>
        </div>
        <label className="eval-progress"><span><strong>{compose?'All layers':`Frame ${frame+1} / ${sprites.length}${label?` · ${label}`:''}`}</strong><output>{(frame/12).toFixed(2)}s / {(sprites.length/12).toFixed(2)}s</output></span>
          <input aria-label="Sprite progress" aria-valuetext={`Frame ${frame+1} of ${sprites.length}${label?`, ${label}`:''}`} type="range" min="0" max={sprites.length-1} step="1" value={frame} disabled={sprites.length<2} onPointerDown={()=>setPlaying(false)} onChange={e=>seek(Number(e.target.value))}/>
        </label>
        <div className="eval-frame-controls">
          {kind==='layered'&&!raw&&<label><input type="checkbox" checked={compose} onChange={e=>{setPlaying(false);setCompose(e.target.checked);}}/> Recompose layers at stored anchors</label>}
          <label>Sprite<select aria-label="Eval sprite" value={frame} onChange={e=>seek(Number(e.target.value))}>{sprites.map((s,i)=><option key={s.id} value={i}>{s.direction||s.role||`Frame ${i+1}`}</option>)}</select></label>
        </div>
      </div>}
      <div className="eval-sprite-strip">{sprites.map((s,i)=><button key={s.id} aria-label={`Show eval sprite ${i+1}`} aria-pressed={frame===i} onClick={()=>seek(i)}>{s.sourceRect?<FrameThumbnail sprite={s}/>:<img src={base+s.image} alt={s.direction||s.role||`${raw?'Raw source':'Processed sprite'} ${i+1}`} loading="lazy"/>}<span>{s.direction||s.role||i+1}</span></button>)}</div>
  </div>;
}

function TrialResult({trial, entry, showAnchors}) {
  const control=trial.runMode==='3d-render-control';
  return <div className="eval-result" data-eval-trial={trial.id}>
    <div className="eval-result-heading"><h4>Result</h4><span className={'eval-status status-'+trial.status}>{statusLabel(trial.status)}</span><span>{trial.runId}</span></div>
    <p className="lab-scope" data-eval-policy={trial.policy||'original'}>{trial.assessmentLabel}{trial.assessedAt&&` · ${trial.assessedAt}`}{trial.policy&&` · ${trial.policy}`}{trial.reviewer&&` · ${trial.reviewer}`}</p>
    {trial.reason&&<p className="eval-failure">{trial.reason}</p>}
    {trial.sprites.length>0?<SpritePlayer sprites={trial.sprites} kind={entry.kind} showAnchors={showAnchors} guide={trial.guideOverlay}/>:<>
      <p className="eval-failure">No processed sprites were delivered. The original generation and recorded checks are shown below.</p>
      {trial.previewSequence&&<SpritePlayer sprites={trial.previewSequence.frames} kind={entry.kind} showAnchors={showAnchors} rawSequence={trial.previewSequence}/>}
      {trial.previewUnavailable&&<p className="eval-player-note">Raw sequence unavailable: {trial.previewUnavailable}</p>}
    </>}
    <div className="eval-downloads">{[['result','Result metadata'],['report','Full eval report'],['review','LLM review evidence'],['policyRecord','Grading policy'],['processing','Processing diagnostic'],['submission','Submission'],['sheet','Spritesheet'],['guide','Guide metadata']].filter(([key])=>trial[key]).map(([key,label])=><a key={key} href={base+trial[key]} target="_blank" rel="noreferrer">{label} ↗</a>)}</div>
    <CheckList title="Delivery checks" checks={trial.automaticChecks}/><CheckList title={trial.policy?'LLM visual review':'Visual review'} checks={trial.visualChecks}/>
    <Diagnostics checks={trial.diagnostics}/>
    {!!trial.previews.length&&<div className="eval-artifacts">{trial.previews.map(p=><figure key={p.image}><a href={base+p.image} target="_blank" rel="noreferrer"><img src={base+p.image} alt={p.label.replaceAll('-',' ')} loading="lazy"/></a><figcaption>{p.label.replaceAll('-',' ')}</figcaption></figure>)}</div>}
    <h4 className="eval-source-heading">{control?'Original 3D renders and recipes':'Original generations and prompts'}</h4>
    <div className="eval-artifacts">{trial.sources.map((source,i)=><figure key={source.image}>
      <a href={base+source.image} target="_blank" rel="noreferrer"><img src={base+source.image} alt={`Original ${control?'3D render':'generation'} ${i+1}`} loading="lazy"/></a>
      <figcaption>Original {control?'3D render':'generation'} {i+1} · {source.role}</figcaption>
      <details className="eval-prompt"><summary>{control?'Render instructions':'Generation prompt'} {i+1}</summary><pre>{source.prompt}</pre><a href={base+source.recipe} target="_blank" rel="noreferrer">Exact {control?'render':'generation'} recipe ↗</a></details>
      {!!source.references.length&&<details><summary>{control?'Renderer inputs':'Supplied references'} · {source.references.length}</summary><div className="eval-reference-images">{source.references.map(r=><figure key={r.image}><a href={base+r.image} target="_blank" rel="noreferrer">{r.mediaType==='file'?<span>{r.name} ↗</span>:<img src={base+r.image} alt={`${r.role} reference`} loading="lazy"/>}</a><figcaption>{r.role}</figcaption></figure>)}</div></details>}
    </figure>)}</div>
    {trial.scope&&<p className="lab-scope">{trial.scope}</p>}
  </div>;
}

export default function EvalLab({onlyAnimations=false, showAnchors=false}) {
  const [gallery,setGallery] = useState(null), [error,setError] = useState('');
  const [selected,setSelected] = useState(()=>new URLSearchParams(window.location.search).get('case'));
  const [attempt,setAttempt] = useState('');
  useEffect(()=>{
    let alive=true;
    fetch(base+'eval-gallery.json').then(r=>{if(!r.ok)throw Error(`Could not load eval results (${r.status})`);return r.json();})
      .then(value=>alive&&setGallery(value)).catch(e=>alive&&setError(e.message));
    return ()=>{alive=false;};
  },[]);
  if(error)return <p role="alert">{error}</p>;
  if(!gallery)return <p className="character-intro">Loading eval results…</p>;
  const cases = gallery.cases.filter(c=>!onlyAnimations||c.kind==='animation');
  const entry = cases.find(c=>c.id===selected)||cases[0];
  const trial = entry.trials.find(t=>t.id===attempt)||entry.latest;
  const select = value => {
    setSelected(value);setAttempt('');
    const url=new URL(window.location.href);url.searchParams.set('view',onlyAnimations?'animations':'evals');url.searchParams.set('case',value);
    window.history.replaceState(null,'',url);
  };
  return <div className="eval-lab" data-evals-ready="true">
    <p className="character-intro">{cases.length} cases · {cases.filter(c=>c.latest).length} recorded outcomes. Visual quality is judged by an independent LLM; pixel metrics are diagnostics. Select a case for its prompt, art and review. Animation previews play at 12 fps.</p>
    <div className="eval-case-grid">{cases.map(c=><button key={c.id} data-eval-case={c.id} aria-pressed={entry.id===c.id} onClick={()=>select(c.id)}>
      <strong>{c.title}</strong><span className={'eval-status status-'+statusOf(c)}>{statusLabel(statusOf(c))}</span>
    </button>)}</div>
    <section className="eval-detail" data-eval-selected={entry.id}>
      <div className="eval-detail-heading"><div><span className="eyebrow">EVAL CASE · SUITE V{entry.suiteVersion}</span><h3>{entry.title}</h3></div>
        {!!entry.latest&&<label>Assessment<select aria-label="Eval attempt" value={trial?.id||''} onChange={e=>setAttempt(e.target.value)}>{entry.trials.filter(t=>t.status!=='not-run').slice().reverse().map(t=><option key={t.id} value={t.id}>{t.assessmentLabel} · {t.assessedAt||t.runId} · {statusLabel(t.status)}</option>)}</select></label>}
      </div>
      <div className="eval-user-prompt"><h4>Prompt</h4><pre>{trial?.prompt||entry.prompt}</pre></div>
      <details className="eval-expected"><summary>Expected behavior and geometry</summary>{trial?.policy&&<p className="lab-scope">Original case contract retained. Image-derived pixel tolerances are diagnostic only in this assessment; seams, proportions and contact are judged visually. Delivery metadata remains enforced.</p>}<dl>{Object.entries(entry.expected).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{JSON.stringify(value)}</dd></div>)}</dl><ul>{Object.values(entry.visualChecks).map(text=><li key={text}>{text}</li>)}</ul></details>
      {trial?<TrialResult key={trial.id} trial={trial} entry={entry} showAnchors={showAnchors}/>:<div className="eval-empty"><span className="eval-status status-not-run">Not run</span><p>No generation or review is recorded for this case yet.</p></div>}
    </section>
  </div>;
}
