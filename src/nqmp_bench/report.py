"""Reporting and leaderboard utilities for NQMP.

Builds metrics, plots operator accuracies, and writes Markdown/HTML reports.
"""

import json
import os
import base64
from pathlib import Path
import re

import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate

from .data import Prediction
from .grader import Metrics, aggregate, dump_metrics


def load_jsonl(path: str) -> list[dict]:
  """Load JSONL from a file."""
  rows: list[dict] = []
  with open(path, 'r') as f:
    for line in f:
      if line.strip():
        rows.append(json.loads(line))
  return rows


def _repo_root() -> Path:
  """Infer the project root from this module location."""
  return Path(__file__).resolve().parents[2]


def _embed_image_base64(path: str) -> str:
  """Read an image file and return a `data:` URL with base64-encoded bytes."""
  with open(path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('ascii')
  ext = os.path.splitext(path)[1].lstrip('.') or 'png'
  return f'data:image/{ext};base64,{b64}'


def _update_leaderboard_readme(
  run: dict[str, str], metrics: Metrics, out_dir: str, basename: str
) -> None:
  """Append to leaderboard.csv and update README leaderboard section."""
  root = _repo_root()
  csv_path = root / 'leaderboard.csv'
  # Build GitHub links for artifacts
  # Assumes repo is hosted at GitHub under this URL and branch
  repo_http = 'https://github.com/sashsinha/nqmp-bench'
  branch = 'main'
  try:
    rel_dir = Path(out_dir).resolve().relative_to(root).as_posix()
  except Exception:
    rel_dir = Path(out_dir).as_posix()
  md_url = f"{repo_http}/blob/{branch}/{rel_dir}/report_{basename}.md"
  # For HTML, GitHub does not render .html in the blob view; use an htmlpreview link to the raw file
  raw_base = 'https://raw.githubusercontent.com/sashsinha/nqmp-bench'
  raw_html_url = f"{raw_base}/{branch}/{rel_dir}/report_{basename}.html"
  html_preview_url = f"https://htmlpreview.github.io/?{raw_html_url}"
  dir_url = f"{repo_http}/tree/{branch}/{rel_dir}"
  chart_url = f"{repo_http}/blob/{branch}/{rel_dir}/operator_accuracy_{basename}.png"
  # Append row
  row = {
    'timestamp': run.get('timestamp', ''),
    'client': run.get('client', ''),
    'model': run.get('model', ''),
    'pairs': run.get('pairs', ''),
    'seed': run.get('seed', ''),
    'item_accuracy': metrics.item_accuracy,
    'pair_joint_accuracy': metrics.pair_joint_accuracy,
    # Avoid Markdown table '|' which breaks cells; use mid-dots
    'report': f"[md]({md_url}) · [html]({html_preview_url}) · [chart]({chart_url}) · [dir]({dir_url})",
    'run_dir': rel_dir,
  }
  # Persist CSV with union of columns (rewrite to keep header in sync)
  try:
    if csv_path.exists():
      existing = pd.read_csv(csv_path)
      df = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    else:
      df = pd.DataFrame([row])
    # Order columns: primary metrics first, helpers after
    preferred = [
      'timestamp',
      'client',
      'model',
      'pairs',
      'seed',
      'item_accuracy',
      'pair_joint_accuracy',
      'report',
      'run_dir',
    ]
    cols = [c for c in preferred if c in df.columns] + [
      c for c in df.columns if c not in preferred
    ]
    df = df[cols]
    df.to_csv(csv_path, index=False)
  except Exception:
    # Fallback to simple append if pandas flow fails
    import csv
    write_header = not csv_path.exists()
    with open(csv_path, 'a', newline='') as f:
      writer = csv.DictWriter(f, fieldnames=list(row.keys()))
      if write_header:
        writer.writeheader()
      writer.writerow(row)

  # Rebuild leaderboard table (top N by pair_joint then item)
  try:
    df = pd.read_csv(csv_path)
    df = df.sort_values(
      ['pair_joint_accuracy', 'item_accuracy'], ascending=[False, False]
    ).fillna('')
    # Escape any legacy '|' in report cells to avoid Markdown column splits
    if 'report' in df.columns:
      df['report'] = df['report'].astype(str).str.replace('|', r'\|', regex=False)
    # Limit rows for README brevity
    top = df.head(20)
    table_md = tabulate(
      top, headers='keys', tablefmt='github', showindex=False, floatfmt='.3f'
    )
  except Exception:
    table_md = '(leaderboard unavailable)'

  # Update README between markers
  readme_path = root / 'README.md'
  text = readme_path.read_text(encoding='utf-8')
  start = '<!-- LEADERBOARD:START -->'
  end = '<!-- LEADERBOARD:END -->'
  if start in text and end in text:
    new_block = f'{start}\n\n{table_md}\n\n{end}'
    text = re.sub(
      r'<!-- LEADERBOARD:START -->.*?<!-- LEADERBOARD:END -->',
      new_block,
      text,
      flags=re.S,
    )
  else:
    # Append a section if markers missing
    text += f'\n\n## Leaderboard\n\n{start}\n\n{table_md}\n\n{end}\n'
  readme_path.write_text(text, encoding='utf-8')


def _dump_prediction_splits(
  preds: list[Prediction], out_dir: str, basename: str
) -> None:
  """Write correct and incorrect prediction JSONL files."""
  corr_path = os.path.join(out_dir, f'correct_predictions_{basename}.jsonl')
  inc_path = os.path.join(out_dir, f'incorrect_predictions_{basename}.jsonl')
  with open(corr_path, 'w') as cf, open(inc_path, 'w') as inf:
    for p in preds:
      row = {
        'pair_id': p.pair_id,
        'item_id': p.item_id,
        'operator': p.meta.get('operator', ''),
        'domain': p.meta.get('domain', ''),
        'question': p.question,
        'prediction': p.prediction,
        'gold': p.gold,
        'answer_type': p.answer_type,
        'correct': p.correct,
      }
      if p.correct:
        cf.write(json.dumps(row) + '\n')
      else:
        inf.write(json.dumps(row) + '\n')


def render_report(
  preds: list[Prediction], out_dir: str, basename: str = 'report'
) -> None:
  """Aggregate metrics and write named report + metrics + chart + HTML + splits.

  Files written:
    metrics_{basename}.json
    operator_accuracy_{basename}.png
    report_{basename}.md
    report_{basename}.html
    correct_predictions_{basename}.jsonl
    incorrect_predictions_{basename}.jsonl
  """
  # Load optional run_info
  run_info_path = os.path.join(out_dir, 'run_info.json')
  run_info = {}
  if os.path.exists(run_info_path):
    try:
      with open(run_info_path, 'r') as f:
        run_info = json.load(f)
    except Exception:
      run_info = {}

  metrics = aggregate(preds)
  os.makedirs(out_dir, exist_ok=True)
  metrics_path = os.path.join(out_dir, f'metrics_{basename}.json')
  dump_metrics(metrics, metrics_path)
  # Per-operator chart
  ops = sorted(metrics.by_operator.keys())
  accs = [metrics.by_operator[o]['item_accuracy'] for o in ops]
  plt.figure()
  plt.bar(ops, accs)
  plt.ylabel('Item Accuracy')
  plt.title('Accuracy by Operator (NQMP)')
  plt.xticks(rotation=30, ha='right')
  chart_path = os.path.join(out_dir, f'operator_accuracy_{basename}.png')
  plt.tight_layout()
  plt.savefig(chart_path, dpi=160)
  # Markdown report
  lines = []
  lines.append('# NQMP Benchmark Report\n')
  if run_info:
    lines.append(
      f'**Client/Model:** {run_info.get("client", "")} / {run_info.get("model", "")}  '
    )
    lines.append(
      f'**Pairs / Seed:** {run_info.get("pairs", "")} / {run_info.get("seed", "")}  '
    )
    lines.append(f'**Timestamp:** {run_info.get("timestamp", "")}\n')
  lines.append(f'**Item Accuracy:** {metrics.item_accuracy:.3f}  ')
  lines.append(f'**Pair Joint Accuracy:** {metrics.pair_joint_accuracy:.3f}\n')
  df = pd.DataFrame({'operator': ops, 'item_accuracy': accs}).sort_values(
    'operator'
  )
  lines.append('## Accuracy by Operator\n')
  lines.append(df.to_markdown(index=False))
  lines.append(f'\n![Operator Accuracy](operator_accuracy_{basename}.png)\n')
  with open(os.path.join(out_dir, f'report_{basename}.md'), 'w') as f:
    f.write('\n'.join(lines))
  # HTML report (embed chart)
  img_data = (
    _embed_image_base64(chart_path) if os.path.exists(chart_path) else ''
  )
  operator_table_html = df.to_html(index=False)
  html = f"""
  <!doctype html>
  <html lang=\"en\"><head><meta charset=\"utf-8\"/>
  <title>NQMP Report - {basename}</title>
  <style>
    body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:900px;margin:40px auto;padding:0 16px;}}
    header h1{{margin:0 0 8px 0;}}
    .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;}}
    .metric{{padding:12px;border:1px solid #eee;border-radius:8px;}}
    table{{border-collapse:collapse;width:100%;}}
    th,td{{border:1px solid #ddd;padding:6px 8px;text-align:left;}}
    th{{background:#f7f7f7;}}
    code{{background:#f6f8fa;padding:2px 4px;border-radius:4px;}}
  </style></head>
  <body>
    <header>
      <h1>NQMP Benchmark Report</h1>
      <p><strong>Run:</strong> {basename}</p>
      <p><strong>Client/Model:</strong> {run_info.get('client', '')} / {run_info.get('model', '')}</p>
      <p><strong>Pairs/Seed:</strong> {run_info.get('pairs', '')} / {run_info.get('seed', '')}</p>
      <p><strong>Timestamp:</strong> {run_info.get('timestamp', '')}</p>
    </header>
    <section class=\"grid\">
      <div class=\"metric\"><h3>Item Accuracy</h3><p>{metrics.item_accuracy:.3f}</p></div>
      <div class=\"metric\"><h3>Pair Joint Accuracy</h3><p>{metrics.pair_joint_accuracy:.3f}</p></div>
    </section>
    <section>
      <h2>Accuracy by Operator</h2>
      <img alt=\"Operator Accuracy\" src=\"{img_data}\" style=\"max-width:100%;height:auto;border:1px solid #eee;border-radius:8px;\"/>
      {operator_table_html}
    </section>
    <section>
      <h2>Artifacts</h2>
      <ul>
        <li><code>metrics_{basename}.json</code></li>
        <li><code>predictions.jsonl</code></li>
        <li><code>correct_predictions_{basename}.jsonl</code></li>
        <li><code>incorrect_predictions_{basename}.jsonl</code></li>
        <li><code>operator_accuracy_{basename}.png</code></li>
      </ul>
    </section>
  </body></html>
  """
  with open(
    os.path.join(out_dir, f'report_{basename}.html'), 'w', encoding='utf-8'
  ) as f:
    f.write(html)
  # Write splits
  _dump_prediction_splits(preds, out_dir, basename)
  # Update leaderboard in README
  if run_info:
    _update_leaderboard_readme(run_info, metrics, out_dir, basename)


def to_predictions(rows: list[dict]) -> list[Prediction]:
  """Convert dict rows to Prediction objects."""
  preds: list[Prediction] = []
  for r in rows:
    preds.append(
      Prediction(
        pair_id=r['pair_id'],
        item_id=r['item_id'],
        question=r['question'],
        prediction=r['prediction'],
        gold=r['gold'],
        answer_type=r['answer_type'],
        correct=bool(r['correct']),
        meta=dict(r.get('meta', {})),
      )
    )
  return preds
