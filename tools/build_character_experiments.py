#!/usr/bin/env python3
"""Rebuild character anchor/removal experiments from untouched saved AI outputs."""
import json
from pathlib import Path
from character_guides import main as guides, ANCHOR, FRAME
from tilekit import (load_rgba, clean_alpha, floor_anchor, normalize, composite_reference,
                     remove_detached_markers, subtract_authored_floor, remove_floor_chroma, write_json, export_tiled)

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public/assets/characters'


def main():
    guides()
    reference=load_rgba(ROOT/'assets/source/character-raster-reference.png')
    character,meta=normalize(reference,anchor_out=ANCHOR,art_width=72)
    character.save(ROOT/'assets/character-guides/raster-character.png')
    write_json(ROOT/'assets/character-guides/raster-character.json',meta)
    flat,large=composite_reference(load_rgba(ROOT/'assets/character-guides/floor-only.png'),character)
    flat.save(ROOT/'assets/character-guides/raster.png')
    large.save(ROOT/'assets/character-guides/raster-4x.png')
    config=json.loads((ROOT/'assets/character-experiment-config.json').read_text())
    PUBLIC.mkdir(parents=True,exist_ok=True)
    entries=[]
    for trial in config['trials']:
        image,cleanup=clean_alpha(load_rgba(ROOT/trial['source']),64)
        floor=floor_anchor(image,trial['mode'])
        scale=floor['nominalSpan']/(floor['rect'][2]-floor['rect'][0])
        normalized,meta=normalize(image,frame=FRAME,anchor_out=ANCHOR,anchor_in=floor['anchor'],scale=scale)
        normalized.save(PUBLIC/f"{trial['id']}-with-guide.png")
        guide=load_rgba(ROOT/f"assets/character-guides/{trial['guide']}.png")
        guide.save(PUBLIC/f"{trial['id']}-guide.png")
        if trial['mode']=='corners':
            # Isolate before scaling: resampling must not connect detached components.
            extracted,removal=remove_detached_markers(image,floor)
            result,extracted_meta=normalize(extracted,frame=FRAME,anchor_out=ANCHOR,
                anchor_in=floor['anchor'],scale=scale)
            usable=True
            removal.update({'normalization':extracted_meta,'productionSafe':True})
        else:
            result,removal=subtract_authored_floor(normalized,load_rgba(ROOT/'assets/character-guides/floor-only.png'))
            usable=False
        chroma=None
        if trial['mode']=='solid':
            key_config=config['floorChromaKey']
            # Normalize the whole composition first. Removing floor pixels cannot
            # change art scale, position, frame, or the already inferred anchor.
            key_floor={**floor_anchor(normalized),'anchor':list(ANCHOR)}
            keyed,chroma=remove_floor_chroma(normalized,key_floor,tuple(key_config['keyRGB']),
                key_config['hueToleranceDegrees'],key_config['hueFeatherDegrees'],
                key_config['minSaturation'],key_config['saturationFeather'],
                key_config['removeCornerRemnants'])
            keyed.save(PUBLIC/f"{trial['id']}-keyed.png")
        result.save(PUBLIC/f"{trial['id']}-removal.png")
        review=trial.get('footReview')
        feet=None
        if review:
            midpoint=[sum(p[i] for p in review['sourceSoles'])/2 for i in (0,1)]
            feet={'midpoint':[round(ANCHOR[i]+(midpoint[i]-floor['anchor'][i])*meta['scale'][i],2) for i in (0,1)],
                  'uncertaintyPixels':round(max(meta['scale'])*review['uncertaintySourcePixels'],2),
                  'purpose':'Independent sole-midpoint review for evaluation only; not a processing input'}
        expected=[96,248] if trial['pose']=='standing' else [98,214]
        error=[round(feet['midpoint'][i]-expected[i],2) for i in (0,1)] if feet else None
        entry={**trial,'size':list(FRAME),'anchor':list(ANCHOR),'floor':floor,
            'withGuide':f"characters/{trial['id']}-with-guide.png",'guideImage':f"characters/{trial['id']}-guide.png",
            'removalImage':f"characters/{trial['id']}-removal.png",'usableExtraction':usable,
            'keyedImage':f"characters/{trial['id']}-keyed.png" if chroma else None,'chromaRemoval':chroma,
            'processing':{'cleanup':cleanup,'normalization':meta},'removal':removal,
            'footMeasurement':feet,
            'metrics':{'guideFootMidpoint':expected,'expectedFootMidpoint':expected,'footDelta':error,'floorAspect':floor['aspect'],
                'footDeltaMeaning':'Visible boot silhouette relative to guide, not ground-anchor error; shoe length can extend below cell center',
                'observedElevation':round(ANCHOR[1]-feet['midpoint'][1],2) if feet else None,
                'anchorMode':'Inferred floor center; never fitted to reviewed feet'}}
        entries.append(entry)
    results={'version':2,'frame':list(FRAME),'cellSize':128,'anchor':list(ANCHOR),'trials':entries,
        'scope':'Seven one-shot trials. Boot reviews describe visible extent, not ground-anchor error. Five explicit green-key cutouts preserve floor-derived normalization; mixed edges are approximate. Exact subtraction is retained as a diagnostic; detached corners preserve selected pixels.'}
    write_json(ROOT/'public/assets/characters.json',results)
    write_json(ROOT/'docs/character-comparison.json',results)
    # Export explicit-key cutouts too, with approximate extraction recorded.
    cutouts=[e for e in entries if e['usableExtraction'] or e['keyedImage']]
    if cutouts:
        tiles={'cellSize':128,'tiles':[{'id':e['id'],'image':e['keyedImage'] or e['removalImage'],
            'size':e['size'],'anchor':e['anchor'],
            'extraction':'approximate-chroma-key' if e['keyedImage'] else 'detached-alpha'} for e in cutouts]}
        scene={'width':3,'height':2,'roadColumns':[],'groundAnchorAlignment':'center','objects':[{'tileId':'character-jump-solid','col':1,'row':1}]}
        write_json(ROOT/'public/assets/characters-tiles.json',tiles)
        write_json(ROOT/'public/assets/characters-scene.json',scene)
        export_tiled(scene,tiles,ROOT/'public/assets/characters.tmj')
    print(json.dumps([{k:e[k] for k in ('id','metrics','usableExtraction')} for e in entries],indent=2))


if __name__=='__main__':
    main()
