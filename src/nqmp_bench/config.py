"""Configuration loader for NQMP.

Reads environment variables (optionally from .env) and exposes a typed config.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
  """Holds runtime configuration loaded from environment."""

  openrouter_api_key: str | None
  openrouter_base_url: str
  default_model: str
  openrouter_site_url: str | None
  openrouter_site_title: str | None


def load_config() -> Config:
  """Load configuration from environment variables."""
  return Config(
    openrouter_api_key=os.getenv('OPENROUTER_API_KEY'),
    openrouter_base_url=os.getenv(
      'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1/chat/completions'
    ),
    default_model=os.getenv('MODEL_NAME', 'openai/gpt-4o-mini'),
    openrouter_site_url=os.getenv('OPENROUTER_HTTP_REFERER'),
    openrouter_site_title=os.getenv('OPENROUTER_X_TITLE'),
  )
