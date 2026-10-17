#!/usr/bin/env python3
"""Deterministic placement previews; uses tilekit's portable image primitives."""
import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

HERE = Path(__file__).resolve().parent
if not (HERE/'tile_tools.py').is_file():
    sys.path.insert(0, str(HERE.parent/'skills/build-overlap-tiles/scripts'))
from tile_tools import load_rgba, render_floor_repeat, write_json


def backgrounds(image, output, stem):
    for name,color in [('light','#edf0e9'),('dark','#19232e')]:
        view=Image.new('RGBA',image.size,color)
        view.alpha_composite(image)
        view.save(output/f'{stem}-{name}-native.png')
        view.resize((image.width*2,image.height*2),Image.Resampling.NEAREST).save(output/f'{stem}-{name}-2x.png')


def grid_view(image,anchor,footprint):
    # Common world scale and stored anchor; canvas grows, art is never fitted.
    w=max(768,image.width+384);h=max(768,image.height+256)
    out=Image.new('RGBA',(w,h),'#dce5d6');d=ImageDraw.Draw(out)
    root=(w//2,h//2+128)
    for x in range(root[0]%128,w,128):d.line((x,0,x,h),fill='#a4b7a1')
    for y in range(root[1]%128,h,128):d.line((0,y,w,y),fill='#a4b7a1')
    fw,fh=footprint
    d.rectangle((root[0]-fw//2,root[1]-fh//2,root[0]+fw//2,root[1]+fh//2),outline='#a16782',width=2)
    out.alpha_composite(image,(root[0]-anchor[0],root[1]-anchor[1]))
    d.line((root[0]-7,root[1],root[0]+7,root[1]),fill='#bc316e')
    d.line((root[0],root[1]-7,root[0],root[1]+7),fill='#bc316e')
    return out


def make_previews(root):
    root=Path(root).resolve();result=json.loads((root/'result.json').read_text());output=root/'previews';output.mkdir(exist_ok=True)
    for sprite in result['sprites']:
        im=load_rgba(root/sprite['image']);backgrounds(im,output,sprite['id'])
        grid_view(im,sprite['anchor'],sprite['footprint']).save(output/f"{sprite['id']}-stored-anchor-grid.png")
    whole=load_rgba(root/'render/whole.png')
    if result['kind']=='floor':
        for n in [3,5]:
            im=render_floor_repeat(whole,n);im.save(output/f'repeat-{n}-native.png');im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST).save(output/f'repeat-{n}-2x.png')
    if result['sprites'][0]['id']=='lava-tile':
        # Each full object is placed at 128px pitch, sorted rear-to-front.
        im=Image.new('RGBA',(512,544),'#e3e9df')
        for y in range(3):
            for x in range(3):im.alpha_composite(whole,(64+x*128-32,64+y*128-152))
        im.save(output/'repeat-3-placed.png')
        im.resize((1024,1088),Image.Resampling.NEAREST).save(output/'repeat-3-placed-2x.png')
    if result['kind']=='layered':
        im=Image.alpha_composite(load_rgba(root/'sprites/stool.png'),load_rgba(root/'sprites/character.png'))
        im.save(output/'recomposed-layers.png');backgrounds(im,output,'recomposed-layers')
        backgrounds(whole,output,'shared-3d-scene')
        diff=ImageChops.difference(im,whole)
        write_json(output/'layer-comparison.json',{'recipe':'Alpha-composite complete stool then character at their common stored ground anchor; no elevation transform is added.',
            'sharedSceneDifferencePixelsAbove8':sum(max(v)>8 for v in diff.get_flattened_data()),
            'note':'Two independently antialiased layers can differ from simultaneous rasterization at shared edges; complete captures and both recompositions retained.'})
    if result.get('depthPieces'):
        rear=load_rgba(root/'render/arch-rear.png');front=load_rgba(root/'render/arch-front.png')
        backgrounds(Image.alpha_composite(rear,front),output,'depth-pieces-recomposed')
        for name in ['behind','center','foreground']:
            actor=load_rgba(root/f'render/actor-{name}.png')
            # Explicit world-depth order follows the actor location.
            order=[actor,rear,front] if name=='behind' else [rear,front,actor] if name=='foreground' else [rear,actor,front]
            composite=Image.new('RGBA',whole.size)
            for layer in order:composite.alpha_composite(layer)
            backgrounds(composite,output,'depth-pieces-actor-'+name)
            backgrounds(load_rgba(root/f'render/passage-{name}.png'),output,'shared-scene-passage-'+name)
    write_json(output/'preview-recipe.json',{'tool':'3d_controls_static_previews.py using tilekit tile_tools primitives and Pillow',
        'spritesFitted':False,'nativePixelsPerCell':128,'twiceScale':'nearest neighbor for inspection only',
        'changesToSources':False,'groundPlacement':'worldGround minus stored local anchor','imageGenerationCalls':0})
    return {'output':str(output),'images':len(list(output.glob('*.png')))}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();print(json.dumps(make_previews(args.output)))
