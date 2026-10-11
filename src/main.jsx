import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
import CharacterLab from './CharacterLab.jsx';
import AnimationLab from './AnimationLab.jsx';

// Vite's base URL keeps asset requests portable under a repository subpath.
const base = `${import.meta.env.BASE_URL}assets/`;
const fetchJSON = async name => {
  const r = await fetch(base + name);
  if (!r.ok) throw new Error(`Could not load ${name} (${r.status})`);
  return r.json();
};
const loadImage = url => new Promise((resolve, reject) => {
  const image = new Image(); image.onload = () => resolve(image);
  image.onerror = () => reject(new Error(`Could not load ${url}`)); image.src = url;
});
const download = (blob, name) => {
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
};

function WorkflowPreview({entry,image,outline}) {
  const ref=useRef(null);
  useEffect(()=>{
    const canvas=ref.current, ctx=canvas.getContext('2d'), W=320;
    canvas.width=W;canvas.height=552;ctx.clearRect(0,0,W,552);
    ctx.fillStyle='#f4f6ef';ctx.fillRect(0,0,W,258);
    ctx.fillStyle='#bdc9b4';
    for(let y=6;y<258;y+=12)for(let x=6;x<W;x+=12)ctx.fillRect(x,y,1,1);
    const [ax,ay]=entry.anchor;
    ctx.drawImage(image,W/2-ax,238-ay);
    if(outline){ctx.strokeStyle='#357967';ctx.lineWidth=1;ctx.setLineDash([4,3]);
      ctx.strokeRect(W/2-64,238-entry.metrics.targetBodyHeight,128,entry.metrics.targetBodyHeight);
      ctx.beginPath();ctx.moveTo(W/2-64,238-(entry.elevation||32));ctx.lineTo(W/2+64,238-(entry.elevation||32));ctx.stroke();ctx.setLineDash([]);}
    ctx.fillStyle='#357967';ctx.beginPath();ctx.arc(W/2,238,3,0,Math.PI*2);ctx.fill();
    // Three columns, two rows; ground pitch stays 128 for every workflow.
    const s=296/384, x=12, y=279, headroom=Math.max(0,entry.artRect[3]-128)*s;
    ctx.fillStyle='#91d844';ctx.fillRect(x,y,296,256*s+headroom);
    for(let row=0;row<2;row++)for(let col=0;col<3;col++)ctx.drawImage(image,
      x+(col+.5)*128*s-ax*s,y+headroom+(row+1)*128*s-ay*s,image.width*s,image.height*s);
    canvas.dataset.ready='true';
  },[entry,image,outline]);
  return <canvas ref={ref} className="workflow-preview" aria-label={`${entry.name}: isolated sprite and six touching neighbors`}/>;
}

function MaterialScene({data}) {
  const ref=useRef(null);
  useEffect(()=>{
    const c=ref.current, ctx=c.getContext('2d');c.width=1280;c.height=550;
    ctx.fillStyle='#f4f6ef';ctx.fillRect(0,0,c.width,c.height);
    const s=.92,pitch=128*s,left=(1280-10*pitch)/2,top=144;
    for(let row=0;row<3;row++)for(let col=0;col<10;col++){
      ctx.drawImage(data.images[data.assets.ground[(col+row)%3]],left+col*pitch,top+row*pitch,pitch+.1,pitch+.1);
    }
    const heights=[16,32,64,96];
    for(let row=0;row<3;row++)for(let col=0;col<10;col++){
      if(col===4||col===5)continue;
      const material=col<4?'plastic':'wood', height=heights[(col+row)%4];
      const t=data.workflows.lockedVariants.find(t=>t.material===material&&t.elevation===height), im=data.images[t.image];
      ctx.drawImage(im,left+(col+.5)*pitch-t.anchor[0]*s,top+(row+1)*pitch-t.anchor[1]*s,im.width*s,im.height*s);
    }
    c.dataset.ready='true';
  },[data]);
  return <canvas ref={ref} className="material-scene" aria-label="Plastic and wood blocks at four heights, overlapping back rows on the same square grid"/>;
}

