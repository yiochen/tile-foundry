import React, {useEffect, useRef, useState} from 'react';

const base = `${import.meta.env.BASE_URL}assets/`;
const labels = {'not-run':'Not run',passed:'Passed',failed:'Failed',blocked:'Blocked',
  ungraded:'Awaiting review','needs-visual-review':'Needs visual review'};
const statusOf = entry => entry.latest?.status || 'not-run';
const statusLabel = status => labels[status] || status;

function SpritePreview({sprites, active, compose, showAnchors}) {
  const ref = useRef(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    const canvas = ref.current;
    canvas.dataset.ready = 'false';
    setError('');
    Promise.all(sprites.map(sprite => new Promise((resolve,reject) => {
      const image = new Image(); image.src = base+sprite.image;
      image.onload = () => resolve(image); image.onerror = () => reject(Error('Could not load the recorded sprite.'));
    }))).then(images => {
      if (!alive) return;
      // Preserve complete registered frames around a shared root, without alpha fitting.
      const left = Math.min(...sprites.map(s=>-s.anchor[0]));
      const top = Math.min(...sprites.map(s=>-s.anchor[1]));
      const right = Math.max(...sprites.map((s,i)=>images[i].width-s.anchor[0]));
      const bottom = Math.max(...sprites.map((s,i)=>images[i].height-s.anchor[1]));
      const margin = 24, root = [margin-left,margin-top];
      canvas.width = right-left+2*margin; canvas.height = bottom-top+2*margin;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#eef1e8'; ctx.fillRect(0,0,canvas.width,canvas.height);
      const footprint = sprites[active].footprint || [128,128];
      ctx.fillStyle = '#d6dfcd';
      ctx.fillRect(root[0]-footprint[0]/2,root[1]-footprint[1]/2,...footprint);
      (compose ? sprites.map((_,i)=>i) : [active]).forEach(i=>ctx.drawImage(images[i],root[0]-sprites[i].anchor[0],root[1]-sprites[i].anchor[1]));
      if(showAnchors){
        ctx.strokeStyle = '#c03d80';ctx.lineWidth = 1;
        ctx.beginPath();ctx.moveTo(root[0]-8,root[1]);ctx.lineTo(root[0]+8,root[1]);
        ctx.moveTo(root[0],root[1]-8);ctx.lineTo(root[0],root[1]+8);ctx.stroke();
      }
      canvas.dataset.ready = 'true';canvas.dataset.frame = String(active);
      canvas.dataset.anchor = sprites[active].anchor.join(',');
    }).catch(e=>alive&&setError(e.message));
    return () => {alive=false;};
  },[sprites,active,compose,showAnchors]);
  return <>{error&&<p role="alert">{error}</p>}<canvas ref={ref} className="eval-sprite-preview" aria-label="Recorded sprites at their stored ground anchor"/></>;
}

function CheckList({title, checks}) {
  if(!checks.length)return null;
  return <details className="eval-checks"><summary>{title} · {checks.filter(c=>c.pass).length} / {checks.length} passed</summary>
    <ul>{checks.map((check,i)=><li key={i} className={check.pass?'check-pass':'check-fail'}>
      <strong>{check.pass?'✓':'×'} {check.check.replaceAll('-',' ')}</strong>
      <p>{typeof check.detail==='string'?check.detail:JSON.stringify(check.detail)}</p>
    </li>)}</ul></details>;
}

