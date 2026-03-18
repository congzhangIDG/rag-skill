from __future__ import annotations

import re
from html import unescape
from typing import Optional, Tuple

import requests
import trafilatura

from rag.ingestion.base import BaseIngester, IngestedDocument


class WebIngester(BaseIngester):
  _userAgent = "Mozilla/5.0 (compatible; RAGBot/1.0)"
  _timeoutSeconds = 30

  def canHandle(self, source: str) -> bool:
    lowerSource = source.lower()
    if not (lowerSource.startswith("http://") or lowerSource.startswith("https://")):
      return False
    if "youtube.com" in lowerSource or "youtu.be" in lowerSource:
      return False
    return True

  def ingest(self, source: str) -> IngestedDocument:
    html, contentBytes = self._fetchHtml(source)

    titleFromMetadata: Optional[str] = None
    text: Optional[str] = None

    extractedWithMetadata = self._extractWithMetadata(html, url=source)
    if extractedWithMetadata:
      titleFromMetadata, textFromMetadata = self._parseTrafilaturaWithMetadata(extractedWithMetadata)
      if textFromMetadata.strip():
        text = textFromMetadata.strip()

    if text is None:
      extracted = trafilatura.extract(html, url=source)
      if extracted and extracted.strip():
        text = extracted.strip()

    if text is None:
      text = self._stripHtmlToText(html)

    title = (
      (titleFromMetadata.strip() if titleFromMetadata else "")
      or self._extractTitleFromHtml(html)
      or source
    )

    return IngestedDocument(
      text=text,
      title=title,
      source_type="web",
      source_uri=source,
      content_bytes=contentBytes,
    )

  def _fetchHtml(self, source: str) -> Tuple[str, bytes]:
    html = trafilatura.fetch_url(source)
    if html:
      return html, html.encode("utf-8", errors="replace")

    headers = {
      "User-Agent": self._userAgent,
    }
    resp = requests.get(source, headers=headers, timeout=self._timeoutSeconds)
    resp.raise_for_status()
    return resp.text, resp.content

  def _extractWithMetadata(self, html: str, url: str) -> Optional[str]:
    try:
      return trafilatura.extract(html, url=url, with_metadata=True)
    except TypeError:
      try:
        return trafilatura.extract(html, url=url, include_metadata=True)
      except TypeError:
        return None

  def _parseTrafilaturaWithMetadata(self, extracted: str) -> Tuple[Optional[str], str]:
    if not extracted.startswith("---"):
      return None, extracted

    lines = extracted.splitlines()
    if not lines or lines[0].strip() != "---":
      return None, extracted

    secondDelimiterIndex: Optional[int] = None
    for i in range(1, len(lines)):
      if lines[i].strip() == "---":
        secondDelimiterIndex = i
        break

    if secondDelimiterIndex is None:
      return None, extracted

    title: Optional[str] = None
    for line in lines[1:secondDelimiterIndex]:
      match = re.match(r"^\s*title\s*:\s*(.+?)\s*$", line, flags=re.IGNORECASE)
      if match:
        title = match.group(1).strip().strip('"').strip("'")
        break

    body = "\n".join(lines[secondDelimiterIndex + 1:]).strip()
    return title, body

  def _extractTitleFromHtml(self, html: str) -> Optional[str]:
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
    cleaned = re.sub(r"(?is)<head\b[^>]*>.*?</head>", " ", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
