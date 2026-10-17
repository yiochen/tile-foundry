import json, sys, hashlib
from pathlib import Path
from PIL import Image, ImageDraw
root=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry/assets/evals/2026-10-17-3d-reskin-r1/character-directions')
skill=root.parent/'skill-snapshot'
sys.dont_write_bytecode=True
sys.path.insert(0,str(skill/'scripts'))
from prepare_review import placement_preview
previews=root/'previews'
previews.mkdir(exist_ok=True)
result=json.loads((root/'result.json').read_text())
control=json.loads((root/'direct3d/result.json').read_text())
for stage, manifest, base in [('ai-reskin',result,root),('direct3d',control,root/'direct3d')]:
    for dark in [False,True]:
        tiles=[]
        theme='dark' if dark else 'light'
        for i,sprite in enumerate(manifest['sprites']):
            image=Image.open(base/sprite['image']).convert('RGBA')
            out=previews/f'{stage}-{i:02}-{theme}.png'
            placement_preview(image,sprite,out,dark)
            tiles.append(Image.open(out).convert('RGBA'))
        tw,th=tiles[0].size
        contact=Image.new('RGBA',(tw*4,(th+24)*2),'#18222e' if dark else '#f4f6ef')
        draw=ImageDraw.Draw(contact)
        for i,tile in enumerate(tiles):
            x=(i%4)*tw;y=(i//4)*(th+24)
            contact.alpha_composite(tile,(x,y+24))
            draw.text((x+24,y+5),manifest['sprites'][i].get('direction',str(i)),fill='#e6edf3' if dark else '#17251f')
        contact.save(previews/f'{stage}-{theme}-native.png')
        contact.resize((contact.width*2,contact.height*2),Image.Resampling.NEAREST).save(previews/f'{stage}-{theme}-2x.png')
parts=['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Eight directions capture and reskin</title><style>body{font:15px system-ui;background:#e9eee8;color:#18251d;margin:24px}main{max-width:1100px;margin:auto}h1{font-size:24px}h2{font-size:20px;margin-top:32px}.grid{display:grid;grid-template-columns:repeat(4,240px);gap:12px}.panel{background:#f4f6ef;border:1px solid #bcc9bc;border-radius:6px;overflow:hidden}.panel strong{display:block;padding:10px 16px}.panel img{display:block;width:240px;height:368px}.note{max-width:750px;line-height:1.5}a{color:#1657a0}@media(max-width:1050px){.grid{grid-template-columns:repeat(2,240px)}}@media(max-width:550px){body{margin:16px}.grid{grid-template-columns:240px;justify-content:center}}</style></head><body><main><h1>Eight neutral directions</h1><p class="note">Fixed 192×320 runtime frame, 128px square ground cell, projected root (96,248). Crosshairs show the authored root. These previews show the source stages without fitting feet or silhouette bounds.</p>']
for stage,label in [('direct3d','Direct 3D control'),('ai-reskin','AI reskin candidate')]:
    parts.append(f'<h2>{label}</h2><p><a href="{stage}-light-2x.png">2× light</a> · <a href="{stage}-dark-2x.png">2× dark</a></p><div class="grid">')
    for i,direction in enumerate(['N','NE','E','SE','S','SW','W','NW']):
        parts.append(f'<article class="panel"><strong>{direction}</strong><img src="{stage}-{i:02}-light.png" alt="{label} {direction}"></article>')
    parts.append('</div>')
parts.append('<h2>Retained source</h2><p><a href="../source-01.png">Untouched generated PNG</a> · <a href="../render/sheet.png">Floor-free 3D edit target</a> · <a href="../render/guide.png">Separate calibration capture</a></p></main></body></html>')
(previews/'index.html').write_text(''.join(parts))
packet={'caseId':'character-directions','request':(root/'request.txt').read_text().rstrip('\n'),'submission':'../submission.json','result':'../result.json','source':'../source-01.png','guide':'../render/guide.json','control':'../direct3d/result.json','native':['ai-reskin-light-native.png','ai-reskin-dark-native.png','direct3d-light-native.png','direct3d-dark-native.png'],'twiceNative':['ai-reskin-light-2x.png','ai-reskin-dark-2x.png','direct3d-light-2x.png','direct3d-dark-2x.png'],'spriteSHA256':{s['id']:hashlib.sha256((root/s['image']).read_bytes()).hexdigest() for s in result['sprites']},'gradingPerformed':False}
(previews/'packet.json').write_text(json.dumps(packet,indent=2)+'\n')
print(json.dumps({'previews':str(previews),'sprites':len(result['sprites'])}))