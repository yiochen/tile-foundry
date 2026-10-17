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


def build(kind,stem,key_rgb=(123,209,75),columns=3,height=160,base=(48,48),frames=6):
    stem=Path(stem);stem.parent.mkdir(parents=True,exist_ok=True)
    if kind=='floor':
        size=(128,128);content='<rect width="128" height="128" fill="#777777"/>'
        metadata={'version':1,'kind':'floor','size':list(size),'cellSize':128,'anchor':[64,64]}
    else:
        if kind in ('object','envelope'):poses=DANCE[:1];columns=1
        else:
            if frames not in (6,12):raise ValueError('Dance guide supports 6 or 12 frames')
            poses=[]
            for i in range(frames):
                position=i*len(DANCE)/frames;index=int(position);fraction=position-index
                def between(a,b):
                    if isinstance(a,(tuple,list)):return [between(x,y) for x,y in zip(a,b)]
                    return round(a+(b-a)*fraction)
                poses.append(between(DANCE[index],DANCE[(index+1)%len(DANCE)]))
        if not 1<=columns<=len(poses):raise ValueError('Columns must fit the pose count')
        rows=(len(poses)+columns-1)//columns;gutter=32
        size=(columns*FRAME[0]+(columns-1)*gutter,rows*FRAME[1]+(rows-1)*gutter)
        parts=[];cells=[];color='rgb('+','.join(map(str,key_rgb))+')'
        for i,pose in enumerate(poses):
            x=(i%columns)*(FRAME[0]+gutter);y=(i//columns)*(FRAME[1]+gutter)
            if kind=='envelope':
                if not 0<height<ANCHOR[1] or any(not 0<v<=128 for v in base):
                    raise ValueError('Envelope height must fit above the root and base must fit the floor')
                left=ANCHOR[0]-base[0]/2;top=ANCHOR[1]-height
                # A plain filled envelope communicates the entire design height;
                # a thin line is easily read as just the shaft of a taller prop.
                subject=(f'<rect x="{left}" y="{top}" width="{base[0]}" height="{height}" fill="#b3becd"/>'
                    f'<rect x="{left}" y="{ANCHOR[1]-base[1]/2}" width="{base[0]}" height="{base[1]}" fill="#7c8b9f"/>'
                    f'<path d="M {left-8},{top} H {left+base[0]+8}" stroke="#384c6b" stroke-width="2"/>')
            else:subject=pose_svg(pose)
            parts.append(f'<g transform="translate({x},{y})"><rect x="32" y="184" width="128" height="128" fill="{color}"/>'+subject+'</g>')
            cells.append({'index':i,'rect':[x,y,x+FRAME[0],y+FRAME[1]],'anchor':list(ANCHOR),'floorRect':list(FLOOR)})
        content=''.join(parts)
        metadata={'version':1,'kind':'object-sheet','size':list(size),'frame':list(FRAME),
            'cellSize':128,'anchor':list(ANCHOR),'keyRGB':list(key_rgb),'columns':columns,
            'rows':rows,'gutter':gutter,'cells':cells,'order':'row-major'}
        if kind=='envelope':
            metadata['subjectRegistration']={'baseSize':list(base),'height':height,'groundClearancePx':0}
        if kind=='dance':metadata.update(nominalStandingHeight=160,fps=12)
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" height="{size[1]}" viewBox="0 0 {size[0]} {size[1]}">{content}</svg>'
    stem.with_suffix('.svg').write_text(svg+'\n')
    rasterize(svg).save(stem.with_suffix('.png'))
    rasterize(svg,4).save(stem.parent/(stem.name+'-4x.png'))
    write_json(stem.with_suffix('.json'),metadata)
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=('floor','object','envelope','dance'))
    parser.add_argument('output',type=Path,help='Output stem: writes SVG, PNG, 4x PNG, and layout JSON')
    parser.add_argument('--key-rgb',type=int,nargs=3,default=(123,209,75))
    parser.add_argument('--columns',type=int,default=3)
    parser.add_argument('--height',type=int,default=160,help='Envelope: total crown-to-ground-root design height')
    parser.add_argument('--base',type=int,nargs=2,default=(48,48),help='Envelope: screen-aligned base width and depth')
    parser.add_argument('--frames',type=int,choices=(6,12),default=6,help='Dance guide: key poses plus interpolated transitions')
    args=parser.parse_args()
    if any(not 0<=c<=255 for c in args.key_rgb):parser.error('Key RGB must be 0..255')
    build(args.kind,args.output,tuple(args.key_rgb),args.columns,args.height,tuple(args.base),args.frames)
    print(args.output.with_suffix('.json'))


if __name__=='__main__':main()
