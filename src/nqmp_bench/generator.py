"""
Robust NQMP pair generator: richer operators, trickier edge-cases, larger lists.

Key changes:
- Configurable list sizes via GenConfig(min_items, max_items)
- Multi-attribute tables (Color/Shape/Size/Hat/Height) to support complex predicates
- New minimal-pair families that target boundary conditions and scope/logic flips
- Deterministic under seed; still returns only boolean/id_list items
"""

import random
from dataclasses import dataclass
from collections.abc import Callable, Iterable, Sequence

from .data import QAPair, QAItem

# Type aliases for clarity
Row = dict[str, str]
RowPred = Callable[[Row], bool]

# -----------------------
# Config
# -----------------------


@dataclass
class GenConfig:
  """Configuration for dataset generation.

  seed: RNG seed for determinism
  num_pairs: number of pairs to emit
  min_items/max_items: inclusive range for context size
  boundary_bias: 0..1 — probability to snap thresholds to equality boundaries
  """

  seed: int = 42
  num_pairs: int = 100
  min_items: int = 6
  max_items: int = 14
  boundary_bias: float = 0.45


# -----------------------
# Helpers
# -----------------------


def _ids(prefix: str, n: int) -> list[str]:
  """Return list of identifiers like F1..Fn."""
  return [f'{prefix}{i}' for i in range(1, n + 1)]


def _fmt_table(rows: Sequence[Row], cols: Sequence[str]) -> str:
  """Format rows as fixed-order tiny table."""
  header = '  '.join(['ID', *cols])
  lines = [header]
  for r in rows:
    lines.append('  '.join([r['id'], *[str(r[c]) for c in cols]]))
  return '\n'.join(lines)


def _boolean(val: bool) -> str:
  return 'Yes' if val else 'No'


def _choice(rng: random.Random, p_true: float) -> bool:
  return rng.random() < p_true


# -----------------------
# World builders
# -----------------------

_COLORS: tuple[str, ...] = ('red', 'green', 'blue', 'yellow')
_SHAPES: tuple[str, ...] = ('round', 'square', 'triangle')
_SIZES: tuple[str, ...] = ('small', 'medium', 'large')
_INVENTORY_COLS: tuple[str, ...] = ('color', 'shape', 'size', 'hat', 'height')


def _build_inventory(
  rng: random.Random, n: int, id_prefix: str = 'X'
) -> tuple[str, list[Row]]:
  """Make a multi-attribute inventory world with Color/Shape/Size/Hat/Height."""
  rows: list[Row] = []
  for id_ in _ids(id_prefix, n):
    color = rng.choice(_COLORS)
    shape = rng.choice(_SHAPES)
    size = rng.choice(_SIZES)
    hat = 'yes' if _choice(rng, 0.5) else 'no'
    height = rng.randint(160, 195)  # cm
    rows.append(
      {
        'id': id_,
        'color': color,
        'shape': shape,
        'size': size,
        'hat': hat,
        'height': str(height),
      }
    )
  context = _fmt_table(rows, _INVENTORY_COLS)
  return context, rows


def _count(rows: Iterable[Row], pred: RowPred) -> int:
  return sum(1 for r in rows if pred(r))


def _ids_where(rows: Iterable[Row], pred: RowPred) -> list[str]:
  return [r['id'] for r in rows if pred(r)]


# -----------------------
# Generators (boolean)
# -----------------------


