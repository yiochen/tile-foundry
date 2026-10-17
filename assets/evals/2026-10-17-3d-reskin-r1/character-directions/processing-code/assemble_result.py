#!/usr/bin/env python3
"""Wrap measured processor outputs in a portable delivery manifest; never fit art."""
import argparse
import json
from pathlib import Path
from PIL import Image
from tile_tools import write_json


def assemble(input_results, registration_path, output_path):
    output_path = Path(output_path).resolve()
    root = output_path.parent
    registration_path = Path(registration_path).resolve()
    registration = json.loads(registration_path.read_text())
    for key in ('kind', 'projection', 'elevationPx', 'occupiedCells'):
        if key not in registration:
            raise ValueError(f'Missing authored registration field: {key}')
    if registration['projection'] != 'top-down-oblique-square-grid':
        raise ValueError('Unknown projection profile')
    sprites = []
    overrides = registration.get('sprites', [])
    for input_path in input_results:
        input_path = Path(input_path).resolve()
        processing = json.loads(input_path.read_text())
        entries = processing.get('frames') or [processing]
        for entry in entries:
            image_path = (input_path.parent / entry['image']).resolve()
            if root not in image_path.parents:
                raise ValueError('Processed images must be inside the output asset bundle')
            with Image.open(image_path) as opened:
                image = opened.convert('RGBA')
            if list(image.size) != entry['size']:
                raise ValueError('Processing metadata does not match actual image size')
            box = image.getchannel('A').getbbox()
            if box is None:
                raise ValueError('Processed sprite is empty')
            index = len(sprites)
            if overrides and index >= len(overrides):
                raise ValueError('Per-sprite registration count does not match processed outputs')
            extra = overrides[index] if overrides else {}
            if any(k in extra for k in ('size', 'anchor', 'footprint', 'image', 'artRect')):
                raise ValueError('Registration may not replace measured frame geometry')
            sprite = {'id': f'sprite-{index:02}', 'index': index,
                      'image': image_path.relative_to(root).as_posix(),
                      'size': entry['size'], 'anchor': entry['anchor'], 'footprint': entry['footprint'],
                      'artRect': [box[0], box[1], box[2]-box[0], box[3]-box[1]],
                      'occupiedCells': registration['occupiedCells'],
                      'elevationPx': registration['elevationPx'],
                      'processing': entry, **extra}
            if registration['kind'] == 'animation':
                duration = entry.get('durationMs', 0)
                if abs(duration-1000/12) >= .001:
                    raise ValueError('Processing must already use 12 fps; no silent retiming')
                sprite['durationMs'] = duration
            sprites.append(sprite)
    if overrides and len(overrides) != len(sprites):
        raise ValueError('Per-sprite registration count does not match processed outputs')
    ids = [s['id'] for s in sprites]
    if not ids or not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Each processed sprite needs a unique, nonempty ID')
    result = {k: v for k,v in registration.items() if k not in ('sprites','elevationPx','occupiedCells')}
    result.update(version=2, cellSize=128, groundAnchorAlignment='center', sprites=sprites,
                  geometryDeclaration='Footprints/elevation/roles are authored constraints; visual verification required')
    if registration['kind'] == 'animation':
        result['fps'] = 12
    write_json(output_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-result', type=Path, action='append', required=True)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = assemble(args.input_result, args.registration, args.output)
    print(json.dumps({'kind':result['kind'],'sprites':len(result['sprites']),'output':str(args.output)},indent=2))


if __name__ == '__main__':
    main()
