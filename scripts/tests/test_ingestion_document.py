from __future__ import annotations

import builtins
import os
import sys
import types
from unittest import mock

import pytest

from rag.ingestion.document import DocxIngester, PdfIngester, XlsxIngester, checkUnstructured


def _addUnstructuredModule(monkeypatch: pytest.MonkeyPatch) -> None:
  unstructuredModule = types.ModuleType("unstructured")
  monkeypatch.setitem(sys.modules, "unstructured", unstructuredModule)


def _removeUnstructuredModule(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.delitem(sys.modules, "unstructured", raising=False)


def _setPartitionFunction(
  monkeypatch: pytest.MonkeyPatch,
  modulePath: str,
  funcName: str,
  func,
) -> None:
  parts = modulePath.split(".")
  for i in range(1, len(parts) + 1):
    name = ".".join(parts[:i])
    if name not in sys.modules:
      monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
  monkeypatch.setattr(sys.modules[modulePath], funcName, func, raising=False)


def testPdfIngesterCanHandle(monkeypatch: pytest.MonkeyPatch) -> None:
  ingester = PdfIngester()
  monkeypatch.setattr(os.path, "isfile", lambda _: True)

  assert ingester.canHandle("a.pdf") is True
  assert ingester.canHandle("a.txt") is False


def testDocxIngesterCanHandle(monkeypatch: pytest.MonkeyPatch) -> None:
  ingester = DocxIngester()
  monkeypatch.setattr(os.path, "isfile", lambda _: True)

  assert ingester.canHandle("a.docx") is True
  assert ingester.canHandle("a.pdf") is False


def testXlsxIngesterCanHandle(monkeypatch: pytest.MonkeyPatch) -> None:
  ingester = XlsxIngester()
  monkeypatch.setattr(os.path, "isfile", lambda _: True)

  assert ingester.canHandle("a.xlsx") is True
  assert ingester.canHandle("a.pdf") is False


def testCheckUnstructuredAvailable(monkeypatch: pytest.MonkeyPatch) -> None:
  _addUnstructuredModule(monkeypatch)
  assert checkUnstructured() is True


def testCheckUnstructuredMissing(monkeypatch: pytest.MonkeyPatch) -> None:
  _removeUnstructuredModule(monkeypatch)
  assert checkUnstructured() is False


def testPdfIngest(monkeypatch: pytest.MonkeyPatch) -> None:
  _addUnstructuredModule(monkeypatch)

  def partitionPdf(source: str):
    assert source == "a/b/c.pdf"
    return ["e1", "e2"]

  _setPartitionFunction(monkeypatch, "unstructured.partition.pdf", "partition_pdf", partitionPdf)
  monkeypatch.setattr(os.path, "isfile", lambda _: True)

  m = mock.mock_open(read_data=b"PDF")
  monkeypatch.setattr(builtins, "open", m)

  doc = PdfIngester().ingest("a/b/c.pdf")
  assert doc.text == "e1\n\ne2"
  assert doc.title == "c"
  assert doc.source_type == "pdf"
  assert doc.source_uri == "a/b/c.pdf"
  assert doc.content_bytes == b"PDF"


def testDocxIngest(monkeypatch: pytest.MonkeyPatch) -> None:
  _addUnstructuredModule(monkeypatch)

  def partitionDocx(source: str):
    assert source == "a/b/c.docx"
    return ["d1"]

  _setPartitionFunction(monkeypatch, "unstructured.partition.docx", "partition_docx", partitionDocx)
  monkeypatch.setattr(os.path, "isfile", lambda _: True)

  m = mock.mock_open(read_data=b"DOCX")
  monkeypatch.setattr(builtins, "open", m)

  doc = DocxIngester().ingest("a/b/c.docx")
  assert doc.text == "d1"
  assert doc.title == "c"
  assert doc.source_type == "docx"
  assert doc.source_uri == "a/b/c.docx"
  assert doc.content_bytes == b"DOCX"


def testXlsxIngest(monkeypatch: pytest.MonkeyPatch) -> None:
  _addUnstructuredModule(monkeypatch)

  def partitionXlsx(source: str):
    assert source == "a/b/c.xlsx"
    return ["x1", "x2", "x3"]

  _setPartitionFunction(monkeypatch, "unstructured.partition.xlsx", "partition_xlsx", partitionXlsx)
  monkeypatch.setattr(os.path, "isfile", lambda _: True)

  m = mock.mock_open(read_data=b"XLSX")
  monkeypatch.setattr(builtins, "open", m)

  doc = XlsxIngester().ingest("a/b/c.xlsx")
  assert doc.text == "x1\n\nx2\n\nx3"
  assert doc.title == "c"
  assert doc.source_type == "xlsx"
  assert doc.source_uri == "a/b/c.xlsx"
  assert doc.content_bytes == b"XLSX"


@pytest.mark.parametrize(
  "ingester, modulePath",
  [
    (PdfIngester(), "unstructured.partition.pdf"),
    (DocxIngester(), "unstructured.partition.docx"),
    (XlsxIngester(), "unstructured.partition.xlsx"),
  ],
)
def testIngestRaisesWhenUnstructuredMissing(ingester, modulePath, monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.delitem(sys.modules, modulePath, raising=False)
  monkeypatch.delitem(sys.modules, "unstructured", raising=False)
  monkeypatch.setattr(os.path, "isfile", lambda _: True)

  with pytest.raises(ImportError) as exc:
    ingester.ingest("a/b/c")

  assert "pip install 'unstructured[all-docs]'" in str(exc.value)
