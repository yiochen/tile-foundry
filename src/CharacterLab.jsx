import {useEffect,useRef,useState} from 'react';

function CharacterPreview({entry,image,showAnchors,label}) {
  const ref=useRef(null);
  useEffect(()=>{
    const c=ref.current,ctx=c.getContext('2d');c.width=192;c.height=320;
    for(let y=0;y<320;y+=12)for(let x=0;x<192;x+=12){ctx.fillStyle=(x/12+y/12)%2?'#edf0e8':'#f6f7f2';ctx.fillRect(x,y,12,12);}
    ctx.drawImage(image,0,0);
    if(showAnchors){
      const [x,y]=entry.anchor;ctx.strokeStyle='#b72e74';ctx.lineWidth=1;ctx.setLineDash([3,3]);ctx.strokeRect(x-64,y-64,128,128);ctx.setLineDash([]);
      ctx.beginPath();ctx.moveTo(x-7,y);ctx.lineTo(x+7,y);ctx.moveTo(x,y-7);ctx.lineTo(x,y+7);ctx.stroke();
      const foot=entry.footMeasurement?.midpoint;
      if(foot&&label!=='Guide'){ctx.fillStyle='#187ab1';ctx.beginPath();ctx.arc(foot[0],foot[1],3,0,Math.PI*2);ctx.fill();}
    }
    c.dataset.ready='true';
  },[entry,image,showAnchors]);
  return <canvas ref={ref} aria-label={`${entry.name}: ${label}`}/>;
}

function GroundedJump({entry,image}) {
  const ref=useRef(null);
  useEffect(()=>{
    const c=ref.current,ctx=c.getContext('2d');c.width=384;c.height=416;
    ctx.fillStyle='#f4f6ef';ctx.fillRect(0,0,384,416);
    const top=160;
    for(let row=0;row<2;row++)for(let col=0;col<3;col++){
      ctx.fillStyle=(col+row)%2?'#dbe9cd':'#e5efd9';ctx.fillRect(col*128,top+row*128,128,128);
      ctx.strokeStyle='#bdcdb0';ctx.strokeRect(col*128+.5,top+row*128+.5,127,127);
    }
    const x=192,y=top+64;
    ctx.drawImage(image,x-entry.anchor[0],y-entry.anchor[1]);
    ctx.strokeStyle='#b72e74';ctx.beginPath();ctx.moveTo(x-10,y);ctx.lineTo(x+10,y);ctx.moveTo(x,y-10);ctx.lineTo(x,y+10);ctx.stroke();
    c.dataset.ready='true';
  },[entry,image]);
  return <canvas ref={ref} className="grounded-jump" aria-label="Extracted airborne courier with its inferred ground anchor at the center of a cell"/>;
}

export default function CharacterLab({data,showAnchors}) {
  const entries=data.characters.trials;
  const [removalMode,setRemovalMode]=useState('chroma');
  const jump=entries.find(e=>e.id===(removalMode==='chroma'?'character-jump-solid':'character-jump-corners'));
  const jumpImage=removalMode==='chroma'?jump.keyedImage:jump.removalImage;
  return <div className="character-lab">
    <p className="character-intro">Seven guides, one courier design. The floor sets position and scale. Pink marks its inferred center; blue marks the visible boot midpoint. Shoe length can extend below the anchor. A simple stick pose leaves room for the model to design the character.</p>
    <label className="character-removal-picker">Solid floor removal <select aria-label="Solid floor removal" value={removalMode} onChange={e=>setRemovalMode(e.target.value)}><option value="chroma">Green chroma key</option><option value="exact">Exact reference subtraction</option></select></label>
    <div className="character-cards">{entries.map((e,i)=>{
      const chroma=removalMode==='chroma'&&e.keyedImage;
      const cutout=chroma||e.usableExtraction;
      const resultPath=chroma?e.keyedImage:e.removalImage;
      return <article className="character-card" key={e.id} data-character={e.id}>
      <span className="eyebrow">CHARACTER TRIAL {String(i+1).padStart(2,'0')}</span><h3>{e.name}</h3>
      <div className="character-panels">{[[e.guideImage,'Guide'],[e.withGuide,'AI result'],[resultPath,chroma?'Chroma-key cutout':e.usableExtraction?'Extracted sprite':'Subtraction diagnostic']].map(([path,label])=><figure key={path}><CharacterPreview entry={e} image={data.images[path]} showAnchors={showAnchors} label={label}/><figcaption>{label}</figcaption></figure>)}</div>
      <dl className="workflow-metrics">
        <div><dt>Ground anchor</dt><dd>{e.anchor.join(', ')} · inferred</dd></div>
        <div><dt>{e.pose==='standing'?'Visible boots relative to center':'Visible boots relative to guide'}</dt><dd>{e.metrics.footDelta.map(v=>v.toFixed(1)).join(', ')} px</dd></div>
        <div><dt>Boot measurement uncertainty</dt><dd>±{e.footMeasurement.uncertaintyPixels.toFixed(1)} px</dd></div>
        <div><dt>Feet above ground anchor</dt><dd>{e.metrics.observedElevation.toFixed(1)} px</dd></div>
        <div><dt>Floor removal</dt><dd className={cutout?'metric-pass':'metric-fail'}>{chroma?'Green keyed; soft edges':e.usableExtraction?'Detached marks removed':'Floor remains'}</dd></div>
      </dl>
      <p className="workflow-note">{chroma?'The measured floor sets scale and anchor before green is keyed. Pale corner remnants are removed only when detached. Mixed shoe edges are approximate; reserve green in the floor region.':e.usableExtraction?(e.pose==='jumping'?'The complete character component survives; its anchor stays below the airborne feet.':'The complete character component survives; its inferred anchor remains at the cell center.'):'Exact subtraction cannot remove a floor that the model repainted. This preview is a diagnostic, not a usable cutout.'}</p>
    </article>})}</div>
    {jump&&<section className="reuse-scene"><span className="eyebrow">ANCHOR WITHOUT FOOT FITTING</span><h3>Airborne art. A fixed ground point.</h3><p>The cutout is placed by the measured floor center, with its original scale and frame. Its feet remain above that point.</p><GroundedJump entry={jump} image={data.images[jumpImage]}/></section>}
    <p className="lab-scope">One output per guide, not a reliability benchmark. Visible boot extents are descriptive, not anchor errors. No boot annotations tune position or scale. Chroma keying permits solid calibration floors but does not recover an exact character matte.</p>
  </div>;
}
