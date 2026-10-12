#!/usr/bin/env python3
"""Compatibility entrypoint for the self-contained tile generation skill."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/build-overlap-tiles/scripts'))
import json
import tile_tools
from tile_tools import *
from project_tiled import export_tiled


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'export-tiled':
        parser = argparse.ArgumentParser(description='Export a playground scene to Tiled')
        parser.add_argument('command')
        parser.add_argument('scene', type=Path)
        parser.add_argument('manifest', type=Path)
        parser.add_argument('output', type=Path)
        args = parser.parse_args()
        export_tiled(json.loads(args.scene.read_text()), json.loads(args.manifest.read_text()), args.output)
    else:
        tile_tools.main()


if __name__ == '__main__':
    main()
