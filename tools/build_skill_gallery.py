#!/usr/bin/env python3
"""Publish saved skill-eval artifacts for the static playground; no new generation."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'assets/evals/2026-10-11-skill-v1'
PUBLIC = ROOT / 'public/assets'


def copy(source, relative):
    destination = PUBLIC / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return relative


def main():
    floor = json.loads((RUN / 'lava-tile/tile.json').read_text())
    floor.update(id='lava', name='Lava tile',
                 image=copy(RUN / 'lava-tile/tile.png', 'skill-evals/lava.png'))
    animations = []
    for folder, title, note in [
        ('dancing-player', 'Dance · first attempt',
         'The final two poses repeat. This attempt failed the pose-diversity eval.'),
        ('dancing-player-retry', 'Dance · corrected poses',
         'Six distinct poses. The floor sets every anchor; shoe edges are approximate. The loop has an abrupt wrap.')
    ]:
        trial = RUN / folder
        submission = json.loads((trial / 'submission.json').read_text())
        result_path = trial / submission['result']
        result = json.loads(result_path.read_text())
        # Preserve the original 8 fps experiment record; publish the existing
        # frames under the requested 12 fps playback contract.
        source_durations = [f['durationMs'] for f in result['frames']]
        result['fps'] = 12
        result['playbackDerivation'] = {'sourceDurationMs': source_durations,
                                       'publishedFPS': 12, 'sourceRecordPreserved': True}
        for frame in result['frames']:
            frame['durationMs'] = 1000 / 12
        prefix = f'skill-evals/{folder}'
        frames = []
        for frame in result['frames']:
            frames.append({key: frame[key] for key in ('id', 'size', 'anchor', 'durationMs')})
            frames[-1]['image'] = copy(result_path.parent / frame['image'], f"{prefix}/{frame['image']}")
        metadata_path = f'{prefix}/result.json'
        (PUBLIC / metadata_path).write_text(json.dumps(result, indent=2) + '\n')
        animations.append({
            'id': folder, 'name': title, 'note': note, 'frames': frames,
            'fps': 12,
            'cellSize': result['cellSize'], 'groundAnchorAlignment': result['groundAnchorAlignment'],
            'sheet': copy(result_path.parent / 'sheet.png', f'{prefix}/sheet.png'),
            'metadata': metadata_path,
            'guide': copy(trial / 'guide.png', f'{prefix}/guide.png'),
            'source': copy(trial / 'source.png', f'{prefix}/source.png'),
            'recipe': copy(trial / 'generation.json', f'{prefix}/generation.json'),
        })
    (PUBLIC / 'skill-gallery.json').write_text(json.dumps({
        'version': 1, 'floor': floor, 'animations': animations,
    }, indent=2) + '\n')
    print('Published lava tile and two six-frame dance trials to the playground.')


if __name__ == '__main__':
    main()
