#!/usr/bin/env python3
"""Self Atlas helper CLI."""

from __future__ import annotations

import sys

from self_atlas_lib.cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
