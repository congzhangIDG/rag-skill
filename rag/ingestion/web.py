from __future__ import annotations

import re
import urllib.request
from html import unescape
from typing import Optional

from rag.ingestion.base import BaseIngester, IngestedDocument


class WebIngester(BaseIngester):
  def canHandle(self, source: str) -> bool:
    lowerSource = source.lower()
    if not (lowerSource.startswith("http://") or lowerSource.startswith("https://")):
      return False
    if "youtube.com" in lowerSource or "youtu.be" in lowerSource:
      return False
    return True

  def ingest(self, source: str) -> IngestedDocument:
    contentBytes = self._fetch(source)
    html = contentBytes.decode("utf-8", errors="replace")

    title = self._extractTitle(html) or source
    text = self._stripHtmlToText(html)

    return IngestedDocument(
      text=text,
      title=title,
      source_type="web",
      source_uri=source,
      content_bytes=contentBytes,
    )

  def _fetch(self, url: str) -> bytes:
    req = urllib.request.Request(
      url,
      headers={
        "User-Agent": "Mozilla/5.0 (compatible; RAGBot/1.0)",
      },
      method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
      return resp.read()

  def _extractTitle(self, html: str) -> Optional[str]:
    match = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html)
    if not match:
      return None
    title = unescape(match.group(1))
    title = re.sub(r"\s+", " ", title).strip()
    return title or None

  def _stripHtmlToText(self, html: str) -> str:
    cleaned = re.sub(
      r"(?is)<(script|style|nav|header|footer)\b[^>]*>.*?</\1>",
      " ",
      html,
    )
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
