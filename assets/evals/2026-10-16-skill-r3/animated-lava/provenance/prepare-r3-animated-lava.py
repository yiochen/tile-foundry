import hashlib,json,shutil
from pathlib import Path
root=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry/assets/evals/2026-10-16-skill-r3/animated-lava')
skill=root.parent/'skill-snapshot'
def write(name,obj):
 (root/name).write_text(json.dumps(obj,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
(root/'references').mkdir(exist_ok=True)
(root/'provenance').mkdir(exist_ok=True)
shutil.copy2(root/'guide.png',root/'references/guide.png')
shutil.copy2(skill/'assets/perspective-reference.jpg',root/'provenance/perspective-reference-inspected.jpg')
shutil.copy2(skill/'assets/perspective-reference.json',root/'provenance/perspective-reference.json')
prompt='''Use case: stylized-concept.
Asset type: opaque 4-column by 3-row appearance-material atlas for moving lava.
Input image 1 is the layout edit target: the supplied square guide. Replace its twelve dark-gray square samples with twelve successive phases of the SAME flowing molten-lava material, in row-major order: top-left to top-right, then the middle row, then the bottom row. Preserve every square boundary, square size, row, column, gutter, and outer margin from the guide. Keep the pale-gray gutters and outer margins completely opaque and undecorated.
Each sample is a completely flat square texture viewed straight on, filled all the way to its square edges. Show stylized warm orange-red molten lava, thin bright yellow-orange flowing channels, and small dark-red cooling-crust flecks. Keep the texture scale, fixed palette and average illumination identical across all twelve phases. No central bright spot or broad light-to-dark shading. Use connected medium-small flowing features suitable for game terrain.
Animate a single coherent flowing pattern through twelve evenly spaced phases of one one-second loop: the molten channels and crust drift steadily to the right, by about one twelfth of a square width per successive sample, wrapping across the square edges. The twelfth phase leads smoothly back into the first. Keep opposite texture edges periodic in every sample; joins must also remain continuous when neighboring tiles display different phases. The material should read as flowing lava rather than twelve unrelated textures.
No raised objects, perspective, front walls, blocks, scene, text, labels, numerals, borders, bevels, drop shadows, transparent pixels or cutout shapes. This call creates only the opaque material atlas; preserve the source layout exactly.'''
(root/'prompt-01.txt').write_text(prompt+'\n')
args={'prompt':prompt,'referenced_image_paths':[str(root/'references/guide.png')],'transparent_background':False}
write('tool-inputs-01.json',args)
registration={
 'kind':'animation','projection':'top-down-oblique-square-grid','cellSize':128,
 'heightAxis':[0,-1],'elevationScale':1,'elevationPx':32,'occupiedCells':[[0,0]],
 'fps':12,'frameCount':12,'order':'row-major','sourceLayout':{'columns':4,'rows':3},
 'intendedFrameSize':[192,320],'intendedGroundAnchor':[96,248],
 'intendedFootprint':[128,128],
 'authoredGeometry':{'template':'template/geometry.json','topRect':[32,152,160,280],
 'frontRect':[32,280,160,312],'groundRect':[32,184,160,312],
 'nearEdgeAnchor':[96,312],'centerAnchor':[96,248],
 'conversion':{'offset':[0,-64],'artMoved':False}},
 'sourceContract':'opaque-appearance-material-phase-atlas',
 'processingPlan':'Use frozen material_animation.py compose with strength 0.7 and authored terrain SVG face masks; sample only predeclared square material regions at one uniform atlas source scale; preserve complete 192x320 SVG alpha and image placement, then assemble_result.py. No whole-object extraction, keying, geometry correction, motion synthesis, or per-frame anchor fitting.',
 'limitations':'Authored silhouette, footprint and elevation are deterministic. AI material motion, loop quality, periodicity and seam quality require independent visual review; uniform source registration does not certify generated layout.'}
write('registration.json',registration)
write('processing-plan.json',{
 'authoredBeforeGeneration':True,'attempt':1,'maximumGenerationCalls':1,
 'sourceRoute':'model-drawn phase atlas; selected to honor explicit 4x3 source panels',
 'generationInputs':'tool-inputs-01.json','registration':'registration.json','guide':'guide.json',
 'guideSHA256':sha(root/'guide.json'),'materialStrength':0.7,
 'references':{'references/guide.png':{'role':'layout edit target: opaque 4x3 square material samples','sha256':sha(root/'references/guide.png')}},
 'inspectedNotSupplied':{'provenance/perspective-reference-inspected.jpg':{'role':'projection understanding only; not image-call input','sha256':sha(root/'provenance/perspective-reference-inspected.jpg')}},
 'commandsBeforeGeneration':[
 'python "$SKILL_DIR/scripts/material_animation.py" guide "$OUTPUT_DIR/guide"',
 'python "$SKILL_DIR/scripts/svg_tools.py" template "$OUTPUT_DIR/template" --height 32 --palette lava --plain --terrain'],
 'commandsAfterGeneration':[
 'python "$SKILL_DIR/scripts/material_animation.py" compose "$OUTPUT_DIR/template" "$OUTPUT_DIR/source-01.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/processed" --strength .7',
 'python "$SKILL_DIR/scripts/assemble_result.py" --input-result "$OUTPUT_DIR/processed/result.json" --registration "$OUTPUT_DIR/registration.json" --output "$OUTPUT_DIR/result.json"'],
 'noCorrectiveGeneration':True,'preserveFailure':True})
write('generation-01.json',{'prompt':prompt,'tool':'image_gen.imagegen','transparentBackground':False,
 'sourceSHA256':None,'references':['references/guide.png'],
 'referenceSHA256':{'references/guide.png':sha(root/'references/guide.png')},
 'referenceRoles':{'references/guide.png':'layout edit target: opaque 4x3 square material samples'},
 'toolInputs':'tool-inputs-01.json','status':'planned-before-generation'})
print(json.dumps({'plan':'processing-plan.json','registration':'registration.json','guideSHA256':sha(root/'guide.json'),'referenceSHA256':sha(root/'references/guide.png')},indent=2))