function TrialResult({trial, entry, showAnchors}) {
  const [frame,setFrame] = useState(0), [playing,setPlaying] = useState(false), [compose,setCompose] = useState(entry.kind==='layered');
  const sprites = trial.sprites;
  useEffect(() => {
    if(!playing||!sprites.length)return;
    const timer = setTimeout(()=>setFrame(i=>(i+1)%sprites.length),1000/12);
    return ()=>clearTimeout(timer);
  },[playing,frame,sprites]);
  return <div className="eval-result" data-eval-trial={trial.id}>
    <div className="eval-result-heading"><h4>Result</h4><span className={'eval-status status-'+trial.status}>{statusLabel(trial.status)}</span><span>{trial.runId}</span></div>
    {trial.reason&&<p className="eval-failure">{trial.reason}</p>}
    {sprites.length>0?<>
      <div className="eval-render"><SpritePreview sprites={sprites} active={frame} compose={compose} showAnchors={showAnchors}/></div>
      {sprites.length>1&&<div className="eval-frame-controls">
        {entry.kind==='animation'&&<button className="secondary-button" onClick={()=>setPlaying(p=>!p)}>{playing?'Pause':'Play'} · 12 fps</button>}
        {entry.kind==='layered'&&<label><input type="checkbox" checked={compose} onChange={e=>setCompose(e.target.checked)}/> Recompose layers at stored anchors</label>}
        <label>Sprite<select aria-label="Eval sprite" value={frame} onChange={e=>{setPlaying(false);setFrame(Number(e.target.value));}}>{sprites.map((s,i)=><option key={s.id} value={i}>{s.direction||s.role||`Frame ${i+1}`}</option>)}</select></label>
      </div>}
      <div className="eval-sprite-strip">{sprites.map((s,i)=><button key={s.id} aria-label={`Show eval sprite ${i+1}`} aria-pressed={frame===i} onClick={()=>{setPlaying(false);setFrame(i);}}><img src={base+s.image} alt={s.direction||s.role||`Processed sprite ${i+1}`} loading="lazy"/><span>{s.direction||s.role||i+1}</span></button>)}</div>
    </>:<p className="eval-failure">No processed sprites were delivered. The original generation and recorded checks are shown below.</p>}
    <div className="eval-downloads">{[['result','Result metadata'],['report','Full eval report'],['processing','Processing diagnostic'],['submission','Submission'],['sheet','Spritesheet'],['guide','Guide metadata']].filter(([key])=>trial[key]).map(([key,label])=><a key={key} href={base+trial[key]} target="_blank" rel="noreferrer">{label} ↗</a>)}</div>
    <CheckList title="Automatic checks" checks={trial.automaticChecks}/><CheckList title="Visual review" checks={trial.visualChecks}/>
    {!!trial.previews.length&&<div className="eval-artifacts">{trial.previews.map(p=><figure key={p.image}><a href={base+p.image} target="_blank" rel="noreferrer"><img src={base+p.image} alt={p.label.replaceAll('-',' ')} loading="lazy"/></a><figcaption>{p.label.replaceAll('-',' ')}</figcaption></figure>)}</div>}
    <h4 className="eval-source-heading">Original generations and prompts</h4>
    <div className="eval-artifacts">{trial.sources.map((source,i)=><figure key={source.image}>
      <a href={base+source.image} target="_blank" rel="noreferrer"><img src={base+source.image} alt={`Original generation ${i+1}`} loading="lazy"/></a>
      <figcaption>Original generation {i+1} · {source.role}</figcaption>
      <details className="eval-prompt"><summary>Generation prompt {i+1}</summary><pre>{source.prompt}</pre><a href={base+source.recipe} target="_blank" rel="noreferrer">Exact generation recipe ↗</a></details>
      {!!source.references.length&&<details><summary>Supplied references · {source.references.length}</summary><div className="eval-reference-images">{source.references.map(r=><figure key={r.image}><a href={base+r.image} target="_blank" rel="noreferrer"><img src={base+r.image} alt={`${r.role} reference`} loading="lazy"/></a><figcaption>{r.role}</figcaption></figure>)}</div></details>}
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
    <p className="character-intro">{cases.length} cases · {cases.filter(c=>c.latest).length} recorded outcomes. Select a case to see its prompt, latest result, original generation and review. Animation previews play at 12 fps.</p>
    <div className="eval-case-grid">{cases.map(c=><button key={c.id} data-eval-case={c.id} aria-pressed={entry.id===c.id} onClick={()=>select(c.id)}>
      <strong>{c.title}</strong><span className={'eval-status status-'+statusOf(c)}>{statusLabel(statusOf(c))}</span>
    </button>)}</div>
    <section className="eval-detail" data-eval-selected={entry.id}>
      <div className="eval-detail-heading"><div><span className="eyebrow">EVAL CASE · SUITE V{entry.suiteVersion}</span><h3>{entry.title}</h3></div>
        {!!entry.latest&&<label>Attempt<select aria-label="Eval attempt" value={trial?.id||''} onChange={e=>setAttempt(e.target.value)}>{entry.trials.filter(t=>t.status!=='not-run').slice().reverse().map(t=><option key={t.id} value={t.id}>{t.runId} · {statusLabel(t.status)}</option>)}</select></label>}
      </div>
      <div className="eval-user-prompt"><h4>Prompt</h4><pre>{trial?.prompt||entry.prompt}</pre></div>
      <details className="eval-expected"><summary>Expected behavior and geometry</summary><dl>{Object.entries(entry.expected).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{JSON.stringify(value)}</dd></div>)}</dl><ul>{Object.values(entry.visualChecks).map(text=><li key={text}>{text}</li>)}</ul></details>
      {trial?<TrialResult key={trial.id} trial={trial} entry={entry} showAnchors={showAnchors}/>:<div className="eval-empty"><span className="eval-status status-not-run">Not run</span><p>No generation or review is recorded for this case yet.</p></div>}
    </section>
  </div>;
}
