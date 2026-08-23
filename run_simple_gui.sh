#!/usr/bin/env bash
set -euo pipefail

MIDNIGHT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$MIDNIGHT_SCRIPT_DIR"

MIDNIGHT_PYTHON=""
if [[ -x "$MIDNIGHT_SCRIPT_DIR/.venv/bin/python" ]]; then
    MIDNIGHT_PYTHON="$MIDNIGHT_SCRIPT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    MIDNIGHT_PYTHON="$(command -v python3)"
fi

if [[ -z "$MIDNIGHT_PYTHON" ]]; then
    echo "ERROR: Python 3.10 or newer is not available." >&2
    exit 1
fi

if ! "$MIDNIGHT_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    echo "ERROR: Python 3.10 or newer is required." >&2
    exit 1
fi

if ! "$MIDNIGHT_PYTHON" -c "import tkinter, requests, nacl, pycardano, cbor2, trezorlib" >/dev/null 2>&1; then
    echo "ERROR: Required Python packages are missing." >&2
    echo "Run: $MIDNIGHT_PYTHON -m pip install -r cardano-claim/requirements_cardano.txt" >&2
    exit 1
fi

exec "$MIDNIGHT_PYTHON" simple_gui.py
