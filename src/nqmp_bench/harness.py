"""Benchmark harness for running datasets through LLM clients.

Handles prompting, per-item logging, resume, and JSONL persistence.
"""

import json
import os
import sys
import time
import hashlib
from dataclasses import dataclass, field
from collections.abc import Callable, Iterable
from typing import Any

from .data import QAPair, Prediction, QAItem
from .grader import is_correct
from .client import BaseClient, OpenRouterClient, EchoClient

PROMPT_TEMPLATE = """You will be given a tiny context and a question.
- If the question is yes/no, answer exactly 'Yes' or 'No'.
- If the question asks to list ids, return a comma-separated list of ids with no spaces.
- Do not add any extra text.

CONTEXT:
{context}

QUESTION:
{question}
"""


@dataclass
class RunConfig:
  """Configuration for running a dataset against a client."""

  client_name: str = 'echo'
  model_name: str | None = None
  temperature: float = 0.0
  out_dir: str | None = None
  resume: bool = False
  verbose: bool = True


@dataclass(slots=True)
class RunLogger:
  """Tee logger that writes JSON lines to a file and prints pretty console lines."""

  path: str | None
  enabled: bool = True
  stdout_format: str = 'auto'  # "auto" | "json" | "pretty"
  max_question: int = 96
  _fh: Any | None = field(init=False, default=None)
  _t0: float = field(init=False, default_factory=time.time)
  _line_no: int = field(init=False, default=0)
  _use_color: bool = field(init=False, default=False)
  _use_pretty: bool = field(init=False, default=False)

  def __post_init__(self) -> None:
    """Initialize sinks and console mode."""
    if self.enabled and self.path:
      self._fh = open(self.path, 'a', encoding='utf-8')

    # Decide console formatting
    if self.stdout_format == 'pretty':
      self._use_pretty = True
    elif self.stdout_format == 'json':
      self._use_pretty = False
    else:  # auto
      self._use_pretty = sys.stdout.isatty()

    # Decide color usage
    self._use_color = (
      self._use_pretty
      and sys.stdout.isatty()
      and os.environ.get('NO_COLOR') is None
      and os.environ.get('TERM') not in {'dumb', None}
    )

  # ---------- Public API ----------

  def log(self, record: dict[str, Any]) -> None:
    """Emit one record to console (pretty or JSON) and to file as JSONL."""
    if not self.enabled:
      return

    # Always write machine JSONL to file first.
    line_json = json.dumps(record, ensure_ascii=False)
    if self._fh:
      self._fh.write(line_json + '\n')
      self._fh.flush()

    # Then print to console in chosen format.
    if self._use_pretty:
      print(self._format_pretty_line(record))
    else:
      print(line_json)

    sys.stdout.flush()

  def close(self) -> None:
    """Close file handle if open."""
    if self._fh:
      self._fh.close()

  # ---------- Pretty formatting ----------

  def _format_pretty_line(self, r: dict[str, Any]) -> str:
    """Render a compact, emoji-rich one-liner for humans."""
    self._line_no += 1
    t_rel = self._style(self._since_start(), 'grey')
    n = self._style(f'{self._line_no:04d}', 'grey')

    event = r.get('event', 'info')
    if event == 'llm_call':
      return self._fmt_llm_call(n, t_rel, r)
    if event == 'llm_error':
      return self._fmt_llm_error(n, t_rel, r)
    if event == 'skip':
      return self._fmt_skip(n, t_rel, r)
    if event == 'interrupt':
      return self._fmt_interrupt(n, t_rel, r)
    return self._fmt_info(n, t_rel, r)

  def _fmt_llm_call(self, n: str, t: str, r: dict[str, Any]) -> str:
    """Pretty print for successful LLM call events."""
    ok = bool(r.get('correct'))
    check = '✅' if ok else '❌'
    check = self._style(check, 'green' if ok else 'red', bold=True)

    model = r.get('model') or 'echo'
    client = r.get('client') or 'client'
    latency = r.get('latency_s')
    attempts = r.get('attempts', 1)
    domain = r.get('domain', '-')
    operator = r.get('operator', '-')
    pair_id = r.get('pair_id', '-')

    q = r.get('question', '')
    q = self._clip(q, self.max_question)

    gold = str(r.get('gold', ''))
    pred = str(r.get('prediction', ''))
    atype = r.get('answer_type', '-')

    parts = [
      f'{n} {t} 🤖 {check}',
      f'⏱ {latency:.3f}s' if isinstance(latency, (int, float)) else '⏱ —',
      f'🧠 {model}',
      f'🔌 {client}',
      f'🪪 {pair_id}',
      f'🌱 {domain} · 🔁 {operator}',
      f'❓ “{q}”',
      f'→ {self._style(pred, "cyan", bold=True)}',
      f'(gold {self._style(gold, "magenta")}, {atype})',
      f'🔄x{attempts}' if attempts and attempts != 1 else '',
    ]
    return '  '.join(p for p in parts if p)

  def _fmt_llm_error(self, n: str, t: str, r: dict[str, Any]) -> str:
    """Pretty print for LLM error events."""
    err = r.get('error', 'unknown error')
    model = r.get('model', '-')
    client = r.get('client', '-')
    q = self._clip(r.get('question', ''), self.max_question)
    pair_id = r.get('pair_id', '-')
    domain = r.get('domain', '-')
    operator = r.get('operator', '-')

    return '  '.join(
      [
        f'{n} {t} 💥 {self._style("ERROR", "red", bold=True)}',
        f'🧠 {model}',
        f'🔌 {client}',
        f'🪪 {pair_id}',
        f'🌱 {domain} · 🔁 {operator}',
        f'❓ “{q}”',
        f'→ {self._style(err, "red")}',
      ]
    )

  def _fmt_skip(self, n: str, t: str, r: dict[str, Any]) -> str:
    """Pretty print for skip events."""
    item_id = r.get('item_id', '-')
    q = self._clip(r.get('question', ''), self.max_question)
    return f'{n} {t} ⏭️  Skipped {self._style(item_id, "yellow")}  ❓ “{q}”'

  def _fmt_interrupt(self, n: str, t: str, r: dict[str, Any]) -> str:
    """Pretty print for interrupts."""
    q = self._clip(r.get('question', ''), self.max_question)
    return f'{n} {t} 🛑  KeyboardInterrupt  ❓ “{q}”'

  def _fmt_info(self, n: str, t: str, r: dict[str, Any]) -> str:
    """Fallback pretty print for miscellaneous events."""
    return f'{n} {t} ℹ️  {json.dumps(r, ensure_ascii=False)}'

  # ---------- Small helpers ----------

  def _since_start(self) -> str:
    """Format elapsed time since logger start."""
    dt = time.time() - self._t0
    if dt < 60:
      return f'+{dt:05.2f}s'
    m, s = divmod(int(dt), 60)
    return f'+{m:02d}m{s:02d}s'

  def _clip(self, text: str, width: int) -> str:
    """Truncate a long string with an ellipsis."""
    return text if len(text) <= width else text[: max(0, width - 1)] + '…'

  def _style(self, s: str, color: str, bold: bool = False) -> str:
    """Apply ANSI color/bold if enabled."""
    if not self._use_color:
      return s
    codes = {
      'grey': '90',
      'red': '31',
      'green': '32',
      'yellow': '33',
      'blue': '34',
      'magenta': '35',
      'cyan': '36',
      'white': '37',
    }
    parts = []
    if bold:
      parts.append('1')
    c = codes.get(color)
    if c:
      parts.append(c)
    if not parts:
      return s
    return f'\033[{";".join(parts)}m{s}\033[0m'


