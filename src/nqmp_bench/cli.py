"""NQMP command-line interface.

Supports dataset generation, running predictions, and rendering reports.
"""

import argparse
import json
import os
from collections.abc import Callable
import datetime
import re

from .generator import GenConfig, generate_pairs
from .harness import RunConfig, run_dataset, _stable_item_id
from .report import render_report, load_jsonl, to_predictions
from .data import QAPair, QAItem


def _safe_name(s: str) -> str:
  """Make a filesystem-safe name from a model or client string."""
  if s is None:
    return 'unknown'
  return re.sub(r'[^A-Za-z0-9._-]+', '-', s)


def _timestamp() -> str:
  return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


def _pairs_to_jsonl(pairs: list[QAPair], path: str) -> None:
  """Write QAPairs to a JSONL file."""
  with open(path, 'w') as f:
    for p in pairs:
      for item in (p.left, p.right):
        f.write(
          json.dumps(
            {
              'pair_id': item.pair_id,
              'operator': item.operator,
              'domain': item.domain,
              'context': item.context,
              'question': item.question,
              'answer': item.answer,
              'answer_type': item.answer_type,
            }
          )
          + '\n'
        )


def _load_pairs(path: str) -> list[QAPair]:
  """Load QAPairs from a JSONL dataset file."""
  rows = []
  with open(path, 'r') as f:
    rows = [json.loads(line) for line in f if line.strip()]
  by_id = {}
  for r in rows:
    by_id.setdefault(r['pair_id'], []).append(r)
  pairs: list[QAPair] = []
  for pid, items in by_id.items():
    left, right = items[0], items[1]
    left_item = QAItem(
      pair_id=pid,
      operator=left['operator'],
      domain=left['domain'],
      context=left['context'],
      question=left['question'],
      answer=left['answer'],
      answer_type=left['answer_type'],
    )
    right_item = QAItem(
      pair_id=pid,
      operator=right['operator'],
      domain=right['domain'],
      context=right['context'],
      question=right['question'],
      answer=right['answer'],
      answer_type=right['answer_type'],
    )
    pairs.append(QAPair(id=pid, left=left_item, right=right_item))
  return pairs


def _load_skip_set(preds_path: str) -> set[str]:
  """Return a set of completed item_ids from predictions.jsonl."""
  done: set[str] = set()
  if os.path.exists(preds_path):
    rows = load_jsonl(preds_path)
    for r in rows:
      iid = r.get('item_id')
      if iid:
        done.add(iid)
      else:
        # Back-compat: derive from pair_id + question if item_id missing
        pid, q = r.get('pair_id'), r.get('question')
        if pid and q:
          done.add(_stable_item_id(pid, q))
  return done


def _make_pred_writer(
  path: str, append: bool
) -> tuple[Callable[[object], None], object]:
  """Open predictions.jsonl and return (writer, file_handle). Writer flushes each line."""
  mode = 'a' if append else 'w'
  fh = open(path, mode, encoding='utf-8')

  def _write(p) -> None:
    fh.write(json.dumps(p.__dict__) + '\n')
    fh.flush()  # ensure progress survives Ctrl-C
    os.fsync(fh.fileno())

  return _write, fh


def cmd_generate(args: argparse.Namespace) -> None:
  """CLI: generate dataset."""
  os.makedirs(args.out, exist_ok=True)
  pairs = generate_pairs(GenConfig(seed=args.seed, num_pairs=args.pairs))
  path = os.path.join(args.out, 'dataset.jsonl')
  _pairs_to_jsonl(pairs, path)
  print(f'Wrote {path}')


def cmd_run(args: argparse.Namespace) -> None:
  """CLI: run predictions over a dataset file with per-call logs and resume."""
  pairs = _load_pairs(args.infile)
  # automatic out dir if not provided
  if args.out is None:
    base = f'{_safe_name(args.client)}-{_safe_name(args.model)}-pairs{len(pairs)}-{_timestamp()}'
    args.out = os.path.join('results', base)
  os.makedirs(args.out, exist_ok=True)

  preds_path = os.path.join(args.out, 'predictions.jsonl')
  skip = _load_skip_set(preds_path) if args.resume else None

  writer, fh = _make_pred_writer(
    preds_path, append=(args.resume and os.path.exists(preds_path))
  )
  try:
    run_dataset(
      pairs,
      RunConfig(
        client_name=args.client,
        model_name=args.model,
        temperature=args.temperature,
        out_dir=args.out,
        resume=args.resume,
        verbose=(not args.quiet),
      ),
      resume_skip=skip,
      write_pred=writer,
    )
  finally:
    fh.close()

  # persist/merge run info
  run_info_path = os.path.join(args.out, 'run_info.json')
  info = {
    'client': args.client,
    'model': args.model or ('echo' if args.client == 'echo' else 'unknown'),
    'pairs': len(pairs),
    'seed': None,
    'timestamp': _timestamp(),
    'resumed': bool(args.resume),
  }
  try:
    if os.path.exists(run_info_path):
      with open(run_info_path, 'r') as rf:
        cur = json.load(rf)
      cur.update(info)
      info = cur
  except Exception:
    pass
  with open(run_info_path, 'w') as f:
    json.dump(info, f, indent=2)
  print(f'Wrote {preds_path}')


def cmd_report(args: argparse.Namespace) -> None:
  """CLI: aggregate metrics + render report from results folder."""
  preds_path = os.path.join(args.in_dir, 'predictions.jsonl')
  rows = load_jsonl(preds_path)
  preds = to_predictions(rows)
  # determine basename from run_info.json if present
  basename = 'report'
  run_info_path = os.path.join(args.in_dir, 'run_info.json')
  if os.path.exists(run_info_path):
    with open(run_info_path, 'r') as f:
      info = json.load(f)
    basename = f'{_safe_name(info.get("client", ""))}-{_safe_name(info.get("model", ""))}-pairs{info.get("pairs", "")}-{_timestamp()}'
  if args.out is None:
    args.out = args.in_dir
  render_report(preds, args.out, basename=basename)
  print(f'Wrote report to {args.out}')


