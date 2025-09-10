"""Grading utilities for NQMP.

Provides normalization helpers, correctness checks, and aggregate metrics.
"""

import json
from dataclasses import dataclass
from .data import Prediction

YES = {'yes', 'y', 'true', '1'}
NO = {'no', 'n', 'false', '0'}


def _normalize_boolean(s: str) -> str:
  """Normalize booleans to 'Yes'/'No'."""
  t = s.strip().lower()
  if t in YES:
    return 'Yes'
  if t in NO:
    return 'No'
  # Heuristic: if the answer contains 'yes' or 'no' tokens amidst chatter.
  return (
    'Yes' if 'yes' in t.split() else ('No' if 'no' in t.split() else s.strip())
  )


def _normalize_id_list(s: str) -> list[str]:
  """Normalize comma-separated id lists (order-insensitive, whitespace-agnostic)."""
  t = s.strip()
  if not t:
    return []
  parts = [p.strip() for p in t.split(',') if p.strip()]
  return sorted(parts)


def is_correct(answer_type: str, pred: str, gold: str) -> bool:
  """Return True if prediction matches gold under normalizers."""
  if answer_type == 'boolean':
    return _normalize_boolean(pred) == _normalize_boolean(gold)
  if answer_type == 'id_list':
    return _normalize_id_list(pred) == _normalize_id_list(gold)
  return pred.strip() == gold.strip()


@dataclass
class Metrics:
  """Aggregated metrics for the run."""

  item_accuracy: float
  pair_joint_accuracy: float
  by_operator: dict[str, dict[str, float]]


def aggregate(preds: list[Prediction]) -> Metrics:
  """Compute item-level accuracy, pair-level joint accuracy, and per-operator metrics."""
  total = len(preds)
  item_acc = sum(1 for p in preds if p.correct) / total if total else 0.0
  # Pair joint: both items in a pair must be correct
  by_pair: dict[str, list[bool]] = {}
  by_op: dict[str, list[bool]] = {}
  for p in preds:
    by_pair.setdefault(p.pair_id, []).append(p.correct)
    op = p.meta.get('operator', 'unknown')
    by_op.setdefault(op, []).append(p.correct)
  pair_joint = (
    sum(all(v) for v in by_pair.values()) / len(by_pair) if by_pair else 0.0
  )
  by_operator_metrics: dict[str, dict[str, float]] = {
    op: {'item_accuracy': sum(v) / len(v)} for op, v in by_op.items()
  }
  return Metrics(
    item_accuracy=item_acc,
    pair_joint_accuracy=pair_joint,
    by_operator=by_operator_metrics,
  )


def dump_metrics(metrics: Metrics, path: str) -> None:
  """Write metrics JSON to disk."""
  with open(path, 'w') as f:
    json.dump(
      {
        'item_accuracy': metrics.item_accuracy,
        'pair_joint_accuracy': metrics.pair_joint_accuracy,
        'by_operator': metrics.by_operator,
      },
      f,
      indent=2,
    )
