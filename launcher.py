"""Entry point used by the packaged builds (PyInstaller) and by `python launcher.py`."""
from __future__ import annotations

import sys

from pasadhi.app.service import main

if __name__ == '__main__':
    sys.exit(main())
