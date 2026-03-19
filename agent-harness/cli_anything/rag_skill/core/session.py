from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RagSession:
  config: Dict[str, Any]
  current_collection: str
  last_results: List[Any]
  history: List[str]
  store: Optional[Any] = None
