from __future__ import annotations

import json
import sys
from typing import Any, Optional


def printJson(payload: Any) -> None:
  sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def printResult(payload: Any, as_json: bool) -> None:
  if as_json:
    printJson({
      "ok": True,
      "result": payload,
    })
    return
  if isinstance(payload, str):
    sys.stdout.write(payload + "\n")
    return
  printJson(payload)


def printError(message: str, as_json: bool, errorType: Optional[str] = None) -> None:
  if as_json:
    printJson({
      "ok": False,
      "error": {
        "message": message,
        "type": errorType or "Error",
      },
    })
    return
  sys.stderr.write(message + "\n")