def gen_pair_majority_vs_half(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Compare majority vs half thresholds for a color predicate."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'M')
  red = _count(rows, lambda r: r['color'] == 'red')
  q1 = 'Are more than half of the items red?'
  a1 = _boolean(red * 2 > n)
  q2 = 'Are at least half of the items red?'
  a2 = _boolean(red * 2 >= n)
  left = QAItem(
    pair_id=pid,
    operator='majority/half',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='majority/half',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_more_vs_atleast_as_many(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Contrast strict `more` vs `at least as many` for two colors."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'C')
  rc = _count(rows, lambda r: r['color'] == 'red')
  gc = _count(rows, lambda r: r['color'] == 'green')
  q1 = 'Are there more red than green items?'
  a1 = _boolean(rc > gc)
  q2 = 'Are there at least as many red as green items?'
  a2 = _boolean(rc >= gc)
  left = QAItem(
    pair_id=pid,
    operator='more/atleast_as_many',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='more/atleast_as_many',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_even_vs_odd(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Test parity (even vs odd) of items matching a predicate."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'P')
  red = _count(rows, lambda r: r['color'] == 'red')
  q1 = 'Is the number of red items even?'
  a1 = _boolean(red % 2 == 0)
  q2 = 'Is the number of red items odd?'
  a2 = _boolean(red % 2 == 1)
  left = QAItem(
    pair_id=pid,
    operator='even/odd',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='even/odd',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_none_vs_notall(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Differentiate `none` vs `not all` for a color predicate."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'N')
  red = _count(rows, lambda r: r['color'] == 'red')
  q1 = 'Are none of the items red?'
  a1 = _boolean(red == 0)
  q2 = 'Are not all of the items red?'
  a2 = _boolean(red < n)
  left = QAItem(
    pair_id=pid,
    operator='none/notall',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='none/notall',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_between_inclusive_exclusive(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Inclusive vs exclusive numeric ranges for count-based questions."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'B')
  red = _count(rows, lambda r: r['color'] == 'red')
  lo = rng.randint(0, n // 2)
  hi = rng.randint(max(lo, 1), n)
  if _choice(rng, cfg.boundary_bias):
    if _choice(rng, 0.5):
      lo = red
    else:
      hi = red
  q1 = f'Are there between {lo} and {hi} red items (inclusive)?'
  a1 = _boolean(lo <= red <= hi)
  q2 = f'Are there between {lo} and {hi} red items (exclusive)?'
  a2 = _boolean(lo < red < hi)
  left = QAItem(
    pair_id=pid,
    operator='range_inclusive/exclusive',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='range_inclusive/exclusive',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_exactly_one_vs_atleast_one_joint(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Exactly-one vs at-least-one for a joint (AND) predicate."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'J')
  both = _count(rows, lambda r: r['color'] == 'red' and r['size'] == 'large')
  q1 = 'Is exactly one item both red and large?'
  a1 = _boolean(both == 1)
  q2 = 'Is at least one item both red and large?'
  a2 = _boolean(both >= 1)
  left = QAItem(
    pair_id=pid,
    operator='exactly1/atleast1',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='exactly1/atleast1',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_any_vs_all_subset(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Any vs all over a filtered subset (e.g., no hats)."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'H')
  subset = [r for r in rows if r['hat'] == 'no']
  heights = [int(r['height']) for r in subset]
  if not heights and rows:
    rows[0]['hat'] = 'no'
    subset = [rows[0]]
    ctx = _fmt_table(rows, _INVENTORY_COLS)  # refresh
    heights = [int(rows[0]['height'])]
  q1 = 'Is any person without a hat at least 180cm?'
  a1 = _boolean(any(h >= 180 for h in heights))
  q2 = 'Is every person without a hat at least 180cm?'
  a2 = _boolean(all(h >= 180 for h in heights))
  left = QAItem(
    pair_id=pid,
    operator='any/all_subset',
    domain='people',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='any/all_subset',
    domain='people',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


# -----------------------
# Generators (id_list)
# -----------------------


def gen_pair_and_or_filter_ids(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Return IDs matching conjunction vs disjunction of predicates."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'A')
  and_ids = _ids_where(
    rows, lambda r: r['color'] == 'red' and r['size'] == 'large'
  )
  or_ids = _ids_where(
    rows, lambda r: r['color'] == 'red' or r['size'] == 'large'
  )
  q1 = 'List ids that are red and large.'
  a1 = ','.join(and_ids)
  q2 = 'List ids that are red or large.'
  a2 = ','.join(or_ids)
  left = QAItem(
    pair_id=pid,
    operator='and/or',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='id_list',
  )
  right = QAItem(
    pair_id=pid,
    operator='and/or',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='id_list',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_unless_vs_or_ids(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """`A unless B` (A and not B) vs `A or B` (IDs)."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'U')
  unless_ids = _ids_where(
    rows, lambda r: r['color'] == 'red' and r['shape'] != 'round'
  )
  or_ids = _ids_where(
    rows, lambda r: r['color'] == 'red' or r['shape'] == 'round'
  )
  q1 = 'List ids that are red unless they are round.'
  a1 = ','.join(unless_ids)
  q2 = 'List ids that are red or round.'
  a2 = ','.join(or_ids)
  left = QAItem(
    pair_id=pid,
    operator='unless/or',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='id_list',
  )
  right = QAItem(
    pair_id=pid,
    operator='unless/or',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='id_list',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_demorgan_ids(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """De Morgan variant: `not A and not B` vs `not A or not B` (IDs)."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'D')
  and_ids = _ids_where(
    rows, lambda r: r['color'] != 'red' and r['size'] != 'large'
  )
  or_ids = _ids_where(
    rows, lambda r: (r['color'] != 'red') or (r['size'] != 'large')
  )
  q1 = 'List ids that are not red and not large.'
  a1 = ','.join(and_ids)
  q2 = 'List ids that are not red or not large.'
  a2 = ','.join(or_ids)
  left = QAItem(
    pair_id=pid,
    operator='demorgan_and/or',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='id_list',
  )
  right = QAItem(
    pair_id=pid,
    operator='demorgan_and/or',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='id_list',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_xor_vs_or_ids(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Exclusive-or vs inclusive-or selection over IDs."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ctx, rows = _build_inventory(rng, n, 'X')
  xor_ids = _ids_where(
    rows, lambda r: (r['color'] == 'red') ^ (r['size'] == 'large')
  )
  or_ids = _ids_where(
    rows, lambda r: (r['color'] == 'red') or (r['size'] == 'large')
  )
  q1 = 'List ids that are red or large but not both.'
  a1 = ','.join(xor_ids)
  q2 = 'List ids that are red or large.'
  a2 = ','.join(or_ids)
  left = QAItem(
    pair_id=pid,
    operator='xor/or',
    domain='inventory',
    context=ctx,
    question=q1,
    answer=a1,
    answer_type='id_list',
  )
  right = QAItem(
    pair_id=pid,
    operator='xor/or',
    domain='inventory',
    context=ctx,
    question=q2,
    answer=a2,
    answer_type='id_list',
  )
  return QAPair(id=pid, left=left, right=right)


# -----------------------
# Legacy/simple families (kept, upgraded to variable sizes)
# -----------------------


def gen_pair_fruits(rng: random.Random, pid: str, cfg: GenConfig) -> QAPair:
  """Simple threshold comparisons in a one-attribute world."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ids = _ids('F', n)
  colors = rng.choices(['red', 'green', 'yellow'], k=n)
  items = list(zip(ids, colors))
  context = 'ID  Value\n' + '\n'.join(f'{k}  {v}' for k, v in items)
  red_count = sum(1 for c in colors if c == 'red')
  k = 2
  if _choice(rng, cfg.boundary_bias):
    k = red_count
  q1 = f'Are there at least {k} red fruits?'
  a1 = _boolean(red_count >= k)
  q2 = f'Are there at most {k} red fruits?'
  a2 = _boolean(red_count <= k)
  left = QAItem(
    pair_id=pid,
    operator='atleast/atmost',
    domain='fruits',
    context=context,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='atleast/atmost',
    domain='fruits',
    context=context,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_ids_filter(rng: random.Random, pid: str, cfg: GenConfig) -> QAPair:
  """Negation over labeled IDs (ok vs not ok)."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ids = _ids('I', n)
  flags = [rng.choice([True, False]) for _ in ids]
  items = list(zip(ids, ['ok' if f else 'bad' for f in flags]))
  context = 'ID  Value\n' + '\n'.join(f'{k}  {v}' for k, v in items)
  pos_ids = [i for i, f in zip(ids, flags) if f]
  neg_ids = [i for i, f in zip(ids, flags) if not f]
  q1, a1 = 'List ids with value ok.', ','.join(pos_ids)
  q2, a2 = 'List ids that are not ok.', ','.join(neg_ids)
  left = QAItem(
    pair_id=pid,
    operator='negation',
    domain='flags',
    context=context,
    question=q1,
    answer=a1,
    answer_type='id_list',
  )
  right = QAItem(
    pair_id=pid,
    operator='negation',
    domain='flags',
    context=context,
    question=q2,
    answer=a2,
    answer_type='id_list',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_any_all(rng: random.Random, pid: str, cfg: GenConfig) -> QAPair:
  """Any vs all threshold comparisons over numeric heights."""
  n = rng.randint(max(4, cfg.min_items), max(5, cfg.max_items))
  ids = _ids('H', n)
  heights = [rng.randint(160, 185) for _ in ids]
  context = 'Heights(cm)\n' + '\n'.join(
    f'{k}  {v}' for k, v in zip(ids, heights)
  )
  thresh = 180
  if _choice(rng, cfg.boundary_bias):
    thresh = rng.choice([min(heights), max(heights)])
  q1 = f'Is any person at least {thresh}cm?'
  a1 = _boolean(any(h >= thresh for h in heights))
  q2 = f'Is everyone at least {thresh}cm?'
  a2 = _boolean(all(h >= thresh for h in heights))
  left = QAItem(
    pair_id=pid,
    operator='any/all',
    domain='heights',
    context=context,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='any/all',
    domain='heights',
    context=context,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


def gen_pair_exact_vs_atleast(
  rng: random.Random, pid: str, cfg: GenConfig
) -> QAPair:
  """Exactly-k vs at-least-k count comparisons."""
  n = rng.randint(cfg.min_items, cfg.max_items)
  ids = _ids('R', n)
  cats = rng.choices(['blue', 'red'], k=n)
  context = 'ID  Value\n' + '\n'.join(f'{k}  {v}' for k, v in zip(ids, cats))
  red_count = sum(c == 'red' for c in cats)
  k = 3
  if _choice(rng, cfg.boundary_bias):
    k = red_count
  q1 = f'Are there exactly {k} red items?'
  a1 = _boolean(red_count == k)
  q2 = f'Are there at least {k} red items?'
  a2 = _boolean(red_count >= k)
  left = QAItem(
    pair_id=pid,
    operator='exactly/atleast',
    domain='colors',
    context=context,
    question=q1,
    answer=a1,
    answer_type='boolean',
  )
  right = QAItem(
    pair_id=pid,
    operator='exactly/atleast',
    domain='colors',
    context=context,
    question=q2,
    answer=a2,
    answer_type='boolean',
  )
  return QAPair(id=pid, left=left, right=right)


# -----------------------
# Registry & entry point
# -----------------------

Generator = Callable[[random.Random, str, GenConfig], QAPair]

_GENERATORS: list[Generator] = [
  gen_pair_majority_vs_half,
  gen_pair_more_vs_atleast_as_many,
  gen_pair_even_vs_odd,
  gen_pair_none_vs_notall,
  gen_pair_between_inclusive_exclusive,
  gen_pair_exactly_one_vs_atleast_one_joint,
  gen_pair_any_vs_all_subset,
  gen_pair_and_or_filter_ids,
  gen_pair_unless_vs_or_ids,
  gen_pair_demorgan_ids,
  gen_pair_xor_vs_or_ids,
  gen_pair_fruits,
  gen_pair_ids_filter,
  gen_pair_any_all,
  gen_pair_exact_vs_atleast,
]


def generate_pairs(cfg: GenConfig) -> list[QAPair]:
  """Generate a list of QAPairs deterministically given a seed.

  We sample contexts with variable sizes, and pick generator families uniformly.
  """
  rng = random.Random(cfg.seed)
  pairs: list[QAPair] = []
  for i in range(cfg.num_pairs):
    pid = f'pair_{i:04d}'
    fn = rng.choice(_GENERATORS)
    pairs.append(fn(rng, pid, cfg))
  return pairs
