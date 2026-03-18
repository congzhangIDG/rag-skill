from __future__ import annotations

import os

from rag.ingestion.base import BaseIngester, IngestedDocument


def checkUnstructured() -> bool:
  try:
    import unstructured  # noqa: F401
    return True
  except ImportError:
    return False


class PdfIngester(BaseIngester):
  def canHandle(self, source: str) -> bool:
    return os.path.isfile(source) and source.lower().endswith(".pdf")

  def ingest(self, source: str) -> IngestedDocument:
    try:
      from unstructured.partition.pdf import partition_pdf
    except ImportError as e:
      raise ImportError("请安装 unstructured: pip install 'unstructured[all-docs]'") from e

    elements = partition_pdf(source)
    text = "\n\n".join(str(el) for el in elements)

    with open(source, "rb") as f:
      contentBytes = f.read()

    fileName = os.path.basename(source)
    name, _ = os.path.splitext(fileName)

    return IngestedDocument(
      text=text,
      title=name,
      source_type="pdf",
      source_uri=source,
      content_bytes=contentBytes,
    )


class DocxIngester(BaseIngester):
  def canHandle(self, source: str) -> bool:
    return os.path.isfile(source) and source.lower().endswith(".docx")

  def ingest(self, source: str) -> IngestedDocument:
    try:
      from unstructured.partition.docx import partition_docx
    except ImportError as e:
      raise ImportError("请安装 unstructured: pip install 'unstructured[all-docs]'") from e

    elements = partition_docx(source)
    text = "\n\n".join(str(el) for el in elements)

    with open(source, "rb") as f:
      contentBytes = f.read()

    fileName = os.path.basename(source)
    name, _ = os.path.splitext(fileName)

    return IngestedDocument(
      text=text,
      title=name,
      source_type="docx",
      source_uri=source,
      content_bytes=contentBytes,
    )


class XlsxIngester(BaseIngester):
  def canHandle(self, source: str) -> bool:
    return os.path.isfile(source) and source.lower().endswith(".xlsx")

  def ingest(self, source: str) -> IngestedDocument:
    try:
      from unstructured.partition.xlsx import partition_xlsx
    except ImportError as e:
      raise ImportError("请安装 unstructured: pip install 'unstructured[all-docs]'") from e

    elements = partition_xlsx(source)
    text = "\n\n".join(str(el) for el in elements)

    with open(source, "rb") as f:
      contentBytes = f.read()

    fileName = os.path.basename(source)
    name, _ = os.path.splitext(fileName)

    return IngestedDocument(
      text=text,
      title=name,
      source_type="xlsx",
      source_uri=source,
      content_bytes=contentBytes,
    )
