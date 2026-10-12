#!/usr/bin/env python3
"""Author sparse SVG references for ground materials and objects on calibration floors."""
import argparse
from pathlib import Path
from svg_tools import rasterize
from tile_tools import write_json

FRAME=(192,320)
ANCHOR=(96,248)
FLOOR=(32,184,160,312)

# Pose geometry only: clothing, anatomy, and character identity belong to imagegen.
DANCE=[
    ((96,110),(96,140),(96,198),[(76,158),(64,140)],[(116,158),(128,140)],[(84,224),(82,248)],[(108,224),(110,248)]),
    ((84,106),(88,137),(96,198),[(64,128),(58,106)],[(110,154),(126,164)],[(78,220),(70,248)],[(104,226),(106,248)]),
    ((108,106),(104,137),(96,198),[(82,154),(66,164)],[(128,128),(134,106)],[(88,226),(86,248)],[(114,220),(122,248)]),
    ((96,102),(96,133),(96,195),[(74,119),(64,88)],[(118,119),(128,88)],[(78,220),(70,248)],[(114,220),(122,248)]),
    ((90,110),(92,140),(96,198),[(68,148),(60,178)],[(114,128),(126,108)],[(106,222),(112,248)],[(86,224),(80,248)]),
    ((102,110),(100,140),(96,198),[(78,128),(66,108)],[(124,148),(132,178)],[(106,224),(112,248)],[(86,222),(80,248)]),
]


def pose_svg(pose):
    head,neck,hip,left_arm,right_arm,left_leg,right_leg=pose
    def chain(points):return 'M '+' L '.join(f'{x},{y}' for x,y in points)
    lines=[chain([neck,hip]),chain([neck,*left_arm]),chain([neck,*right_arm]),
           chain([hip,*left_leg]),chain([hip,*right_leg])]
    for leg in (left_leg,right_leg):
        x,y=leg[-1];lines.append(f'M {x-6},{y} H {x+6}')
    return f'<g fill="none" stroke="#384c6b" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><circle cx="{head[0]}" cy="{head[1]}" r="20"/><path d="'+ ' '.join(lines)+'"/></g>'


def build(kind,stem,key_rgb=(123,209,75),columns=3):
    stem=Path(stem);stem.parent.mkdir(parents=True,exist_ok=True)
    if kind=='floor':
        size=(128,128);content='<rect width="128" height="128" fill="#777777"/>'
        metadata={'version':1,'kind':'floor','size':list(size),'cellSize':128,'anchor':[64,64]}
    else:
        if kind=='object':poses=DANCE[:1];columns=1
        else:poses=DANCE
        if not 1<=columns<=len(poses):raise ValueError('Columns must fit the pose count')
        rows=(len(poses)+columns-1)//columns;gutter=32
        size=(columns*FRAME[0]+(columns-1)*gutter,rows*FRAME[1]+(rows-1)*gutter)
        parts=[];cells=[];color='rgb('+','.join(map(str,key_rgb))+')'
        for i,pose in enumerate(poses):
            x=(i%columns)*(FRAME[0]+gutter);y=(i//columns)*(FRAME[1]+gutter)
            parts.append(f'<g transform="translate({x},{y})"><rect x="32" y="184" width="128" height="128" fill="{color}"/>'+pose_svg(pose)+'</g>')
            cells.append({'index':i,'rect':[x,y,x+FRAME[0],y+FRAME[1]],'anchor':list(ANCHOR),'floorRect':list(FLOOR)})
        content=''.join(parts)
        metadata={'version':1,'kind':'object-sheet','size':list(size),'frame':list(FRAME),
            'cellSize':128,'anchor':list(ANCHOR),'keyRGB':list(key_rgb),'columns':columns,
            'rows':rows,'gutter':gutter,'cells':cells,'order':'row-major'}
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" height="{size[1]}" viewBox="0 0 {size[0]} {size[1]}">{content}</svg>'
    stem.with_suffix('.svg').write_text(svg+'\n')
    rasterize(svg).save(stem.with_suffix('.png'))
    rasterize(svg,4).save(stem.parent/(stem.name+'-4x.png'))
    write_json(stem.with_suffix('.json'),metadata)
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=('floor','object','dance'))
    parser.add_argument('output',type=Path,help='Output stem: writes SVG, PNG, 4x PNG, and layout JSON')
    parser.add_argument('--key-rgb',type=int,nargs=3,default=(123,209,75))
    parser.add_argument('--columns',type=int,default=3)
    args=parser.parse_args()
    if any(not 0<=c<=255 for c in args.key_rgb):parser.error('Key RGB must be 0..255')
    build(args.kind,args.output,tuple(args.key_rgb),args.columns)
    print(args.output.with_suffix('.json'))


if __name__=='__main__':main()
