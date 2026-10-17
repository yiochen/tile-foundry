"""Create ungraded evidence without changing any source or runtime frame."""
from pathlib import Path
import importlib.util
import json
import shutil
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
FROZEN = ROOT.parent / 'skill-snapshot' / 'scripts'
PREVIEWS = ROOT / 'previews'
PREVIEWS.mkdir(exist_ok=True)
shutil.copy2(FROZEN / 'review_playback.py', ROOT / 'playback_helper.py')
spec = importlib.util.spec_from_file_location('playback_helper', ROOT / 'playback_helper.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

for label, manifest_path in [('reskin', ROOT / 'result.json'), ('direct3d', ROOT / 'render/result.json')]:
    manifest = json.loads(manifest_path.read_text())
    sprites = manifest['sprites']
    paths = [manifest_path.parent / s['image'] for s in sprites]
    helper.write_playback(sprites, paths, PREVIEWS / f'{label}-playback.html')
    for theme, color in [('light', '#f4f6ef'), ('dark', '#18222e')]:
        sheet = Image.new('RGBA', (4 * 224 + 16, 3 * 352 + 16), color)
        draw = ImageDraw.Draw(sheet)
        for i, (sprite, path) in enumerate(zip(sprites, paths)):
            left, top = 16 + (i % 4) * 224, 16 + (i // 4) * 352
            root_x, root_y = left + sprite['anchor'][0], top + sprite['anchor'][1]
            half_w, half_h = sprite['footprint'][0] / 2, sprite['footprint'][1] / 2
            draw.rectangle((root_x - half_w, root_y - half_h, root_x + half_w, root_y + half_h), outline='#789080')
            with Image.open(path) as im:
                assert list(im.size) == sprite['size']
                sheet.alpha_composite(im.convert('RGBA'), (left, top))
            draw.line((root_x - 5, root_y, root_x + 5, root_y), fill='#b72e74')
            draw.line((root_x, root_y - 5, root_x, root_y + 5), fill='#b72e74')
            draw.text((left, top), f'{label} frame {i:02}', fill='#8d9b94' if theme == 'dark' else '#35443b')
        sheet.convert('RGB').save(PREVIEWS / f'{label}-{theme}-native.png')
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST).convert('RGB').save(PREVIEWS / f'{label}-{theme}-2x.png')

with Image.open(ROOT / 'source-01.png') as source:
    for theme, color in [('light', '#f4f6ef'), ('dark', '#18222e')]:
        background = Image.new('RGBA', source.size, color)
        background.alpha_composite(source.convert('RGBA'))
        background.convert('RGB').save(PREVIEWS / f'source-{theme}.png')

print(json.dumps({'previews': sorted(p.name for p in PREVIEWS.iterdir()), 'modifiedRuntimeFrames': False}, indent=2))
