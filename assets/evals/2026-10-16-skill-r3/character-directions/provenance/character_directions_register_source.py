import json,hashlib,shutil
from pathlib import Path
from PIL import Image
OUT=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry/assets/evals/2026-10-16-skill-r3/character-directions')
src=Path('/Users/yiouchen/.codex/generated_images/01a143ab-53da-7fb0-935c-f9ff5903fc68/exec-7c5a7d08-a9e1-4be7-ab58-cffefcf2c3a0.png')
shutil.copy2(src,OUT/'source-01.png')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=json.loads((OUT/'tool-input-01.json').read_text())
recipe={'prompt':inputs['prompt'],'tool':'image_gen.imagegen','transparentBackground':inputs['transparent_background'],'references':['references/guide.png'],'referenceSHA256':{'references/guide.png':sha(OUT/'references/guide.png')},'referenceRoles':{'references/guide.png':'layout edit target'},'sourceSHA256':sha(OUT/'source-01.png'),'toolInputs':'tool-input-01.json','toolOutputOriginalPath':str(src),'generationAttempt':1,'correctionAttempts':0}
(OUT/'generation-01.json').write_text(json.dumps(recipe,indent=2)+'\n')
submission={'caseId':'character-directions','outputDirectory':str(OUT),'userPrompt':(OUT/'request.txt').read_text().rstrip('\n'),'sources':[{'image':'source-01.png','recipe':'generation-01.json'}],'guide':'guide.json','guideSHA256':sha(OUT/'guide.json'),'result':'result.json'}
(OUT/'submission.json').write_text(json.dumps(submission,indent=2)+'\n')
im=Image.open(OUT/'source-01.png')
print(json.dumps({'size':im.size,'mode':im.mode,'sourceSHA256':sha(OUT/'source-01.png'),'sourceOriginalSHA256':sha(src),'alphaExtrema':im.getchannel('A').getextrema()},indent=2))
