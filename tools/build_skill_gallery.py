#!/usr/bin/env python3
"""Publish the latest recorded current-suite eval outcomes."""
from pathlib import Path
from build_eval_gallery import build_gallery

ROOT = Path(__file__).resolve().parents[1]


def main():
    result = build_gallery(ROOT/'assets/evals',ROOT/'skills/build-overlap-tiles/evals/cases.json',
                           ROOT/'public/assets',ROOT/'docs/evals')
    print(f"Published {len(result['cases'])} current eval cases; "
          f"{sum(c['latest'] is not None for c in result['cases'])} have recorded outcomes.")


if __name__ == '__main__':
    main()
