"""Core data structures for NQMP.

Defines the schema for QA items, pairs, and model predictions.
"""

from dataclasses import dataclass, field
from typing import Literal

AnswerType = Literal['boolean', 'id_list']


@dataclass
class QAItem:
  """Single QA item with context and gold."""

  pair_id: str
  operator: str
  domain: str
  context: str
  question: str
  answer: str
  answer_type: AnswerType
  meta: dict[str, str] = field(default_factory=dict)


@dataclass
class QAPair:
  """Two minimally different items forming a pair."""

  id: str
  left: QAItem
  right: QAItem


@dataclass
class Prediction:
  """Model prediction record."""

  pair_id: str
  item_id: str
  question: str
  prediction: str
  gold: str
  answer_type: AnswerType
  correct: bool
  meta: dict[str, str] = field(default_factory=dict)
