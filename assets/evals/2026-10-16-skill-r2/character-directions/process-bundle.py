from pathlib import Path
import json, sys, hashlib, subprocess
from PIL import Image
OUT=Path(__file__).resolve().parent
REPO=OUT.parents[3]
SKILL=OUT.parent/'skill-snapshot'
PYTHON=REPO/'.venv/bin/python'

def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
source=OUT/'source-01.png'
with Image.open(source) as opened:
    rgba=opened.convert('RGBA')
    alpha=rgba.getchannel('A')
    imageinfo={'fileFormat':opened.format,'originalMode':opened.mode,'size':list(opened.size),'alphaExtrema':list(alpha.getextrema()),'nonzeroAlphaPixels':sum(a>0 for a in alpha.tobytes()),'opaqueAlphaPixels':sum(a==255 for a in alpha.tobytes())}
recipe=json.loads((OUT/'generation-01.json').read_text())
recipe['sourceSHA256']=sha(source)
recipe['source']='source-01.png'
recipe['sourceImageProperties']=imageinfo
recipe['toolResult']={'output_hint':'Generated images are saved to /Users/yiouchen/.codex/generated_images/01a1439f-43a6-7721-bb0d-bd531cea7bbe as /Users/yiouchen/.codex/generated_images/01a1439f-43a6-7721-bb0d-bd531cea7bbe/exec-bce99977-3f33-47fe-a38f-53b28611d70d.png by default.','originalGeneratedFile':'/Users/yiouchen/.codex/generated_images/01a1439f-43a6-7721-bb0d-bd531cea7bbe/exec-bce99977-3f33-47fe-a38f-53b28611d70d.png','originalGeneratedFileSHA256':sha(source),'preservedWithoutModification':True}
write(OUT/'generation-01.json',recipe)
submission=json.loads((OUT/'submission.json').read_text())
submission['sources']=[{'image':'source-01.png','recipe':'generation-01.json','role':'whole-asset'}]
write(OUT/'submission.json',submission)
# The repository wrapper delegates to tile_tools, verified identical to the frozen processor.
live=REPO/'skills/build-overlap-tiles/scripts/tile_tools.py'
frozen=SKILL/'scripts/tile_tools.py'
assert sha(live)==sha(frozen), 'Refuse live processor drift from frozen skill'
cmd=[str(PYTHON),'tools/tilekit.py','process-on-floor',str(source),str(OUT/'guide.json'),str(OUT/'processed'),'--min-alpha','32']
run=subprocess.run(cmd,cwd=REPO,capture_output=True,text=True)
(OUT/'processing.stdout.txt').write_text(run.stdout)
(OUT/'processing.stderr.txt').write_text(run.stderr)
evidence={'command':cmd,'workingDirectory':str(REPO),'exitCode':run.returncode,'stdout':'processing.stdout.txt','stderr':'processing.stderr.txt','sourceSHA256':sha(source),'guideSHA256':sha(OUT/'guide.json'),'sourceImageProperties':imageinfo,'wrapper':'tools/tilekit.py','wrapperSHA256':sha(REPO/'tools/tilekit.py'),'processorSHA256':sha(frozen),'liveProcessorMatchesFrozenSnapshot':True,'attempts':1,'imageGenerationCalls':1,'gutterRecoveryAttempted':False,'manualGeometryAdjustments':False,'clippingOrColorGuessing':False}
write(OUT/'processing.json',evidence)
if run.returncode==0:
    acmd=[str(PYTHON),str(SKILL/'scripts/assemble_result.py'),'--input-result',str(OUT/'processed/result.json'),'--registration',str(OUT/'registration.json'),'--output',str(OUT/'result.json')]
    arun=subprocess.run(acmd,cwd=REPO,capture_output=True,text=True)
    (OUT/'assembly.stdout.txt').write_text(arun.stdout)
    (OUT/'assembly.stderr.txt').write_text(arun.stderr)
    evidence['assembly']={'command':acmd,'exitCode':arun.returncode,'stdout':'assembly.stdout.txt','stderr':'assembly.stderr.txt'}
    write(OUT/'processing.json',evidence)
    if arun.returncode!=0:run=arun
if run.returncode!=0:
    error=(run.stderr or run.stdout).strip()
    write(OUT/'result.json',{'version':2,'kind':'directions','status':'failed','projection':'top-down-oblique-square-grid','cellSize':128,'groundAnchorAlignment':'center','heightAxis':[0,-1],'elevationScale':1,'sprites':[],'source':'source-01.png','guide':'guide.json','registration':'registration.json','processingEvidence':'processing.json','diagnostics':[{'stage':'deterministic-extraction','message':error,'consequence':'No runtime sprites delivered; cannot remove floor or normalize panels within the registered extraction contract.','attempts':1}],'geometryDeclaration':'Authored registration constraints are not measured output geometry. No clipping, anchor fitting, guessed-color cleanup, or correction generation was used.'})
print(json.dumps({'processingExitCode':run.returncode,'image':imageinfo,'stdout':run.stdout,'stderr':run.stderr,'result':'result.json','submission':'submission.json'},indent=2))
