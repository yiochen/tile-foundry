from pathlib import Path
from PIL import Image
import json, hashlib, shutil
root=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry')
out=root/'assets/evals/2026-10-16-skill-r3/animated-waves'
skill=root/'assets/evals/2026-10-16-skill-r3/skill-snapshot'
(out/'references').mkdir(exist_ok=True)
(out/'provenance').mkdir(exist_ok=True)
shutil.copyfile(out/'guide.png',out/'references/material-atlas-guide.png')
shutil.copyfile(skill/'assets/perspective-reference.jpg',out/'provenance/inspected-projection-reference.jpg')
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prompt='''Use case: stylized-concept
Asset type: opaque ocean-water appearance-material animation atlas.
Input image 1 is the exact layout edit target: a 1024 by 1024 square containing twelve equal gray square samples in four columns and three rows. Replace each gray sample with a complete flat ocean-water material phase. Preserve all sample boundaries, margins and gutters in their exact positions. All gutters and outer margins must stay fully opaque neutral light gray.

Create twelve successive phases of a single gently rolling ocean wave surface, in row-major order: left to right across the first row, then the second row, then the third row. The samples form a continuous one-second loop with twelve equally spaced steps. Keep the same waves and crests progressing smoothly at each step; the last phase leads naturally into the first phase. Broad rounded ripples with slender soft white and pale-cyan crest streaks on medium cyan-blue water, polished hand-painted game texture. No shore, land, objects or debris.

Every sample is a flat fully opaque square material, filled to its edges, seen straight down with no perspective, no extrusion, no front wall and no raised geometry. Use constant palette, texture scale and uniform average illumination across all twelve samples. No global brightness drift. Opposite edges must continue their ripple patterns and colors, and the entire perimeter pattern must remain identical across phases so adjacent copies can connect even with different phases. Keep movement in the interior fluid and readable, with gentle periodic wave motion rather than independent new water patterns.

Exact layout from the reference: each sample is 224 by 224; column left edges are 16, 272, 528, 784; row top edges are 144, 400, 656. These positions only specify the reference layout. Do not draw coordinates or labels. Keep twelve distinct square samples with opaque 32px gutters. No border, rim, bevel, drop shadow, scenery, text, numbering, watermark, transparent pixels or cutout silhouettes.'''
args={'prompt':prompt,'referenced_image_paths':[str(out/'references/material-atlas-guide.png')],'transparent_background':False}
(out/'generation-01-prompt.txt').write_text(prompt+'\n')
(out/'tool-inputs-01.json').write_text(json.dumps(args,indent=2)+'\n')
registration={
 'kind':'animation','projection':'top-down-oblique-square-grid','heightAxis':[0,-1],'elevationScale':1,
 'elevationPx':32,'occupiedCells':[[0,0]],'supportCells':[[0,0]],'order':'row-major',
 'sourceContract':'opaque-material-atlas-12-model-drawn-phases',
 'intendedFrameSize':[192,320],'intendedGroundAnchor':[96,248],'intendedFootprint':[128,128],
 'intendedTopRect':[32,152,160,280],'intendedFrontRect':[32,280,160,312],
 'authoredNearEdgeAnchor':[96,312],
 'anchorConversion':{'from':'near-edge','to':'center','offset':[0,-64],'artMoved':False},
 'intendedTiming':{'count':12,'fps':12,'durationMs':1000/12,'totalDurationMs':1000},
 'sourceLayout':{'guide':'guide.json','columns':4,'rows':3,'order':'row-major'},
 'processingPlan':{'geometry':'authored template SVG and masks preserve complete frame and alpha',
 'materialSampling':'known authored square regions at one uniform source scale; no object clipping',
 'processor':'frozen scripts/material_animation.py compose','strength':.7,
 'palette':'authored ocean palette; only generated high-frequency RGB detail is transferred',
 'motion':'12 supplied source phases; no synthesis or corrective generation'},
 'sprites':[{'id':f'wave-{i:02}'} for i in range(12)]
}
(out/'registration.json').write_text(json.dumps(registration,indent=2)+'\n')
plan={
 'authoredBeforeGeneration':True,'caseId':'animated-waves','generationCallLimit':1,
 'route':'model-drawn phase atlas mapped onto authored full-cell raised faces',
 'rationale':'The request explicitly asks for twelve source panels in a 4-column 3-row layout. The frozen material-animation workflow keeps their source contract opaque and flat while authored faces provide footprint, wall height and projection.',
 'invariants':{'frame':[192,320],'groundCenterAnchor':[96,248],'footprint':[128,128],'frontWallHeightPx':32,'count':12,'fps':12,'order':'row-major'},
 'guideSHA256':hashfile(out/'guide.json'),
 'referenceSHA256':{'references/material-atlas-guide.png':hashfile(out/'references/material-atlas-guide.png')},
 'referenceRoles':{'references/material-atlas-guide.png':'layout edit target: twelve opaque square appearance-material samples'},
 'inspectedOnlyProvenance':{'provenance/inspected-projection-reference.jpg':{'role':'projection explanation; not sent to model','sha256':hashfile(out/'provenance/inspected-projection-reference.jpg')}},
 'templateGeometry':'template/geometry.json',
 'plannedCommands':[
 'python "$SKILL_DIR/scripts/material_animation.py" compose "$OUTPUT_DIR/template" "$OUTPUT_DIR/source-01.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/processed" --strength .7',
 'python "$SKILL_DIR/scripts/assemble_result.py" --input-result "$OUTPUT_DIR/processed/result.json" --registration "$OUTPUT_DIR/registration.json" --output "$OUTPUT_DIR/result.json"'],
 'failurePolicy':'Retain original and all evidence; no second image call, guide fitting, per-axis scale changes, clipping or post-generation anchor adjustment.'
}
(out/'processing-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'registration':str(out/'registration.json'),'plan':str(out/'processing-plan.json'),'toolInputs':str(out/'tool-inputs-01.json'),'guideSHA256':plan['guideSHA256']}))
