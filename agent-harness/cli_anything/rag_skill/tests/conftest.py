from __future__ import annotations

import os
import sys


def _ensureHarnessOnPath() -> None:
  here = os.path.abspath(os.path.dirname(__file__))
  harnessRoot = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
  if harnessRoot not in sys.path:
    sys.path.insert(0, harnessRoot)


_ensureHarnessOnPath()
