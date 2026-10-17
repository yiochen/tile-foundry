"""Publish Blender prototypes separately from frozen eval grades."""
from pathlib import Path
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'assets/blender/dancing-adventurer-v2'
EARLIER=ROOT/'assets/blender/dancing-adventurer-v1'
PUBLIC=ROOT/'public/assets'
REL=Path('blender/dancing-adventurer-v2')
OLDREL=Path('blender/dancing-adventurer-v1')


def main():
    files=['dancing-adventurer.blend','dancing-adventurer.glb','hero.png','grid-projection.png',
        'design-reference.png','reskin-reference.png','source-01.png','source-02.png',
        'reskin-prompt.txt','reskin-prompt-single.txt','generation-01.json','generation-02.json',
        'capture.json','guide.json','guide-single.json','checks.json','processing-01.json','processing-02.json']
    for bundle,rel in [(BUNDLE,REL),(EARLIER,OLDREL)]:
        destination=PUBLIC/rel;destination.mkdir(parents=True,exist_ok=True)
        for name in files:
            source=bundle/name
            if source.exists():shutil.copy2(source,destination/name)
        for directory in ['control','reskin-single','validation']:
            if (bundle/directory).exists():shutil.copytree(bundle/directory,destination/directory,dirs_exist_ok=True)
    def public(name):return (REL/name).as_posix()
    def old(name):return (OLDREL/name).as_posix()
    def frames(directory):
        result=json.loads((BUNDLE/directory/'result.json').read_text())
        return [{**s,'image':public(f'{directory}/{s["image"]}')} for s in result['sprites']]
    comparisons=[
        {'title':'Previous AI design target','image':public('design-reference.png'),
         'note':'The blue-tunic adventurer that guided the design. Original 192 × 320 frame; its body is larger than the authored nominal scale.'},
        {'title':'Corrected Blender character','image':public('hero.png'),
         'note':'35° ordinary orthographic camera. Outward elbows, aligned wrists, continuous weighted joints and fixed soles. No imagegen.'},
        {'title':'Square-grid camera comparison','image':public('grid-projection.png'),
         'note':'Same corrected model and world scale: 45° orthographic camera with √2 vertical projection stretch. Rounded forms elongate.'}]
    if (BUNDLE/'reskin-single/result.json').exists():
        comparisons.insert(2,{'title':'Style-only paint-over · corrected pose','image':public('reskin-single/frames/frame-00.png'),
            'note':'A fresh single-frame imagegen surface edit of the corrected rig. Uniform complete-frame sampling; no silhouette fitting.'})
    downloads=[(public('dancing-adventurer.blend'),'Editable corrected Blender scene'),
        (public('dancing-adventurer.glb'),'Corrected animated GLB'),
        (public('control/sheet.png'),'Corrected 3D spritesheet'),
        (public('control/result.json'),'Frame and anchor metadata'),
        (public('validation/rig-checks.json'),'Rig validation'),
        (public('checks.json'),'3D registration checks'),
        (old('source-01.png'),'Earlier AI atlas · before arm fix'),
        (old('generation-01.json'),'Earlier atlas recipe'),
        (old('source-02.png'),'Earlier single-frame paint-over · before arm fix')]
    if (BUNDLE/'source-01.png').exists():downloads.extend([
        (public('source-01.png'),'Current unchanged AI paint-over'),
        (public('generation-01.json'),'Current paint-over recipe')])
    data={'bones':22,'model':public('dancing-adventurer.glb'),'comparisons':comparisons,
        'controlFrames':frames('control'),'reskinFrames':[],
        'reskinSource':old('source-01.png'),
        'reskinNote':'The corrected pose’s single-frame paint-over is compared above. An earlier 24-pose atlas trial, made before the arm repair, improved the painted appearance but enlarged characters and shifted rows. Opaque art crossed panel gutters, so its animation export was rejected. It is retained below as a failed layout experiment.',
        'processingNote':'One uniform whole-canvas scale and a global alpha threshold of 32/255. No silhouette mask, color key, per-pose fitting or clipping. The earlier atlas was rejected for opaque art outside authored panels. Single-frame edits are sampled as whole registered frames; successful extraction does not certify geometry.',
        'prompt':(EARLIER/'reskin-prompt.txt').read_text(),
        'singlePrompt':(BUNDLE/'reskin-prompt-single.txt').read_text(),
        'validationImages':[
            {'image':old('validation/mcp-before-angles.png'),'label':'Before repair · front, side and three-quarter'},
            {'image':public('validation/mcp-after-angles.png'),'label':'After repair · same three views'},
            {'image':public('validation/mcp-animation-frames.png'),'label':'After repair · animation frames 1, 5, 9, 13, 17, 21'}],
        'downloads':[{'path':path,'label':label} for path,label in downloads]}
    (PUBLIC/'blender-adventurer.json').write_text(json.dumps(data,indent=2)+'\n')
    print('Published corrected Blender adventurer: 24 frames at 12 fps; MCP validation and earlier AI layout failure retained.')


if __name__=='__main__':main()
