from pathlib import Path
from PIL import Image
import json,hashlib,shutil,math
root=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry'); out=root/'assets/evals/2026-10-16-skill-r3/animated-waves'; skill=root/'assets/evals/2026-10-16-skill-r3/skill-snapshot'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record={}
r=json.loads((out/'result.json').read_text()); s=json.loads((out/'submission.json').read_text()); recipe=json.loads((out/'generation-01.json').read_text())
assert len(r['sprites'])==12
assert r['fps']==12
assert s['userPrompt']==(out/'request.txt').read_text().rstrip('\n')
assert s['guideSHA256']==sha(out/s['guide'])
assert recipe['sourceSHA256']==sha(out/'source-01.png')
assert recipe['transparentBackground'] is False
assert recipe['prompt']==json.loads((out/'tool-inputs-01.json').read_text())['prompt']
for ref in recipe['references']:assert recipe['referenceSHA256'][ref]==sha(out/ref)
for i,frame in enumerate(r['sprites']):
 assert frame['index']==i
 assert frame['size']==[192,320]
 assert frame['anchor']==[96,248]
 assert frame['footprint']==[128,128]
 assert frame['occupiedCells']==[[0,0]]
 assert frame['elevationPx']==32
 assert math.isclose(frame['durationMs'],1000/12,abs_tol=1e-10)
 assert Image.open(out/frame['image']).size==(192,320)
 assert (out/frame['image']).resolve().is_relative_to(out)
record={'scope':'File, hash, dimensional and timing integrity; no visual grade','assertionsCompleted':True,'frameCount':12,'generationCalls':1,'durationMsPerFrame':1000/12,'loopDurationMs':1000,'reviewStatus':'pending-independent-review'}
(out/'integrity-check.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'provenance/scripts').mkdir(exist_ok=True)
for file in ['waves_prepare.py','waves_finalize.py','waves_preview_fix.py','waves_integrity.py']:shutil.copyfile(Path('/tmp')/file,out/'provenance/scripts'/file)
processing={
 'python':str(root/'.venv/bin/python'),
 'commands':[
 {'tool':'frozen scripts/material_animation.py','args':['guide',str(out/'guide')],'exitCode':0},
 {'tool':'frozen scripts/svg_tools.py','args':['template',str(out/'template'),'--height','32','--palette','ocean','--plain','--terrain'],'exitCode':0},
 {'tool':'frozen scripts/material_animation.py','args':['compose',str(out/'template'),str(out/'source-01.png'),str(out/'guide.json'),str(out/'processed'),'--strength','.7'],'exitCode':0},
 {'tool':'frozen scripts/assemble_result.py','args':['--input-result',str(out/'processed/result.json'),'--registration',str(out/'registration.json'),'--output',str(out/'result.json')],'exitCode':0},
 {'tool':'tools/tilekit.py','args':['check-solid',str(out/'processed/frames/frame-00.png'),str(out/'coverage.json'),'--anchor','96','312','--pitch','128','128','--body-rect','32','152','160','312','--preview'],'exitCode':0}],
 'scriptSHA256':{name:sha(skill/'scripts'/name) for name in ['material_animation.py','svg_tools.py','assemble_result.py','tile_tools.py','review_playback.py']},
 'repoCompatibilityCheckerSHA256':sha(root/'tools/tilekit.py'),
 'customPreviewScripts':['provenance/scripts/waves_finalize.py','provenance/scripts/waves_preview_fix.py','capture-previews.mjs'],
 'notes':['No corrective generation, per-frame registration fitting, alpha trimming or source rewriting.','Preview canvas was enlarged after initial rendering; earlier preview PNGs are retained.','Image appearance and continuity require independent visual review.']}
(out/'processing-log.json').write_text(json.dumps(processing,indent=2)+'\n')
print(json.dumps(record))
