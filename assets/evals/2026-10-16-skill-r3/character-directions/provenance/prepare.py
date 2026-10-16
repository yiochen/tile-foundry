import sys,json,hashlib,shutil
from pathlib import Path
ROOT=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry')
SKILL=ROOT/'assets/evals/2026-10-16-skill-r3/skill-snapshot'
OUT=ROOT/'assets/evals/2026-10-16-skill-r3/character-directions'
sys.path.insert(0,str(SKILL/'scripts'))
from svg_tools import rasterize
from tile_tools import write_json
(OUT/'references').mkdir(exist_ok=True)
(OUT/'provenance').mkdir(exist_ok=True)
(OUT/'previews').mkdir(exist_ok=True)
dirs=['north','northeast','east','southeast','south','southwest','west','northwest']
parts=[];cells=[]
for i,d in enumerate(dirs):
    x=(i%4)*224;y=(i//4)*352
    # A neutral sparse anatomy guide; silhouette width varies by facing, height does not.
    torso=13 if d in ('east','west') else 21 if d in ('north','south') else 18
    stance=7 if d in ('east','west') else 13
    body=f'<circle cx="96" cy="105" r="17" fill="#b3becd"/><path d="M {96-torso},134 Q 96,122 {96+torso},134 L {96+torso-4},189 L {96-torso+4},189 Z" fill="#b3becd"/><g fill="none" stroke="#a3afbf" stroke-width="10" stroke-linecap="round"><path d="M {96-torso+1},140 L {96-torso-6},191 M {96+torso-1},140 L {96+torso+6},191 M {96-torso+7},186 L {96-stance},244 M {96+torso-7},186 L {96+stance},244"/></g><path d="M {89-stance},248 H {101-stance} M {91+stance},248 H {103+stance}" stroke="#a3afbf" stroke-width="5" stroke-linecap="round"/>'
    parts.append(f'<g transform="translate({x},{y})"><rect x="32" y="184" width="128" height="128" fill="rgb(123,209,75)"/>{body}</g>')
    cells.append({'index':i,'direction':d,'rect':[x,y,x+192,y+320],'anchor':[96,248],'floorRect':[32,184,160,312]})
svg='<svg xmlns="http://www.w3.org/2000/svg" width="864" height="672" viewBox="0 0 864 672">'+''.join(parts)+'</svg>'
(OUT/'guide.svg').write_text(svg+'\n')
rasterize(svg).save(OUT/'references/guide.png')
rasterize(svg,2).save(OUT/'previews/guide-2x.png')
guide={'version':1,'kind':'object-sheet','size':[864,672],'frame':[192,320],'cellSize':128,'anchor':[96,248],'keyRGB':[123,209,75],'columns':4,'rows':2,'gutter':32,'cells':cells,'order':'row-major','nominalStandingHeight':160}
write_json(OUT/'guide.json',guide)
registration={'kind':'directions','projection':'top-down-oblique-square-grid','heightAxis':[0,-1],'elevationScale':1,'elevationPx':160,'occupiedCells':[[0,0]],'nominalStandingHeight':160,'order':dirs,'sprites':[{'id':'player-'+d,'direction':d} for d in dirs]}
write_json(OUT/'registration.json',registration)
prompt='''Use case: sketch-to-render. The supplied raster is a layout edit target for an original 8-direction player-character sprite source sheet. Replace all eight gray neutral-standing placeholders with the SAME one original player; invent a charming, readable hand-painted adventure-game design. Retain the eight plain bright-green calibration squares exactly as shown. Their shape, placement and flat reserved RGB 123,209,75 are calibration geometry, not scenery. Do not shade them, add rims, or cast shadows onto them.

Keep this exact canvas aspect and 4-column, 2-row panel layout. Each conceptual panel is 192x320, with 32px transparent gutters. Canvas 864x672. Every panel contains one complete independently isolated character standing neutrally upright with relaxed arms, on its own calibration square. The row-major direction order is NORTH (back view, facing up), NORTHEAST (back-right view), EAST (right profile), SOUTHEAST (front-right view), SOUTH (front view, facing down), SOUTHWEST (front-left view), WEST (left profile), NORTHWEST (back-left view). Rotate only the character around its ground root. Keep one identity, anatomy, costume, palette, scale, lighting and fixed camera across all directions.

Square-grid top-down oblique game projection, front-facing three-quarter view: ground cells remain screen-aligned squares with parallel horizontal/vertical edges, never diamonds. Show character tops and fronts appropriate to each facing. Height projects vertically upward. Use a fixed camera, no vanishing-point convergence or camera rotation.

Each local calibration square remains x=32 to160, y=184 to312, width and depth128. The projected ground root is its center at local (96,248), between the supporting feet. Entire crown-to-ground-root standing design height, including hair or cap, is 160px: 1.25 calibration-square widths. Match the sparse guide's top at y=88 and root y=248; leave the large headroom empty. This is a compact game character at the guide's size, not a panel-filling portrait. Feet support the body at that common root; small shoe toes can extend below it. Keep every limb, hair and accessory complete inside its panel. Reserve the green calibration hue exclusively for the squares, especially around legs and shoes.

Preserve actual transparency outside each complete character and its calibration square, including all gutters. Omit the gray placeholder, guide strokes, labels, borders, scenery, checkerboard paint and text. Keep every calibration square visible and intact around the feet in the generated source.'''
(OUT/'prompt-01.txt').write_text(prompt+'\n')
call={'prompt':prompt,'referenced_image_paths':[str(OUT/'references/guide.png')],'transparent_background':True}
write_json(OUT/'tool-input-01.json',call)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copy2(SKILL/'assets/perspective-reference.jpg',OUT/'provenance/projection-reference-inspected-not-supplied.jpg')
plan={'status':'planned-before-generation','generationCalls':1,'correctionCalls':0,'sourceContract':'transparent isolated whole-asset panels; opaque reserved green calibration squares retained in source','sourceLayout':{'columns':4,'rows':2,'frame':[192,320],'gutter':32,'size':[864,672],'order':dirs},'projection':'top-down-oblique-square-grid','cellSize':128,'heightAxis':[0,-1],'elevationScale':1,'registrationBasis':'floor-width','normalization':'Measure intact floor width and center separately in each isolated panel. Uniformly scale 128/measuredWidth and translate floor center to (96,248); never scale from alpha bounds or fit foot positions. No axis stretching.','floorRemoval':{'method':'bundled remove_floor_chroma after normalization','keyRGB':[123,209,75],'minAlpha':32,'hueToleranceDegrees':28,'hueFeatherDegrees':8,'saturationTransition':[0.02,0.12]},'panelExtraction':'Strict known guide panels first. If actual art only protrudes into planned gutters, inspect and allow bundled alpha-seam recovery only when whole transparent separator exists; retain original failure. Never clip touching art.','processingCommand':'python SKILL_DIR/scripts/tile_tools.py process-on-floor source-01.png guide.json processed --min-alpha 32 --registration floor-width','resultAssembly':'python SKILL_DIR/scripts/assemble_result.py --input-result processed/result.json --registration registration.json --output result.json','limitations':'AI geometry and nominal anatomy height are design targets, not certified geometry. Mixed chroma edges are approximate. Report any processing failure with sources intact.','references':{'references/guide.png':{'role':'layout edit target','sha256':sha(OUT/'references/guide.png')}},'inspectedNotSupplied':{'provenance/projection-reference-inspected-not-supplied.jpg':{'role':'projection interpretation only; not supplied to image generation','sha256':sha(OUT/'provenance/projection-reference-inspected-not-supplied.jpg')}},'guideSHA256':sha(OUT/'guide.json'),'registrationSHA256':sha(OUT/'registration.json')}
write_json(OUT/'processing-plan.json',plan)
shutil.copy2('/tmp/character_directions_prepare.py',OUT/'provenance/prepare.py')
print(json.dumps({'guide':str(OUT/'references/guide.png'),'size':[864,672],'guideSHA256':sha(OUT/'guide.json'),'referenceSHA256':sha(OUT/'references/guide.png'),'plan':str(OUT/'processing-plan.json')},indent=2))