function WorkflowLab({data,outline}) {
  const [material,setMaterial]=useState('plastic'),[height,setHeight]=useState(32);
  const locked=data.workflows.lockedVariants.find(t=>t.material===material&&t.elevation===height);
  const cards=data.workflows.cards.map(t=>t.id.startsWith('locked-')?locked:t);
  return <div className="workflow-lab">
    <div className="lab-intro"><p>One shape, five trials. Compare block and sphere style references against the SVG-only render. The SVG target is a 128 × 128 top with a 32 px front wall.</p><div className="lab-controls"><span>SVG material card</span><label><span className="sr-only">Material variant</span><select value={material} onChange={e=>setMaterial(e.target.value)}><option value="plastic">Coral plastic</option><option value="wood">Honey wood</option></select></label><label><span className="sr-only">SVG height</span><select value={height} onChange={e=>setHeight(Number(e.target.value))}>{[16,32,64,96].map(h=><option value={h} key={h}>{h} px high</option>)}</select></label></div></div>
    <div className="workflow-cards">{cards.map((t,i)=><article className="workflow-card" key={t.id} data-workflow={i} data-workflow-id={t.id}>
      <div className="workflow-heading"><span className="eyebrow">EXPERIMENT 0{i+1}</span><h3>{t.name}</h3><p>{t.method}</p></div>
      <WorkflowPreview entry={t} image={data.images[t.image]} outline={outline}/>
      <dl className="workflow-metrics"><div><dt>Uncovered pixels</dt><dd className={t.metrics.coverage.ok?'metric-pass':'metric-fail'}>{t.metrics.coverage.uncoveredPixels.toLocaleString()} / 16,384</dd></div><div><dt>Far / near width</dt><dd>{t.metrics.parallel.farWidth} / {t.metrics.parallel.nearWidth} px</dd></div><div><dt>Body / SVG target</dt><dd>{t.metrics.bodyHeight} / {t.metrics.targetBodyHeight} px</dd></div><div><dt>SVG silhouette match</dt><dd>{(100*t.metrics.silhouetteIoU).toFixed(1)}%</dd></div><div><dt>Exact SVG alpha</dt><dd>{t.metrics.alphaExact?'Yes':'No'}</dd></div></dl><p className="workflow-note">{t.note}</p>
    </article>)}</div>
    <p className="lab-scope">The sphere trial keeps the block-reference prompt unchanged and replaces only the second image. One saved output per SVG strategy, generated at different times. Silhouette metrics do not measure internal detail or color continuity.</p>
    <section className="reuse-scene"><div><span className="eyebrow">ONE MATERIAL → MANY TILES</span><h3>Shared footprint. Four heights.</h3><p>The same two generated materials feed eight exact SVG variants. Foreground blocks overlap the back rows.</p></div><MaterialScene data={data}/><button className="secondary-button" onClick={()=>document.querySelector('.material-scene').toBlob(blob=>blob&&download(blob,'svg-material-scene.png'))}>Export this scene PNG ↓</button></section>
  </div>;
}

