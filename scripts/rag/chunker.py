from __future__ import annotations

from collections import namedtuple
import os
import re
from typing import List, Optional, Tuple


ChunkSpan = namedtuple("ChunkSpan", ["text", "char_start", "char_end"])


DEFAULT_SEPARATORS = [
  "\n\n",
  "\n",
  "。",
  "？",
  "！",
  ".",
  "?",
  "!",
  "，",
  ",",
  " ",
  "",
]


def detectLanguage(file_path: str) -> str:
  _, ext = os.path.splitext(file_path)
  ext = ext.lower()

  mapping = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".cs": "csharp",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rs": "rust",
    ".md": "markdown",
  }
  return mapping.get(ext, "text")


def splitTextChunks(
  text: str,
  chunk_size: int = 600,
  overlap: int = 100,
  separators: Optional[List[str]] = None,
) -> List[ChunkSpan]:
  if chunk_size <= 0:
    raise ValueError("chunk_size must be > 0")
  if overlap < 0:
    raise ValueError("overlap must be >= 0")
  if separators is None:
    separators = list(DEFAULT_SEPARATORS)

  if not text:
    return []

  segments = _recursiveSplitToSpans(text, 0, len(text), separators, 0, chunk_size)
  step_limit = chunk_size if overlap <= 0 else max(1, chunk_size - overlap)
  normalized = _normalizeSpansToMaxLen(segments, step_limit)
  base_chunks = _mergeSpansToBaseChunks(text, normalized, first_limit=chunk_size, next_limit=step_limit)
  overlapped = _applyOverlapByPrevEnd(base_chunks, overlap)
  return _spansToChunkSpans(text, overlapped)


def splitCodeChunks(
  text: str,
  language: str,
  chunk_size: int = 600,
  overlap: int = 100,
) -> List[ChunkSpan]:
  if not text:
    return []
  if chunk_size <= 0:
    raise ValueError("chunk_size must be > 0")
  if overlap < 0:
    raise ValueError("overlap must be >= 0")

  pattern = _getTopLevelBoundaryPattern(language)
  if pattern is None:
    return splitTextChunks(text, chunk_size=chunk_size, overlap=overlap)

  raw_starts = [m.start() for m in re.finditer(pattern, text, re.MULTILINE)]
  if not raw_starts:
    return splitTextChunks(text, chunk_size=chunk_size, overlap=overlap)

  raw_starts = sorted(set(raw_starts))

  starts: List[int] = []
  for i, s in enumerate(raw_starts):
    min_start = 0 if i == 0 else raw_starts[i - 1]
    starts.append(_extendStartWithLeadingComments(text, s, min_start=min_start))

  blocks: List[Tuple[int, int]] = []
  for i, s in enumerate(starts):
    raw_next = raw_starts[i + 1] if i + 1 < len(raw_starts) else len(text)
    if s < raw_next:
      blocks.append((s, raw_next))

  final_spans: List[Tuple[int, int]] = []
  for (s, e) in blocks:
    if e - s <= chunk_size:
      final_spans.append((s, e))
      continue
    final_spans.extend(_splitLargeBlockByLines(text, s, e, chunk_size, overlap))

  return _spansToChunkSpans(text, _filterNonEmptySpans(text, final_spans))


def _getTopLevelBoundaryPattern(language: str) -> Optional[str]:
  lang = (language or "").lower()
  if lang == "python":
    return r"^(?:def |class |async def )"
  if lang in ("javascript", "typescript"):
    return r"^(?:export\s+)?(?:async\s+)?function\s+|^class\s+|^export\s+|^const\s+\w+\s*="
  if lang == "go":
    return r"^(?:func |type )"
  if lang in ("java", "csharp", "kotlin"):
    return r"^(?:public |private |protected |class |interface )"
  if lang == "rust":
    return r"^(?:fn |impl |struct |enum )"
  return None


def _recursiveSplitToSpans(
  text: str,
  start: int,
  end: int,
  separators: List[str],
  sep_index: int,
  chunk_size: int,
) -> List[Tuple[int, int]]:
  if end <= start:
    return []

  if sep_index >= len(separators):
    return _forceSliceToSpans(start, end, chunk_size)

  sep = separators[sep_index]
  if sep == "":
    return _forceSliceToSpans(start, end, chunk_size)

  pieces = _splitRangeBySeparator(text, start, end, sep)
  if len(pieces) == 1:
    return _recursiveSplitToSpans(text, start, end, separators, sep_index + 1, chunk_size)

  spans: List[Tuple[int, int]] = []
  for (ps, pe) in pieces:
    if pe - ps > chunk_size:
      spans.extend(_recursiveSplitToSpans(text, ps, pe, separators, sep_index + 1, chunk_size))
    else:
      spans.append((ps, pe))
  return spans


def _splitRangeBySeparator(text: str, start: int, end: int, sep: str) -> List[Tuple[int, int]]:
  spans: List[Tuple[int, int]] = []
  i = start
  while True:
    j = text.find(sep, i, end)
    if j == -1:
      break
    piece_end = j + len(sep)
    spans.append((i, piece_end))
    i = piece_end
  spans.append((i, end))
  return spans


