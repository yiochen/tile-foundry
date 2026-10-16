from pathlib import Path
import json, sys, hashlib
OUT=Path(__file__).resolve().parent
SKILL=OUT.parent/'skill-snapshot'
sys.path.insert(0,str(SKILL/'scripts'))
from svg_tools import rasterize
from PIL import Image

def write(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

(OUT/'references').mkdir(exist_ok=True)
(OUT/'previews').mkdir(exist_ok=True)
directions=['north','northeast','east','southeast','south','southwest','west','northwest']
# Author registration before generation: same square and neutral pose in every isolated panel.
# Empty margins and gutters make the entire reference a 3:2 canvas.
size=[1152,768]
parts=[];cells=[]
for i,direction in enumerate(directions):
    x=48+(i%4)*288;y=32+(i//4)*384
    cells.append({'index':i,'direction':direction,'rect':[x,y,x+192,y+320],'anchor':[96,248],'floorRect':[32,184,160,312]})
    parts.append(f'''<g transform="translate({x},{y})">
      <rect x="32" y="184" width="128" height="128" fill="rgb(123,209,75)"/>
      <g fill="none" stroke="#5a6679" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="96" cy="108" r="20"/>
      <path d="M 96,128 V 194 M 96,136 L 76,148 L 72,193 M 96,136 L 116,148 L 120,193 M 96,194 L 84,222 L 84,248 M 96,194 L 108,222 L 108,248 M 78,248 H 90 M 102,248 H 114"/>
      </g></g>''')
svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1152" height="768" viewBox="0 0 1152 768">'+''.join(parts)+'</svg>\n'
(OUT/'guide.svg').write_text(svg)
rasterize(svg).save(OUT/'guide.png')
rasterize(svg).save(OUT/'references/guide.png')
rasterize(svg,2).save(OUT/'guide-2x.png')
guide={'version':1,'kind':'object-sheet','size':size,'frame':[192,320],'cellSize':128,'anchor':[96,248],'keyRGB':[123,209,75],'columns':4,'rows':2,'gutter':[96,64],'outerMargins':[48,32],'cells':cells,'order':'row-major','nominalStandingHeight':160,'heightAxis':[0,-1],'elevationScale':1,'projection':'top-down-oblique-square-grid','authoredBeforeGeneration':True,'subjectRegistration':{'nominalHeadCrownY':88,'groundRoot':[96,248],'nominalStandingHeight':160,'rootIndependentOfToes':True}}
write(OUT/'guide.json',guide)
registration={'kind':'directions','projection':'top-down-oblique-square-grid','elevationPx':160,'occupiedCells':[[0,0]],'heightAxis':[0,-1],'elevationScale':1,'nominalStandingHeight':160,'registration':{'method':'measured-calibration-floor','guide':'guide.json'},'sprites':[{'id':f'player-{d}','direction':d} for d in directions]}
write(OUT/'registration.json',registration)
prompt='''Use case: stylized-concept
Asset type: original eight-direction game character sheet, one continuous identity in eight isolated panels.
Input image 1 is an EDIT TARGET and geometry/layout guide only. Replace the gray stick placeholders with the original player character. Preserve every plain green calibration square, its screen-aligned square shape, exact placement, and uniform reserved RGB 123,209,75. Keep all empty margins and panel separators truly transparent.

Create one original player character with a cohesive illustrated RPG design. Invent an appealing, readable adventurer identity with simple clothing, boots, a clear hairstyle and modest practical accessories. No weapons or other extended props. Use polished hand-painted game-sprite shading and clean silhouettes. Keep exactly the same anatomy, outfit, colors, facial identity, hair, accessories and lighting across all eight views. Reserve the green calibration hue exclusively for the floor, including in the lower body where it overlaps the square.

Follow the supplied 1152x768 canvas and its exact four-column, two-row panel layout. Each isolated panel corresponds to a 192x320 logical frame. Reading left to right: top row NORTH (back view, facing screen up), NORTHEAST (back/right view, facing upper right), EAST (right-facing profile), SOUTHEAST (front/right view, facing lower right); bottom row SOUTH (front view, facing screen down), SOUTHWEST (front/left view, facing lower left), WEST (left-facing profile), NORTHWEST (back/left view, facing upper left). Turn only the character around the fixed root. Every direction is the same relaxed neutral upright standing pose, arms resting at the sides, feet planted naturally; no walking, dancing, crouching or leaning.

Camera and projection: fixed square-grid top-down oblique projection, front-facing three-quarter game view. The ground squares remain horizontal/vertical screen-aligned squares, never diamond-shaped or foreshortened. See the top of the head and shoulders while retaining readable upright bodies. Preserve parallel edges; no perspective vanishing points and no camera rotation between directions.

Scale and root: in every local panel the full crown-to-ground-root design height is nominally 160 pixels, exactly 1.25 widths of the visible 128px calibration square, including all hair or headwear. The sparse guide's crown is at local y=88 and projected ground root is local (96,248). Keep head, torso, limb lengths and total anatomy scale consistent in every view. Place the root at the center of each calibration square. Shoe toes may extend a little below that root without moving it. Keep each complete subject inside its isolated panel; do not touch neighboring panels or their separators.

Preserve the green squares as temporary visible calibration substrates, flat and uniform, without rims, bevels, texture, gradients, front walls or cast shadows. Render actual alpha transparency outside the characters and squares. Remove the gray guide strokes completely. No labels, numbers, arrows, scenery, checkerboard paint or watermark. Produce only these eight isolated character-on-square panels on the supplied canvas.'''
(OUT/'prompt-01.txt').write_text(prompt+'\n')
args={'prompt':prompt,'referenced_image_paths':[str(OUT/'references/guide.png')],'transparent_background':True}
write(OUT/'imagegen-input-01.json',args)
recipe={'prompt':prompt,'references':['references/guide.png'],'referenceSHA256':{'references/guide.png':digest(OUT/'references/guide.png')},'referenceRoles':{'references/guide.png':'edit-target: authored sparse geometry and calibration layout; not appearance or identity'},'transparentBackground':True,'tool':'image_gen.imagegen','toolInputs':args,'sourceSHA256':None,'attempt':1,'attemptBudget':1}
write(OUT/'generation-01.json',recipe)
result={'version':2,'kind':'directions','status':'blocked','projection':'top-down-oblique-square-grid','cellSize':128,'groundAnchorAlignment':'center','heightAxis':[0,-1],'elevationScale':1,'sprites':[],'diagnostics':['Generation and deterministic extraction have not completed.']}
write(OUT/'result.json',result)
submission={'caseId':'character-directions','outputDirectory':str(OUT),'userPrompt':(OUT/'request.txt').read_text().rstrip('\n'),'sources':[],'guide':'guide.json','guideSHA256':digest(OUT/'guide.json'),'result':'result.json'}
write(OUT/'submission.json',submission)
write(OUT/'guide-authorship.json',{'script':'author-guide.py','rasterizer':'frozen skill scripts/svg_tools.py:rasterize (CairoSVG)','generationReference':'references/guide.png','sourceGuideSHA256':digest(OUT/'guide.svg'),'guideSHA256':digest(OUT/'guide.json'),'rasterSHA256':digest(OUT/'references/guide.png'),'declaredConstraintsAreNotMeasurements':True,'projectionReferenceInspected':str(SKILL/'assets/perspective-reference.jpg'),'projectionReferenceSuppliedToImageTool':False})
print(json.dumps({'guide':str(OUT/'guide.png'),'size':size,'referenceSHA256':digest(OUT/'references/guide.png'),'directions':directions},indent=2))