function App() {
  const [data,setData] = useState(null), [failure,setFailure] = useState('');
  const [scene,setScene] = useState(null), [preset,setPreset] = useState('village');
  const [selected,setSelected] = useState('tree'), [mode,setMode] = useState(() => {
    const view=new URLSearchParams(window.location.search).get('view');
    return ['scene','cuts','atlas','workflows','characters','animations'].includes(view)?view:'scene';
  });
  const [tool,setTool] = useState('inspect'), [grid,setGrid] = useState(false);
  const [anchors,setAnchors] = useState(false), [footprints,setFootprints] = useState(false);
  const [renderer,setRenderer] = useState('atlas'), [zoom,setZoom] = useState(100);
  const [cell,setCell] = useState(null), [history,setHistory] = useState([]);
  const [status,setStatus] = useState(''), [assetInfo,setAssetInfo] = useState(false);
  const canvasRef=useRef(null), containerRef=useRef(null), layoutRef=useRef(null);
  const [containerWidth,setContainerWidth] = useState(700);
  useEffect(() => {
    let alive=true;
    (async () => {
      const [assets,atlas,village,stress,contact,validation,workflows,characters,gallery] = await Promise.all(
        ['tiles.json','atlas.json','village.json','stress.json','contact.json','validation.json','workflows.json','characters.json','skill-gallery.json'].map(fetchJSON));
      const urls=[...new Set([...assets.tiles.map(t=>t.image),...assets.ground,assets.road,assets.roadCenter,'atlas.png',...workflows.cards.map(t=>t.image),...workflows.lockedVariants.map(t=>t.image),...characters.trials.flatMap(t=>[t.guideImage,t.withGuide,t.removalImage,t.keyedImage].filter(Boolean)),gallery.floor.image,...gallery.animations.flatMap(a=>a.frames.map(f=>f.image))])];
      const entries=await Promise.all(urls.map(async url=>[url,await loadImage(base+url)]));
      if(alive){setData({assets,atlas,village,stress,contact,validation,workflows,characters,gallery,images:Object.fromEntries(entries)});setScene(village);}
    })().catch(e=>alive&&setFailure(e.message));
    return () => {alive=false;};
  },[]);
  useEffect(() => {
    if(!containerRef.current) return;
    const ro=new ResizeObserver(entries=>setContainerWidth(Math.floor(entries[0].contentRect.width)));
    ro.observe(containerRef.current); return () => ro.disconnect();
  },[data]);
  const tile=data?.assets.tiles.find(t=>t.id===selected);
  useEffect(() => {
    if(!data||!scene||!canvasRef.current) return;
    const canvas=canvasRef.current;
    const W=Math.max(240,containerWidth), s=Math.min(72,(W-32)/scene.width)*zoom/100;
    const fit=Math.min(s,(W-24)/scene.width), top=108*fit/64+18;
    const H=mode==='scene'?Math.ceil(top+scene.height*fit+18):mode==='cuts'?440:340;
    const ratio=window.devicePixelRatio||1;
    canvas.width=Math.round(W*ratio);canvas.height=Math.round(H*ratio);
    canvas.style.width=W+'px';canvas.style.height=H+'px';
    const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);
    ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
    const fill=(color,x,y,w,h)=>{ctx.fillStyle=color;ctx.fillRect(x,y,w,h);};
    const dot=(x,y,color='#257774')=>{ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fill();};
    const checker=(x,y,w,h)=>{for(let yy=y;yy<y+h;yy+=12)for(let xx=x;xx<x+w;xx+=12)fill(((xx-x)/12+(yy-y)/12)%2?'#edf0e8':'#f6f7f2',xx,yy,Math.min(12,x+w-xx),Math.min(12,y+h-yy));};
    const drawTile=(id,bx,by,scale)=>{
      const t=data.assets.tiles.find(t=>t.id===id);
      if(renderer==='atlas'){
        const f=data.atlas.frames[id], r=f.frame;
        ctx.drawImage(data.images['atlas.png'],r.x,r.y,r.w,r.h,bx-f.anchor[0]*scale,by-f.anchor[1]*scale,r.w*scale,r.h*scale);
      }else ctx.drawImage(data.images[t.image],bx-t.anchor[0]*scale,by-t.anchor[1]*scale,t.size[0]*scale,t.size[1]*scale);
    };
    ctx.clearRect(0,0,W,H);
    if(mode==='scene'){
      const left=(W-scene.width*fit)/2, groundTop=top;
      layoutRef.current={left,top:groundTop,size:fit,width:scene.width,height:scene.height};
      ctx.save();ctx.shadowColor='rgba(38,69,27,.14)';ctx.shadowBlur=18;ctx.shadowOffsetY=8;
      fill('#91d844',left,groundTop,scene.width*fit,scene.height*fit);ctx.restore();
      for(let row=0;row<scene.height;row++)for(let col=0;col<scene.width;col++){
        const road=scene.roadColumns.includes(col);
        const centerCol=scene.roadColumns[Math.floor(scene.roadColumns.length/2)];
        const ground=road?(col===centerCol?data.assets.roadCenter:data.assets.road):data.assets.ground[(col*7+row*11)%3];
        ctx.drawImage(data.images[ground],left+col*fit,groundTop+row*fit,fit+.15,fit+.15);
      }
      const scale=fit/data.assets.cellSize;
      const rowAnchor=scene.groundAnchorAlignment==='center'?.5:1;
      [...scene.objects].sort((a,b)=>a.row-b.row||a.col-b.col).forEach(o=>drawTile(o.tileId,left+(o.col+.5)*fit,groundTop+(o.row+rowAnchor)*fit,scale));
      if(grid){ctx.strokeStyle='rgba(35,67,22,.24)';ctx.lineWidth=1;ctx.beginPath();
        for(let col=0;col<=scene.width;col++){const x=left+col*fit;ctx.moveTo(x,groundTop);ctx.lineTo(x,groundTop+scene.height*fit);}
        for(let row=0;row<=scene.height;row++){const y=groundTop+row*fit;ctx.moveTo(left,y);ctx.lineTo(left+scene.width*fit,y);}ctx.stroke();}
      scene.objects.forEach(o=>{
        const t=data.assets.tiles.find(t=>t.id===o.tileId), bx=left+(o.col+.5)*fit, by=groundTop+(o.row+rowAnchor)*fit;
        if(footprints){ctx.strokeStyle='rgba(32,64,109,.75)';ctx.fillStyle='rgba(115,178,255,.18)';
          const c=t.collision;ctx.fillRect(bx+c.x*scale,by+c.y*scale,c.width*scale,c.height*scale);
          ctx.strokeRect(bx+c.x*scale,by+c.y*scale,c.width*scale,c.height*scale);}
        if(anchors)dot(bx,by);
      });
      if(cell){ctx.strokeStyle='#fffdf3';ctx.lineWidth=2;ctx.strokeRect(left+cell.col*fit+1,groundTop+cell.row*fit+1,fit-2,fit-2);}
    }else if(mode==='cuts'){
      layoutRef.current=null;
      const cols=W<450?2:4, gap=16, frameW=(W-(cols+1)*gap)/cols;
      const scale=Math.min(frameW/192,.64), frameH=320*scale;
      const rows=Math.ceil(data.assets.tiles.length/cols), realHeight=rows*(frameH+50)+16;
      if(H!==realHeight){canvas.height=Math.ceil(realHeight*ratio);canvas.style.height=realHeight+'px';ctx.scale(ratio,ratio);}
      data.assets.tiles.forEach((t,i)=>{
        const x=gap+(i%cols)*(frameW+gap), y=16+Math.floor(i/cols)*(frameH+50);
        checker(x,y,frameW,frameH);ctx.strokeStyle='#d2d8cc';ctx.strokeRect(x,y,frameW,frameH);
        const bx=x+frameW/2, by=y+t.anchor[1]*scale;
        drawTile(t.id,bx,by,scale);dot(bx,by);
        ctx.fillStyle='#33423a';ctx.font='12px system-ui';ctx.textAlign='center';
        ctx.fillText(t.name,bx,y+frameH+20);ctx.fillStyle='#798379';ctx.fillText(`${t.artRect[2]} × ${t.artRect[3]} art`,bx,y+frameH+37);
      });
    }else{
      layoutRef.current=null;
      const image=data.images['atlas.png'], scale=Math.min((W-32)/image.width,1.15), x=(W-image.width*scale)/2,y=22;
      checker(x,y,image.width*scale,image.height*scale);ctx.drawImage(image,x,y,image.width*scale,image.height*scale);
      Object.entries(data.atlas.frames).forEach(([id,f])=>{
        const r=f.frame;ctx.strokeStyle='#257774';ctx.lineWidth=1;
        ctx.strokeRect(x+r.x*scale,y+r.y*scale,r.w*scale,r.h*scale);
        dot(x+(r.x+f.anchor[0])*scale,y+(r.y+f.anchor[1])*scale);
      });
    }
    canvas.dataset.ready='true';
  },[data,scene,mode,renderer,grid,anchors,footprints,zoom,containerWidth,cell]);
  const remember=next=>{setHistory(h=>[...h.slice(-29),scene]);setScene(next);};
  const undo=()=>{if(history.length){setScene(history.at(-1));setHistory(h=>h.slice(0,-1));setStatus('Last edit undone');}};
  const changePreset=value=>{setPreset(value);setScene(data[value]);setHistory([]);setCell(null);};
  const interact=event=>{
    if(!layoutRef.current||!scene) return;
    const bounds=canvasRef.current.getBoundingClientRect(), l=layoutRef.current;
    const col=Math.floor((event.clientX-bounds.left-l.left)/l.size), row=Math.floor((event.clientY-bounds.top-l.top)/l.size);
    if(col<0||row<0||col>=l.width||row>=l.height) return;
    setCell({col,row});
    const existing=scene.objects.find(o=>o.col===col&&o.row===row);
    if(tool==='inspect'){if(existing)setSelected(existing.tileId);setStatus(`Cell ${col}, ${row}${existing?' · '+existing.tileId:' · empty'}`);return;}
    const objects=scene.objects.filter(o=>o.col!==col||o.row!==row);
    if(tool==='place')objects.push({col,row,tileId:selected});
    remember({...scene,objects});setStatus(tool==='place'?`Placed ${selected} at ${col}, ${row}`:`Cleared ${col}, ${row}`);
  };
  const importScene=async event=>{
    try{const file=event.target.files[0];if(!file)return;const next=JSON.parse(await file.text());
      if(!Number.isInteger(next.width)||!Number.isInteger(next.height)||next.width<1||next.height<1||next.width>40||next.height>40||!Array.isArray(next.objects)||!Array.isArray(next.roadColumns))throw Error('Invalid scene dimensions or arrays');
      if(next.groundAnchorAlignment!==undefined&&!['bottom','center'].includes(next.groundAnchorAlignment))throw Error('Invalid ground anchor alignment');
      const ids=new Set(data.assets.tiles.map(t=>t.id)), occupied=new Set();
      next.objects.forEach(o=>{const key=`${o.col},${o.row}`;if(!ids.has(o.tileId)||!Number.isInteger(o.col)||!Number.isInteger(o.row)||o.col<0||o.row<0||o.col>=next.width||o.row>=next.height||occupied.has(key))throw Error('Unknown tile, invalid position, or duplicate cell');occupied.add(key);});
      if(next.roadColumns.some(c=>!Number.isInteger(c)||c<0||c>=next.width))throw Error('Invalid road columns');
      remember(next);setCell(null);setStatus(`Loaded ${file.name}`);
    }catch(e){setStatus(`Import failed: ${e.message}`);}event.target.value='';
  };
  if(failure)return <main className="boot"><h1>Tile Foundry</h1><p role="alert">{failure}</p><p>Run <code>npm run assets</code> before starting the playground.</p></main>;
  if(!data)return <main className="boot">Loading tiles…</main>;
  return <>
    <header className="app-header"><div className="brand"><div className="brand-mark">▦</div><div><h1>Tile Foundry</h1><span>Generate once. Build a world.</span></div></div><div className="header-right"><span className="project-label">TOY VILLAGE / STUDY 01</span><span className="ready-badge"><i/> Assets ready</span></div></header>
    <div className={'workspace '+(['workflows','characters','animations'].includes(mode)?'lab-mode':'')}>
      <aside className="library"><div className="section-heading"><h2>Tile library</h2><span>04</span></div><p className="subtle">One grid. Different silhouettes.</p>
        <div className="asset-grid">{data.assets.tiles.map(t=><button key={t.id} className={'asset-card '+(selected===t.id?'selected':'')} aria-pressed={selected===t.id} onClick={()=>setSelected(t.id)}><div className="asset-preview"><img src={base+t.image} alt=""/></div><strong>{t.name}</strong><span>{t.heightClass} · 1 cell</span></button>)}</div>
        <div className="library-bottom"><span className="eyebrow">THE RECIPE</span><ol><li><span>01</span> Generate isolated art</li><li><span>02</span> Clean & preserve anchor</li><li><span>03</span> Normalize the footprint</li><li><span>04</span> Pack & preview overlap</li></ol><button className="text-button" onClick={()=>setAssetInfo(!assetInfo)}> {assetInfo?'Hide':'View'} processing details ↗</button>{assetInfo&&<p className="detail-text">Alpha floor 64 / 255 · 192 × 320 frames · trimmed atlas · 4 px padding · 2 px extrusion. Original PNGs and prompts are retained.</p>}</div>
      </aside>
      <main className="stage">
        <div className="stage-heading"><div><span className="eyebrow">OVERLAP PLAYGROUND</span><h2>{mode==='scene'?scene.name:mode==='cuts'?'Full sprite cuts':mode==='workflows'?'Workflow lab':mode==='characters'?'Character anchors':mode==='animations'?'Tiles & animation':'Packed atlas'}</h2></div>{!['workflows','characters','animations'].includes(mode)&&<label className="scene-picker"><span className="sr-only">Scene preset</span><select value={preset} onChange={e=>changePreset(e.target.value)}><option value="village">Village lane</option><option value="stress">Overlap stress test</option><option value="contact">Solid block contact</option></select></label>}</div>
        <div className="stage-toolbar"><div className="segmented">{[['scene','Scene'],['cuts','Sprite cuts'],['atlas','Atlas'],['workflows','Workflows'],['characters','Characters'],['animations','Animations']].map(([id,label])=><button key={id} aria-pressed={mode===id} className={mode===id?'active':''} onClick={()=>setMode(id)}>{label}</button>)}</div><div className="display-options">{['workflows','characters','animations'].includes(mode)?<label><input type="checkbox" checked={grid} onChange={e=>setGrid(e.target.checked)}/> {mode==='workflows'?'SVG outline':'Ground anchor'}</label>:<><label><input type="checkbox" checked={grid} onChange={e=>setGrid(e.target.checked)}/> Grid</label><label><input type="checkbox" checked={anchors} onChange={e=>setAnchors(e.target.checked)}/> Anchors</label><label><input type="checkbox" checked={footprints} onChange={e=>setFootprints(e.target.checked)}/> Collisions</label></>}</div></div>
        <div className="canvas-wrap" ref={containerRef} style={['workflows','characters','animations'].includes(mode)?{display:'none'}:undefined}><canvas ref={canvasRef} onPointerDown={interact} aria-label="Tile scene preview with square ground cells and sprites overlapping back rows"/></div>
        {mode==='workflows'?<WorkflowLab data={data} outline={grid}/>:mode==='characters'?<CharacterLab data={data} showAnchors={grid}/>:mode==='animations'?<AnimationLab data={data} showAnchors={grid}/>:<div className="stage-footer"><span>{scene.width} × {scene.height} cells <b>·</b> {scene.objects.length} objects <b>·</b> Ground Y sort</span><span>Orthographic 2D</span></div>}
      </main>
      <aside className="inspector"><div className="section-heading"><h2>Inspector</h2><span>↗</span></div><div className="inspector-art"><img src={base+tile.image} alt={tile.name}/><span className="pivot-dot"/></div><span className="eyebrow">{tile.material.toUpperCase()}</span><h3>{tile.name}</h3><p className="subtle">{tile.heightClass} silhouette · complete sprite</p><dl><div><dt>Ground cell</dt><dd>128 × 128</dd></div><div><dt>Sprite canvas</dt><dd>192 × 320</dd></div><div><dt>Ground anchor</dt><dd>{tile.anchor.map(Math.round).join(', ')}</dd></div><div><dt>Visible art</dt><dd>{tile.artRect[2]} × {tile.artRect[3]}</dd></div></dl>
        <div className="inspector-section"><label className="control-label" htmlFor="renderer">Sprite source</label><select id="renderer" value={renderer} onChange={e=>setRenderer(e.target.value)}><option value="atlas">Trimmed atlas</option><option value="sprites">Individual PNGs</option></select><label className="control-label" htmlFor="zoom">Scene scale <span>{zoom}%</span></label><input id="zoom" type="range" min="55" max="100" value={zoom} onChange={e=>setZoom(Number(e.target.value))}/></div>
        <div className="inspector-section"><span className="control-label">Cell tool</span><div className="segmented tool-buttons">{['inspect','place','erase'].map(t=><button key={t} aria-pressed={tool===t} className={tool===t?'active':''} onClick={()=>setTool(t)}>{t[0].toUpperCase()+t.slice(1)}</button>)}</div><p className="detail-text">{tool==='place'?'Choose a tile, then tap a ground cell.':tool==='erase'?'Tap a ground cell to remove its object.':'Tap a ground cell to inspect its object.'}</p><button className="secondary-button" disabled={!history.length} onClick={undo}>↶ Undo last edit</button></div>
        <div className="export-actions"><button className="primary-button" onClick={()=>canvasRef.current.toBlob(blob=>blob&&download(blob,'tile-foundry-scene.png'))}>Export preview PNG <span>↓</span></button><button className="secondary-button" onClick={()=>download(new Blob([JSON.stringify(scene,null,2)],{type:'application/json'}),'scene.json')}>Export scene JSON</button><label className="text-button import-button">Import scene JSON <input type="file" accept=".json,application/json" onChange={importScene}/></label></div>
      </aside>
    </div><div className="status-bar" role="status"><span>{mode==='workflows'?'Five trials · two generated materials · eight SVG variants':mode==='characters'?'Seven character trials · floor-derived ground anchors':mode==='animations'?'Lava floor · two dance trials · six frames each':status||'Four generated sprites · reusable ground · anchors reviewed in scene'}</span><span>{mode==='workflows'?'SVG → Reference / Masks → Compare':mode==='characters'?'Guide → Pose → Anchor → Extract':mode==='animations'?'Floor center → Anchor → Playback':'Source → Crop → Anchor → Atlas → Scene'}</span></div>
  </>;
}

createRoot(document.getElementById('root')).render(<App/>);
