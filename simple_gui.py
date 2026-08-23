#!/usr/bin/env python3
"""Application launcher for the Cardano NIGHT redemption GUI."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    repository_root = Path(__file__).resolve().parent
    cardano_claim_dir = repository_root / "cardano-claim"
    gui_path = cardano_claim_dir / "midnight_redeem_gui.py"
    if not gui_path.is_file():
        raise FileNotFoundError(f"Redemption GUI not found: {gui_path}")
    sys.path.insert(0, str(cardano_claim_dir))
    runpy.run_path(str(gui_path), run_name="__main__")


if __name__ == "__main__":
    main()