def _stable_item_id(pair_id: str, question: str) -> str:
  """Deterministic id for an item across runs."""
  raw = f'{pair_id}|{question}'.encode('utf-8')
  return hashlib.sha1(raw).hexdigest()[:16]


def _client_from_name(name: str) -> BaseClient:
  """Instantiate client by name."""
  if name == 'openrouter':
    return OpenRouterClient()
  if name == 'echo':
    return EchoClient(seed=0)
  raise ValueError(f'Unknown client: {name}')


def _eval_item(
  client: BaseClient,
  item: QAItem,
  model_name: str | None,
  temperature: float,
  logger: RunLogger,
  client_name: str,
) -> Prediction:
  """Query client and grade a single item and emit a structured log."""
  prompt = PROMPT_TEMPLATE.format(context=item.context, question=item.question)
  t0 = time.time()
  resp = client.predict(prompt, model=model_name, temperature=temperature)
  dt = time.time() - t0
  correct = is_correct(item.answer_type, resp.text, item.answer)
  rec = {
    'event': 'llm_call',
    'pair_id': item.pair_id,
    'operator': item.operator,
    'domain': item.domain,
    'question': item.question,
    'gold': item.answer,
    'prediction': resp.text,
    'answer_type': item.answer_type,
    'correct': correct,
    'latency_s': round(dt, 3),
    'client': client_name,
    'model': (model_name or 'echo'),
    'attempts': getattr(resp, 'attempts', 1),
    'status_code': getattr(resp, 'status_code', None),
  }
  logger.log(rec)
  return Prediction(
    pair_id=item.pair_id,
    item_id=_stable_item_id(item.pair_id, item.question),
    question=item.question,
    prediction=resp.text,
    gold=item.answer,
    answer_type=item.answer_type,
    correct=correct,
    meta={'operator': item.operator, 'domain': item.domain},
  )


