import json,hashlib
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
submission=json.loads((root/'submission.json').read_text())
result=json.loads((root/'result.json').read_text())
guide=json.loads((root/'render/guide.json').read_text())
recipe=json.loads((root/'generation-01.json').read_text())
receipt=json.loads((root/'execution-receipt.json').read_text())
processed=json.loads((root/'processed/result.json').read_text())
control=json.loads((root/'direct3d/result.json').read_text())
packet=json.loads((root/'previews/packet.json').read_text())
directions=['N','NE','E','SE','S','SW','W','NW']
assert result['version']==2 and result['kind']=='directions'
assert [s['direction'] for s in result['sprites']]==directions
assert len(result['sprites'])==8
assert sha(root/'source-01.png')==recipe['sourceSHA256']
assert sha(root/'references/pose-sheet.png')==recipe['referenceSHA256']['references/pose-sheet.png']
assert sha(root/'render/sheet.png')==sha(root/'references/pose-sheet.png')
assert sha(root/'render/guide.json')==submission['guideSHA256']==receipt['guideSHA256']
assert receipt['freshBuiltinImageCallsMade']==1
assert sha(root/'tool-input-01.json')==receipt['predeclaredToolInputSHA256']
assert recipe['transparentBackground'] is True
assert processed['cleanup']['minAlpha']==32
assert control['cleanup']['minAlpha']==0 and control['cleanup']['removedAlphaMass']==0
assert not processed['cleanup']['rendererMaskApplied'] and not processed['cleanup']['colorKeyApplied']
assert not processed['normalization']['perPoseFitting']
assert guide['anchor']==[96,248] and guide['frame']==[192,320]
images=[]
for sprite in result['sprites']:
    path=(root/sprite['image']).resolve()
    assert path.is_relative_to(root)
    assert sprite['anchor']==[96,248] and sprite['size']==[192,320] and sprite['footprint']==[128,128]
    assert sprite['registration']['method']=='authored-3d-projection'
    assert sha(path)==packet['spriteSHA256'][sprite['id']]
    with Image.open(path) as im:
        assert im.size==(192,320) and im.mode=='RGBA'
        a=im.getchannel('A')
        assert a.getbbox()
        assert all(a.crop(rect).getextrema()[1]==0 for rect in [(0,0,192,1),(0,319,192,320),(0,0,1,320),(191,0,192,320)])
    images.append({'image':sprite['image'],'sha256':sha(path),'direction':sprite['direction']})
for relative in ['render/scene.json','render/scene/rig.json','render/scene/poses.json','render/capture.json','render/scene/render_3d_scene.js','render/mask-sheet.png','render/depth-sheet.png','render/guide.png','previews/screenshot-desktop.png','previews/screenshot-mobile.png']:
    assert (root/relative).is_file()
record={'type':'delivery-integrity','status':'completed','sprites':images,'sourceSHA256':sha(root/'source-01.png'),'guideSHA256':sha(root/'render/guide.json'),'sourceSize':processed['sourceSize'],'frame':[192,320],'anchor':[96,248],'directionOrder':directions,'minAlpha':32,'removedAlphaMass':processed['cleanup']['removedAlphaMass'],'direct3DRemovedAlphaMass':0,'exactBuiltinCalls':1,'visualGradingPerformed':False,'geometryScope':'Authored registration transfer only; this integrity check does not assess AI geometry, proportions or contact.'}
(root/'integrity-check.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':'completed','sprites':len(images),'order':directions,'minAlpha':32,'removedAlphaMass':record['removedAlphaMass']}))