def _forceSliceToSpans(start: int, end: int, chunk_size: int) -> List[Tuple[int, int]]:
  spans: List[Tuple[int, int]] = []
  i = start
  while i < end:
    j = min(i + chunk_size, end)
    spans.append((i, j))
    i = j
  return spans


def _normalizeSpansToMaxLen(spans: List[Tuple[int, int]], max_len: int) -> List[Tuple[int, int]]:
  out: List[Tuple[int, int]] = []
  for (s, e) in spans:
    if e <= s:
      continue
    if e - s <= max_len:
      out.append((s, e))
      continue
    out.extend(_forceSliceToSpans(s, e, max_len))
  return out


def _mergeSpansToBaseChunks(
  text: str,
  spans: List[Tuple[int, int]],
  first_limit: int,
  next_limit: int,
) -> List[Tuple[int, int]]:
  spans = [(s, e) for (s, e) in spans if e > s]
  if not spans:
    return []

  chunks: List[Tuple[int, int]] = []
  current_start: Optional[int] = None
  current_end: Optional[int] = None
  limit = first_limit

  def flush():
    nonlocal current_start, current_end, limit
    if current_start is None or current_end is None:
      return
    if text[current_start:current_end].strip():
      chunks.append((current_start, current_end))
    current_start = None
    current_end = None
    limit = next_limit

  for (s, e) in spans:
    if current_start is None:
      current_start = s
      current_end = e
      continue

    if (e - current_start) > limit:
      flush()
      current_start = s
      current_end = e
      continue

    current_end = e

  flush()
  return _filterNonEmptySpans(text, chunks)


def _applyOverlapByPrevEnd(chunks: List[Tuple[int, int]], overlap: int) -> List[Tuple[int, int]]:
  if overlap <= 0 or len(chunks) <= 1:
    return chunks

  out: List[Tuple[int, int]] = [chunks[0]]
  for i in range(1, len(chunks)):
    prev_end = chunks[i - 1][1]
    s, e = chunks[i]
    out.append((max(0, prev_end - overlap), e))
  return out


def _splitLargeBlockByLines(
  text: str,
  start: int,
  end: int,
  chunk_size: int,
  overlap: int,
) -> List[Tuple[int, int]]:
  line_spans: List[Tuple[int, int]] = []
  i = start
  while i < end:
    j = text.find("\n", i, end)
    if j == -1:
      line_spans.append((i, end))
      break
    line_spans.append((i, j + 1))
    i = j + 1

  normalized: List[Tuple[int, int]] = []
  for (s, e) in line_spans:
    if e - s <= chunk_size:
      normalized.append((s, e))
    else:
      normalized.extend(_forceSliceToSpans(s, e, chunk_size))

  step_limit = chunk_size if overlap <= 0 else max(1, chunk_size - overlap)
  normalized = _normalizeSpansToMaxLen(normalized, step_limit)
  base_chunks = _mergeSpansToBaseChunks(text, normalized, first_limit=chunk_size, next_limit=step_limit)
  return _applyOverlapByPrevEnd(base_chunks, overlap)


def _extendStartWithLeadingComments(text: str, start: int, min_start: int = 0) -> int:
  if start <= min_start:
    return start

  line_start = text.rfind("\n", min_start, start)
  line_start = min_start if line_start == -1 else line_start + 1

  line_starts: List[int] = []
  p = min_start
  while True:
    n = text.find("\n", p, start)
    line_starts.append(p)
    if n == -1:
      break
    p = n + 1

  i = len(line_starts) - 1
  while i - 1 >= 0:
    prev_line_start = line_starts[i - 1]
    prev_line_end = text.find("\n", prev_line_start, start)
    if prev_line_end == -1:
      prev_line_end = start
    line = text[prev_line_start:prev_line_end]
    stripped = line.strip()
    if stripped == "":
      i -= 1
      continue
    if stripped.startswith("#"):
      i -= 1
      continue
    if stripped.startswith("//"):
      i -= 1
      continue
    if stripped.startswith("/*") or stripped.startswith("*") or stripped.endswith("*/"):
      i -= 1
      continue
    if stripped.startswith('"""') or stripped.startswith("'''"):
      i -= 1
      continue
    break

  return line_starts[i]


def _filterNonEmptySpans(text: str, spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
  filtered: List[Tuple[int, int]] = []
  for (s, e) in spans:
    if e <= s:
      continue
    if text[s:e].strip() == "":
      continue
    filtered.append((s, e))
  return filtered


def _spansToChunkSpans(text: str, spans: List[Tuple[int, int]]) -> List[ChunkSpan]:
  out: List[ChunkSpan] = []
  for (s, e) in spans:
    if e <= s:
      continue
    chunk_text = text[s:e]
    if chunk_text.strip() == "":
      continue
    out.append(ChunkSpan(chunk_text, s, e))
  return out
