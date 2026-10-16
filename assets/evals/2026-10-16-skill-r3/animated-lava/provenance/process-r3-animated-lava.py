from pathlib import Path
import hashlib,json,shutil,subprocess,sys
from PIL import Image
root=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry/assets/evals/2026-10-16-skill-r3/animated-lava')
skill=root.parent/'skill-snapshot'
py='/Users/yiouchen/.codex/worktrees/1834/tile-foundry/.venv/bin/python'
original=Path('/Users/yiouchen/.codex/generated_images/01a143a5-be11-7ea2-846b-dac29ab3d008/exec-8ee586c4-fa5f-43bd-aa58-def85eee749e.png')
def write(name,obj):(root/name).write_text(json.dumps(obj,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=root/'source-01.png'
shutil.copy2(original,source)
recipe=json.loads((root/'generation-01.json').read_text())
recipe.update(sourceSHA256=sha(source),status='generated',originalToolOutputPath=str(original),actualToolInputs='tool-inputs-01.json',generationCallCount=1)
write('generation-01.json',recipe)
write('tool-output-01.json',{'tool':'image_gen.imagegen','sourceOriginalPath':str(original),'sourceCopiedPath':'source-01.png','sourceSHA256':sha(source),'imageUrlReturned':True,'outputHint':'Generated images are saved to /Users/yiouchen/.codex/generated_images/01a143a5-be11-7ea2-846b-dac29ab3d008 as /Users/yiouchen/.codex/generated_images/01a143a5-be11-7ea2-846b-dac29ab3d008/exec-8ee586c4-fa5f-43bd-aa58-def85eee749e.png by default.\nIf you need to use a generated image at another path, copy it and leave the original in place unless the user explicitly asks you to delete it.\nThe generated image is already displayed to the user. There is no need to render it in the final response as a Markdown image or file link.'})
commands=[
 [py,str(skill/'scripts/material_animation.py'),'compose',str(root/'template'),str(source),str(root/'guide.json'),str(root/'processed'),'--strength','.7'],
 [py,str(skill/'scripts/assemble_result.py'),'--input-result',str(root/'processed/result.json'),'--registration',str(root/'registration.json'),'--output',str(root/'result.json')]]
logs=[]
for args in commands:
 r=subprocess.run(args,capture_output=True,text=True)
 logs.append({'argv':args,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if r.returncode:break
write('processing-commands.json',logs)
write('submission.json',{'caseId':'animated-lava','outputDirectory':str(root),'userPrompt':(root/'request.txt').read_text().removesuffix('\n'),'sources':[{'image':'source-01.png','recipe':'generation-01.json','role':'appearance-material'}],'guide':'guide.json','guideSHA256':sha(root/'guide.json'),'result':'result.json'})
if logs[-1]['exitCode']:
 write('result.json',{'version':2,'status':'blocked','kind':'animation','reason':logs[-1]['stderr'],'projection':'top-down-oblique-square-grid','cellSize':128,'groundAnchorAlignment':'center','fps':12,'sprites':[]})
print(json.dumps(logs,indent=2))
with Image.open(source) as im:print(json.dumps({'originalSize':list(im.size),'originalMode':im.mode,'alphaExtrema':im.convert('RGBA').getchannel('A').getextrema(),'originalUnchanged':sha(source)==sha(original)}))
