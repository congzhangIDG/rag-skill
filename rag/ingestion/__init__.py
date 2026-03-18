from __future__ import annotations

from typing import Dict

from rag.ingestion.base import BaseIngester, IngestedDocument
from rag.ingestion.code import CodeIngester, DirectoryIngester
from rag.ingestion.document import DocxIngester, PdfIngester, XlsxIngester
from rag.ingestion.text import TextIngester
from rag.ingestion.web import WebIngester


_INGESTER_REGISTRY: Dict[str, BaseIngester] = {
  "text": TextIngester(),
  "code": CodeIngester(),
  "pdf": PdfIngester(),
  "docx": DocxIngester(),
  "xlsx": XlsxIngester(),
  "web": WebIngester(),
}


def getIngester(source_type: str) -> BaseIngester:
  return _INGESTER_REGISTRY[source_type]


__all__ = [
  "IngestedDocument",
  "BaseIngester",
  "CodeIngester",
  "DirectoryIngester",
  "PdfIngester",
  "DocxIngester",
  "XlsxIngester",
  "TextIngester",
  "WebIngester",
  "getIngester",
]
