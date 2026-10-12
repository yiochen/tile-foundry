#!/usr/bin/env python3
"""Compatibility entrypoint for the self-contained tile generation skill."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/build-overlap-tiles/scripts'))
from guide_tools import *

if __name__ == "__main__":
    main()