def run_dataset(
  pairs: Iterable[QAPair],
  cfg: RunConfig,
  resume_skip: set[str] | None = None,
  write_pred: Callable[[Prediction], None] | None = None,
) -> list[Prediction]:
  """Run all items; write each prediction immediately; continue on per-item errors.

  Args:
    resume_skip: set of item_ids already completed (skip these).
    write_pred: callback to persist each Prediction (e.g., append JSONL + flush).
  """
  client = _client_from_name(cfg.client_name)
  logger = RunLogger(
    os.path.join(cfg.out_dir, 'run.log') if cfg.out_dir else None,
    enabled=cfg.verbose,
  )
  preds: list[Prediction] = []
  try:
    for pair in pairs:
      for item in (pair.left, pair.right):
        item_id = _stable_item_id(item.pair_id, item.question)
        if resume_skip and item_id in resume_skip:
          logger.log(
            {
              'event': 'skip',
              'pair_id': item.pair_id,
              'question': item.question,
              'item_id': item_id,
            }
          )
          continue
        try:
          p = _eval_item(
            client,
            item,
            cfg.model_name,
            cfg.temperature,
            logger,
            cfg.client_name,
          )
          preds.append(p)
          if write_pred:
            write_pred(p)  # persist immediately
        except KeyboardInterrupt:
          logger.log(
            {
              'event': 'interrupt',
              'pair_id': item.pair_id,
              'question': item.question,
            }
          )
          raise
        except Exception as e:
          # Log error and proceed
          logger.log(
            {
              'event': 'llm_error',
              'pair_id': item.pair_id,
              'operator': item.operator,
              'domain': item.domain,
              'question': item.question,
              'error': str(e),
              'client': cfg.client_name,
              'model': (cfg.model_name or 'echo'),
            }
          )
          continue
  finally:
    logger.close()
  return preds


def dump_jsonl(path: str, rows: Iterable[dict]) -> None:
  """Write JSONL to a file."""
  with open(path, 'w') as f:
    for r in rows:
      f.write(json.dumps(r) + '\n')
