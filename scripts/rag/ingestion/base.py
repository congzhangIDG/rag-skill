from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class IngestedDocument:
  text: str
  title: str
  source_type: str
  source_uri: str
  content_bytes: bytes


class BaseIngester(ABC):
  @abstractmethod
  def ingest(self, source: str) -> IngestedDocument:
    raise NotImplementedError

  @abstractmethod
  def canHandle(self, source: str) -> bool:
    raise NotImplementedError
