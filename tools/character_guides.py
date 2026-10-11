#!/usr/bin/env python3
"""Authored character guides; artwork is SVG, not a generated sprite substitute."""
from pathlib import Path
from svgkit import rasterize
from tilekit import write_json

ROOT = Path(__file__).resolve().parents[1]
FRAME = (192, 320)
ANCHOR = (96, 248)
FLOOR = (32, 184, 160, 312)


def floor_svg(corners=False):
    if corners:
        return '<path d="M 32,200 V 184 H 48 M 144,184 H 160 V 200 M 32,296 V 312 H 48 M 144,312 H 160 V 296" fill="none" stroke="#7bd14b" stroke-width="4"/>'
    return '<rect x="32" y="184" width="128" height="128" fill="#7bd14b"/><path d="M 34,198 V 186 H 46 M 146,186 H 158 V 198 M 34,298 V 310 H 46 M 146,310 H 158 V 298" fill="none" stroke="#eaffd5" stroke-width="2"/>'


def stick_svg(jump=False):
    if jump:
        body = '<path d="M 96,106 V 164 M 96,120 L 70,132 L 58,108 M 96,120 L 122,130 L 134,104 M 96,164 L 76,182 L 84,208 M 96,164 L 118,181 L 108,212"/>'
        head = '<circle cx="96" cy="84" r="22"/>'
        shoes = '<path d="M 78,212 H 92 M 104,216 H 118"/>'
    else:
        body = '<path d="M 96,142 V 200 M 96,156 L 74,172 L 70,190 M 96,156 L 118,172 L 122,190 M 96,200 L 86,224 V 244 M 96,200 L 106,224 V 244"/>'
        head = '<circle cx="96" cy="120" r="22"/>'
        shoes = '<path d="M 78,248 H 92 M 100,248 H 114"/>'
    return '<g fill="none" stroke="#384c6b" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">'+body+head+shoes+'</g>'


def character_svg():
    return '''<defs>
      <linearGradient id="coat" x2="0" y2="1"><stop stop-color="#64bafb"/><stop offset="1" stop-color="#2469bf"/></linearGradient>
      <linearGradient id="skin" x2="0" y2="1"><stop stop-color="#ffe2a9"/><stop offset="1" stop-color="#eab17b"/></linearGradient>
      <linearGradient id="cap" x2="0" y2="1"><stop stop-color="#ffb751"/><stop offset="1" stop-color="#e76828"/></linearGradient>
    </defs>
    <g stroke="#344d72" stroke-width="2" stroke-linejoin="round">
      <path d="M 82,195 L 79,233 H 92 L 96,208 L 101,233 H 114 L 109,195 Z" fill="#344b72"/>
      <path d="M 78,232 H 93 V 246 H 74 Q 72,238 78,232 Z M 100,232 H 114 L 120,244 V 246 H 100 Z" fill="#623b29"/>
      <path d="M 78,151 L 67,166 L 64,187 L 73,193 L 80,174 M 114,151 L 125,166 L 128,187 L 119,193 L 112,174" fill="url(#coat)"/>
      <ellipse cx="69" cy="191" rx="7" ry="8" fill="url(#skin)"/>
      <ellipse cx="123" cy="191" rx="7" ry="8" fill="url(#skin)"/>
      <path d="M 82,146 Q 96,140 110,146 L 116,198 Q 96,209 76,198 Z" fill="url(#coat)"/>
      <path d="M 96,149 V 200" fill="none" stroke="#d6edff"/>
      <rect x="76" y="190" width="40" height="7" rx="2" fill="#5c392a"/>
      <rect x="92" y="189" width="8" height="9" rx="1" fill="#f9cb68"/>
      <circle cx="96" cy="121" r="24" fill="url(#skin)"/>
      <path d="M 72,115 Q 70,92 95,94 Q 123,94 120,115 Z" fill="url(#cap)"/>
      <path d="M 71,111 Q 96,104 125,113 L 123,118 Q 96,112 73,118 Z" fill="#fa8d32"/>
      <path d="M 78,98 Q 86,94 95,96" stroke="#ffe09b" fill="none"/>
    </g>
    <ellipse cx="87" cy="122" rx="3" ry="4" fill="#293449"/><ellipse cx="105" cy="122" rx="3" ry="4" fill="#293449"/>
    <path d="M 89,133 Q 96,139 103,133" fill="none" stroke="#8b4c38" stroke-width="2"/>
    <path d="M 74,247 H 93 M 100,247 H 120" stroke="#3b2922" stroke-width="2"/>'''


def document(content):
    return '<svg xmlns="http://www.w3.org/2000/svg" width="192" height="320" viewBox="0 0 192 320">'+content+'</svg>'


def main():
    directory = ROOT / 'assets/character-guides'
    directory.mkdir(parents=True, exist_ok=True)
    guides = {
        'box': floor_svg()+'<rect x="60" y="96" width="72" height="152" fill="#90a8c4" stroke="#384c6b" stroke-width="2"/>',
        'stick': floor_svg()+stick_svg(),
        'drawn': floor_svg()+character_svg(),
        'jump-solid': floor_svg()+stick_svg(True),
        'jump-corners': floor_svg(True)+stick_svg(True),
        'standing-corners': floor_svg(True)+character_svg(),
        'character-only': character_svg(),
        'floor-only': floor_svg(),
        'corners-only': floor_svg(True),
    }
    for name, content in guides.items():
        svg = document(content)
        (directory/f'{name}.svg').write_text(svg+'\n')
        rasterize(svg).save(directory/f'{name}.png')
        rasterize(svg, 4).save(directory/f'{name}-4x.png')
    write_json(directory/'geometry.json', {'version':1,'frame':FRAME,'footprint':[128,128],
        'floorRect':FLOOR,'anchor':ANCHOR,'anchorMeaning':'Floor cell center, independent of feet and sprite bounds',
        'standingFootBaseline':248,'jumpFootMidpoint':[98,214],'jumpExpectedElevation':34,
        'cornerOuterRect':[30,182,162,314],'referenceScale':4})
    print('Authored character SVG variants and clean floor references')


if __name__ == '__main__':
    main()
