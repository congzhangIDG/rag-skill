from __future__ import annotations

from typing import Dict

from rag.ingestion.base import BaseIngester, IngestedDocument
from rag.ingestion.text import TextIngester


_INGESTER_REGISTRY: Dict[str, BaseIngester] = {
  "text": TextIngester(),
}


def getIngester(source_type: str) -> BaseIngester:
  return _INGESTER_REGISTRY[source_type]


__all__ = [
  "IngestedDocument",
  "BaseIngester",
  "TextIngester",
  "getIngester",
]