def cmd_all(args: argparse.Namespace) -> None:
  """CLI: end-to-end run (generate -> run -> report) with auto naming, logs, and resume."""
  # auto out dir if not provided
  if args.out is None:
    base = f'{_safe_name(args.client)}-{_safe_name(args.model)}-pairs{args.pairs}-{_timestamp()}'
    args.out = os.path.join('results', base)
  os.makedirs(args.out, exist_ok=True)

  ds_path = os.path.join(args.out, 'dataset.jsonl')
  pr_path = os.path.join(args.out, 'predictions.jsonl')

  # Generate or reuse dataset
  if args.resume and os.path.exists(ds_path):
    pairs = _load_pairs(ds_path)
  else:
    pairs = generate_pairs(GenConfig(seed=args.seed, num_pairs=args.pairs))
    _pairs_to_jsonl(pairs, ds_path)

  # Resume skip set
  skip = _load_skip_set(pr_path) if args.resume else None

  writer, fh = _make_pred_writer(
    pr_path, append=(args.resume and os.path.exists(pr_path))
  )
  try:
    preds = run_dataset(
      pairs,
      RunConfig(
        client_name=args.client,
        model_name=args.model,
        temperature=args.temperature,
        out_dir=args.out,
        resume=args.resume,
        verbose=(not args.quiet),
      ),
      resume_skip=skip,
      write_pred=writer,
    )
  finally:
    fh.close()

  # Persist/merge run info
  run_info_path = os.path.join(args.out, 'run_info.json')
  info = {
    'client': args.client,
    'model': args.model or ('echo' if args.client == 'echo' else 'unknown'),
    'pairs': args.pairs,
    'seed': args.seed,
    'timestamp': _timestamp(),
    'resumed': bool(args.resume),
  }
  try:
    if os.path.exists(run_info_path):
      with open(run_info_path, 'r') as rf:
        cur = json.load(rf)
      cur.update(info)
      info = cur
  except Exception:
    pass
  with open(run_info_path, 'w') as f:
    json.dump(info, f, indent=2)

  # Report
  basename = f'{_safe_name(args.client)}-{_safe_name(args.model)}-pairs{args.pairs}-{_timestamp()}'
  render_report(preds, args.out, basename=basename)
  print(f'Artifacts written under {args.out}')


def main() -> None:
  """Entry point for nqmp CLI."""
  ap = argparse.ArgumentParser(
    prog='nqmp', description='NQMP tiny benchmark harness'
  )
  sub = ap.add_subparsers(dest='cmd', required=True)

  a = sub.add_parser('generate', help='Generate dataset')
  a.add_argument(
    '--pairs', type=int, default=100, help='Number of pairs to generate'
  )
  a.add_argument('--seed', type=int, default=42, help='RNG seed')
  a.add_argument('--out', type=str, required=True, help='Output directory')
  a.set_defaults(func=cmd_generate)

  r = sub.add_parser('run', help='Run predictions over dataset')
  r.add_argument(
    '--in', dest='infile', type=str, required=True, help='Dataset JSONL path'
  )
  r.add_argument(
    '--client',
    type=str,
    choices=['echo', 'openrouter', 'gemini'],
    default='echo',
    help='LLM client to use',
  )
  r.add_argument(
    '--model', type=str, default=None, help='Model name (OpenRouter)'
  )
  r.add_argument(
    '--temperature', type=float, default=0.0, help='Sampling temperature'
  )
  r.add_argument(
    '--out',
    type=str,
    default=None,
    help='Output directory (auto-named if omitted)',
  )
  r.add_argument(
    '--resume',
    action='store_true',
    help='Resume this run by skipping already-predicted items and appending to predictions.jsonl',
  )
  r.add_argument(
    '--quiet', action='store_true', help='Disable per-call stdout logs'
  )
  r.set_defaults(func=cmd_run)

  rp = sub.add_parser('report', help='Aggregate metrics & render report')
  rp.add_argument(
    '--in',
    dest='in_dir',
    type=str,
    required=True,
    help='Results directory containing predictions.jsonl',
  )
  rp.add_argument(
    '--out',
    type=str,
    default=None,
    help='Output directory (defaults to --in dir)',
  )
  rp.set_defaults(func=cmd_report)

  al = sub.add_parser('all', help='End-to-end: generate -> run -> report')
  al.add_argument(
    '--pairs', type=int, default=100, help='Number of pairs to generate'
  )
  al.add_argument('--seed', type=int, default=42, help='RNG seed')
  al.add_argument(
    '--client',
    type=str,
    choices=['echo', 'openrouter', 'gemini'],
    default='echo',
    help='LLM client to use',
  )
  al.add_argument(
    '--model', type=str, default=None, help='Model name (OpenRouter)'
  )
  al.add_argument(
    '--temperature', type=float, default=0.0, help='Sampling temperature'
  )
  al.add_argument(
    '--out',
    type=str,
    default=None,
    help='Output directory (auto-named if omitted)',
  )
  al.add_argument(
    '--resume',
    action='store_true',
    help='Resume this run if output dir exists (skip done items)',
  )
  al.add_argument(
    '--quiet', action='store_true', help='Disable per-call stdout logs'
  )
  al.set_defaults(func=cmd_all)

  args = ap.parse_args()
  args.func(args)
