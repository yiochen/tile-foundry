import React, {useEffect, useRef, useState} from 'react';

const base = `${import.meta.env.BASE_URL}assets/`;

function AnchoredPreview({frame, images, ground, theme, showAnchors}) {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current, ctx = canvas.getContext('2d');
    canvas.width = 256; canvas.height = 384;
    ctx.fillStyle = theme === 'dark' ? '#242935' : '#f1f2e9';
    ctx.fillRect(0, 0, 256, 384);
    // A stored sprite anchor is placed at the center of this 128 px ground cell.
    const [x, y] = [128, 264];
    if (ground) ctx.drawImage(images[ground], x - 64, y - 64, 128, 128);
    else {
      ctx.fillStyle = theme === 'dark' ? '#3b4250' : '#d9e0cf';
      ctx.fillRect(x - 64, y - 64, 128, 128);
    }
    ctx.drawImage(images[frame.image], x - frame.anchor[0], y - frame.anchor[1]);
    if (showAnchors) {
      ctx.strokeStyle = '#ff4b97'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x - 7, y); ctx.lineTo(x + 7, y);
      ctx.moveTo(x, y - 7); ctx.lineTo(x, y + 7); ctx.stroke();
      ctx.fillStyle = '#ff4b97'; ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();
    }
    canvas.dataset.ready = 'true'; canvas.dataset.frame = frame.id;
    canvas.dataset.anchor = frame.anchor.join(',');
  }, [frame, images, ground, theme, showAnchors]);
  return <canvas ref={ref} className="animation-preview" aria-label={`Dancing player on ${theme} ground`}/>;
}

export default function AnimationLab({data, showAnchors}) {
  const gallery = data.gallery;
  const [selected, setSelected] = useState('dancing-player-retry');
  const [playing, setPlaying] = useState(true), [index, setIndex] = useState(0);
  const [speed, setSpeed] = useState(1), [ground, setGround] = useState('plain');
  const animation = gallery.animations.find(a => a.id === selected);
  const frame = animation.frames[index];
  useEffect(() => {
    if (!playing) return;
    const timer = setTimeout(() => setIndex(i => (i + 1) % animation.frames.length), frame.durationMs / speed);
    return () => clearTimeout(timer);
  }, [playing, index, animation, speed, frame.durationMs]);
  return <div className="animation-lab">
    <div className="character-intro">Play the generated dance, step through its six poses, and compare the cutout on light and dark backgrounds. Each frame uses the saved floor-center anchor. The green calibration floor has been removed.</div>
    <section className="animation-card">
      <div className="animation-controls">
        <label>Animation<select aria-label="Animation trial" value={selected} onChange={e => {setSelected(e.target.value); setIndex(0);}}>{gallery.animations.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
        <button className="secondary-button" aria-label={playing ? 'Pause animation' : 'Play animation'} onClick={() => setPlaying(p => !p)}>{playing ? 'Pause' : 'Play'}</button>
        <label>Speed<select aria-label="Animation speed" value={speed} onChange={e => setSpeed(Number(e.target.value))}>{[.5, 1, 2].map(s => <option key={s} value={s}>{s}×</option>)}</select></label>
        <label>Floor<select aria-label="Animation floor" value={ground} onChange={e => setGround(e.target.value)}><option value="plain">Plain</option><option value="lava">Lava</option></select></label>
      </div>
      <div className="animation-stages">{['light', 'dark'].map(theme => <figure key={theme}><AnchoredPreview frame={frame} images={data.images} ground={ground === 'lava' ? gallery.floor.image : null} theme={theme} showAnchors={showAnchors}/><figcaption>{theme === 'light' ? 'Light' : 'Dark'} background · frame <span data-animation-frame>{index + 1}</span> / {animation.frames.length}</figcaption></figure>)}</div>
      <label className="animation-scrubber">Frame {index + 1}<input aria-label="Animation frame" type="range" min="0" max={animation.frames.length - 1} value={index} onChange={e => {setPlaying(false); setIndex(Number(e.target.value));}}/></label>
      <div className="animation-frames">{animation.frames.map((f, i) => <button key={f.id} aria-label={`Show animation frame ${i + 1}`} aria-pressed={i === index} onClick={() => {setPlaying(false); setIndex(i);}}><img src={base + f.image} alt={`Dance pose ${i + 1}`}/><span>{i + 1}</span></button>)}</div>
      <p className="workflow-note">{animation.note} Frame: {frame.size.join(' × ')} px. Ground cell: {animation.cellSize} × {animation.cellSize} px. Anchor: {frame.anchor.join(', ')}. Default playback: {animation.fps} fps.</p>
      <div className="animation-downloads"><a href={base + animation.sheet} download>Download spritesheet</a><a href={base + animation.metadata} download>Frame metadata</a><a href={base + animation.source} target="_blank" rel="noreferrer">Original AI output</a><a href={base + animation.recipe} target="_blank" rel="noreferrer">Generation prompt</a><a href={base + animation.guide} target="_blank" rel="noreferrer">SVG guide render</a></div>
    </section>
    <section className="animation-card lava-card"><div><span className="eyebrow">GENERATED FLOOR</span><h3>Lava · touching neighbors</h3><p className="workflow-note">One 128 × 128 tile repeated on a 3 × 3 grid. Slight seam differences remain visible in the molten channels.</p><a href={base + gallery.floor.image} download>Download lava tile</a></div><div className="lava-repeat" aria-label="Nine touching lava tiles">{Array.from({length: 9}, (_, i) => <img key={i} src={base + gallery.floor.image} alt=""/>)}</div></section>
  </div>;
}
