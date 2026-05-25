"""Integration (third-party API key) settings.

A single-row `integration_settings` table holds keys entered via the admin Settings
page. `apply_integration_settings()` copies any non-empty key onto the live `settings`
object, overriding the corresponding environment variable. Because every service reads
its key from `settings` at point-of-use (see the `api_key` properties on TTSService /
QAService / ClaudeService / ScriptService, and `get_stt_provider()`), updates take
effect immediately — no restart required.

NOTE: prod SQLite has no persistent volume, so DB-stored keys are wiped on redeploy.
Set the matching env vars in Coolify for permanence; DB keys act as an in-app override.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from config import settings
from models import IntegrationSettings

logger = logging.getLogger(__name__)

# Placeholder Claude key shipped as the env default — treated as "not configured".
_CLAUDE_PLACEHOLDER = "sk-default-key"

# (provider key, IntegrationSettings attr, settings attr)
_PROVIDERS = (
    ("elevenlabs", "elevenlabs_api_key", "ELEVENLABS_API_KEY"),
    ("deepgram", "deepgram_api_key", "DEEPGRAM_API_KEY"),
    ("claude", "claude_api_key", "CLAUDE_API_KEY"),
)


def get_or_create_settings(db: Session) -> IntegrationSettings:
    """Return the single integration_settings row, creating it (id=1) if absent."""
    row = db.query(IntegrationSettings).first()
    if row is None:
        row = IntegrationSettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def apply_integration_settings(db: Session) -> None:
    """Copy any non-empty DB key onto the live `settings` object (DB overrides env)."""
    row = db.query(IntegrationSettings).first()
    if row is None:
        return
    for _provider, db_attr, settings_attr in _PROVIDERS:
        value = (getattr(row, db_attr) or "").strip()
        if value:
            setattr(settings, settings_attr, value)
    logger.info("Integration settings applied from database")


def update_settings(
    db: Session,
    *,
    elevenlabs_api_key: Optional[str] = None,
    deepgram_api_key: Optional[str] = None,
    claude_api_key: Optional[str] = None,
    updated_by: Optional[int] = None,
) -> IntegrationSettings:
    """Persist provided keys then apply them to the live settings.

    Only non-None fields are written, so callers can update one key at a time.
    An empty string clears a key (reverting that provider to its env default on the
    next process start; the live `settings` value is not lowered here).
    """
    row = get_or_create_settings(db)
    if elevenlabs_api_key is not None:
        row.elevenlabs_api_key = elevenlabs_api_key.strip() or None
    if deepgram_api_key is not None:
        row.deepgram_api_key = deepgram_api_key.strip() or None
    if claude_api_key is not None:
        row.claude_api_key = claude_api_key.strip() or None
    if updated_by is not None:
        row.updated_by = updated_by
    db.commit()
    db.refresh(row)
    apply_integration_settings(db)
    return row


def _mask(value: str) -> str:
    """Mask a secret, revealing only the last 4 chars (e.g. '••••••1a2b')."""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * 6 + value[-4:]


def integration_status(db: Session) -> dict:
    """Report, per provider, whether a key is effectively configured and its source.

    Reflects the *effective* value that services will use (the live `settings`),
    never returning the raw key — only a masked preview.
    """
    row = db.query(IntegrationSettings).first()
    out: dict = {}
    for provider, db_attr, settings_attr in _PROVIDERS:
        db_value = ((getattr(row, db_attr) if row else None) or "").strip()
        effective = (getattr(settings, settings_attr) or "").strip()
        if provider == "claude" and effective == _CLAUDE_PLACEHOLDER:
            effective = ""
        configured = bool(effective)
        out[provider] = {
            "configured": configured,
            "masked": _mask(effective) if configured else None,
            "source": "database" if db_value else ("environment" if configured else None),
        }
    return out
