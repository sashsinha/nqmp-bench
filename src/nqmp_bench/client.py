"""Client adapters for querying LLMs.

Includes an OpenRouter-compatible HTTP client and a local echo stub.
"""

import time
import random
from dataclasses import dataclass
from typing import Any

import requests

from .config import load_config

# -----------------------
# Types & retry config
# -----------------------


@dataclass
class RetryConfig:
  """Retry/backoff configuration."""

  max_retries: int = 4
  backoff_base: float = 0.8  # exponential base
  backoff_cap: float = 8.0  # seconds max per sleep


def _should_retry(status: int | None) -> bool:
  """Return True if HTTP status suggests a transient failure."""
  if status is None:
    return True
  return status in (408, 409, 425, 429, 500, 502, 503, 504)


# -----------------------
# Base client
# -----------------------


@dataclass
class LLMResponse:
  """Simple wrapper for LLM outputs."""

  text: str
  raw: dict[str, Any]
  attempts: int = 1
  status_code: int | None = None


class BaseClient:
  """Abstract LLM client."""

  def predict(
    self, prompt: str, model: str | None = None, temperature: float = 0.0
  ) -> LLMResponse:
    """Return the model output for a single prompt."""
    raise NotImplementedError


# -----------------------
# OpenRouter client
# -----------------------


class OpenRouterClient(BaseClient):
  """OpenRouter-compatible chat completions client."""

  def __init__(
    self, api_key: str | None = None, base_url: str | None = None
  ) -> None:
    """Create a client.

    Args:
      api_key: API key to authenticate with OpenRouter. If omitted, read
        from the environment via `load_config()`.
      base_url: Override the API base URL.
    """
    cfg = load_config()
    self.api_key = api_key or cfg.openrouter_api_key
    self.base_url = base_url or cfg.openrouter_base_url
    if not self.api_key:
      raise RuntimeError(
        'OPENROUTER_API_KEY missing; set it in environment or .env'
      )

  def predict(
    self, prompt: str, model: str | None = None, temperature: float = 0.0
  ) -> LLMResponse:
    """Send a single-prompt chat completion request.

    Args:
      prompt: The user prompt.
      model: Model identifier to use (falls back to config default).
      temperature: Sampling temperature.

    Returns:
      LLMResponse containing the output text and raw payload.
    """
    cfg = load_config()
    model_name = model or cfg.default_model
    headers = {
      'Authorization': f'Bearer {self.api_key}',
      'Content-Type': 'application/json',
    }
    # Optional OpenRouter ranking headers
    if getattr(cfg, 'openrouter_site_url', None):
      headers['HTTP-Referer'] = cfg.openrouter_site_url
    if getattr(cfg, 'openrouter_site_title', None):
      headers['X-Title'] = cfg.openrouter_site_title

    payload = {
      'model': model_name,
      'messages': [
        {
          'role': 'system',
          'content': "Answer strictly with either 'Yes'/'No' or a comma-separated id list depending on the question. No extra text.",
        },
        {'role': 'user', 'content': prompt},
      ],
      'temperature': temperature,
    }

    retry = RetryConfig()
    for attempt in range(1, retry.max_retries + 2):  # attempts = retries + 1
      status = None
      try:
        resp = requests.post(
          self.base_url, headers=headers, json=payload, timeout=60
        )
        status = resp.status_code
        resp.raise_for_status()  # will raise on 4xx/5xx
        data = resp.json()
        try:
          text = data['choices'][0]['message']['content'].strip()
        except Exception:
          text = str(data)
        return LLMResponse(
          text=text, raw=data, attempts=attempt, status_code=status
        )
      except Exception:
        if attempt <= retry.max_retries and _should_retry(status):
          sleep = min(
            retry.backoff_cap,
            (retry.backoff_base**attempt) + random.random() * 0.25,
          )
          time.sleep(sleep)
          continue
        raise  # exhausted


# -----------------------
# Echo stub (offline)
# -----------------------


class EchoClient(BaseClient):
  """Local stub for offline dev; returns deterministic pseudo-answers."""

  def __init__(self, seed: int = 0) -> None:
    self.seed = seed

  def predict(
    self, prompt: str, model: str | None = None, temperature: float = 0.0
  ) -> LLMResponse:
    """Return a deterministic pseudo-answer for testing offline.

    The output alternates between 'Yes'/'No' for booleans and returns up to
    three dummy IDs for list questions.
    """
    rnd = hash((prompt, self.seed)) % 100
    if 'List ids' in prompt:
      k = rnd % 3  # 0..2 items
      ids = [f'X{i + 1}' for i in range(k)]
      text = ','.join(ids)
    else:
      text = 'Yes' if rnd % 2 == 0 else 'No'
    return LLMResponse(text=text, raw={'stub': True, 'seed': self.seed})
