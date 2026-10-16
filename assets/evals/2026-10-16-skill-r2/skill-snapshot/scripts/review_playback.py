"""Self-contained, ungraded playback evidence from complete registered frames."""
import base64
import json
from pathlib import Path


def write_playback(sprites, image_paths, output, terrain=False):
    """Embed the supplied PNGs unchanged; display at stored roots, never alpha-fit."""
    frames=[]
    for sprite,path in zip(sprites,image_paths):
        frames.append({k:sprite[k] for k in ('size','anchor','footprint')})
        frames[-1]['image']='data:image/png;base64,'+base64.b64encode(Path(path).read_bytes()).decode()
    if len(frames)<2:return None
    document='''<!doctype html><meta charset="utf-8"><title>Registered animation review</title>
<style>body{font:16px system-ui;background:#eee;color:#222;margin:24px}canvas{display:block;margin-top:16px;max-width:100%}input{width:280px}label{margin:12px}</style>
<button id="play">Pause</button><label>Frame <input id="seek" type="range" min="0" step="1" value="0"></label><output id="frame"></output>
<label><input id="dark" type="checkbox" style="width:auto">Dark</label>
<label><input id="offset" type="checkbox" style="width:auto">Offset neighbor phases</label>
<label>Scale <select id="scale"><option>1</option><option>2</option></select></label>
<p>Complete frames at their stored ground root. 12 fps, row-major. Magenta crosses mark roots.</p><canvas id="view"></canvas>
<script>
const frames=__FRAMES__,terrain=__TERRAIN__;
const canvas=document.getElementById('view'),ctx=canvas.getContext('2d'),seek=document.getElementById('seek');
const count=terrain?3:1,margin=24,px=frames[0].footprint[0],py=frames[0].footprint[1];
const left=Math.min(...frames.map(f=>-f.anchor[0])),top=Math.min(...frames.map(f=>-f.anchor[1]));
const width=Math.max(...frames.map(f=>f.size[0]-f.anchor[0]))-left+(count-1)*px+margin*2;
const height=Math.max(...frames.map(f=>f.size[1]-f.anchor[1]))-top+(count-1)*py+margin*2;
let images=[],index=0,playing=true,epoch=performance.now();seek.max=frames.length-1;
function draw(){const scale=Number(document.getElementById('scale').value);canvas.width=Math.ceil(width*scale);canvas.height=Math.ceil(height*scale);ctx.scale(scale,scale);
ctx.fillStyle=document.getElementById('dark').checked?'#18222e':'#f4f6ef';ctx.fillRect(0,0,width,height);
for(let y=0;y<count;y++)for(let x=0;x<count;x++){let rootX=margin-left+x*px,rootY=margin-top+y*py;ctx.strokeStyle='#789080';ctx.strokeRect(rootX-px/2,rootY-py/2,px,py);}
for(let y=0;y<count;y++)for(let x=0;x<count;x++){const phase=(index+(document.getElementById('offset').checked?x+y*count:0))%frames.length,f=frames[phase];ctx.drawImage(images[phase],margin-left+x*px-f.anchor[0],margin-top+y*py-f.anchor[1]);}
ctx.strokeStyle='#b72e74';for(let y=0;y<count;y++)for(let x=0;x<count;x++){const X=margin-left+x*px,Y=margin-top+y*py;ctx.beginPath();ctx.moveTo(X-5,Y);ctx.lineTo(X+5,Y);ctx.moveTo(X,Y-5);ctx.lineTo(X,Y+5);ctx.stroke();}
seek.value=index;document.getElementById('frame').value=`${index+1}/${frames.length} · 12 fps`;canvas.dataset.frame=index;}
document.getElementById('play').onclick=()=>{playing=!playing;epoch=performance.now()-index*1000/12;document.getElementById('play').textContent=playing?'Pause':'Play';};
seek.oninput=()=>{playing=false;document.getElementById('play').textContent='Play';index=Number(seek.value);draw();};
for(const id of ['dark','offset','scale'])document.getElementById(id).onchange=draw;
Promise.all(frames.map(f=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=reject;im.src=f.image;}))).then(value=>{images=value;draw();requestAnimationFrame(function tick(now){if(playing){const next=Math.floor((now-epoch)*12/1000)%frames.length;if(next!==index){index=next;draw();}}requestAnimationFrame(tick);});});
</script>'''
    document=document.replace('__FRAMES__',json.dumps(frames)).replace('__TERRAIN__',json.dumps(terrain))
    Path(output).write_text(document)
    return Path(output)
