from __future__ import annotations

import os
import re

from rag.ingestion.base import BaseIngester, IngestedDocument


class TextIngester(BaseIngester):
  def canHandle(self, source: str) -> bool:
    ext = os.path.splitext(source)[1].lower()
    return ext in {".md", ".txt", ".rst"}

  def ingest(self, source: str) -> IngestedDocument:
    with open(source, "rb") as f:
      contentBytes = f.read()

    text = contentBytes.decode("utf-8", errors="replace")
    title = self._extractTitle(source, text)

    return IngestedDocument(
      text=text,
      title=title,
      source_type="text",
      source_uri=source,
      content_bytes=contentBytes,
    )

  def _extractTitle(self, source: str, text: str) -> str:
    ext = os.path.splitext(source)[1].lower()

    if ext == ".md":
      for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
          return match.group(1)

    fileName = os.path.basename(source)
    name, _ = os.path.splitext(fileName)
    return name
