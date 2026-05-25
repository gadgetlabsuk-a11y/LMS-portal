"""Admin integration-settings endpoints (third-party API keys).

- GET  /api/admin/integrations  — masked status per provider (never returns raw keys)
- PUT  /api/admin/integrations  — set/clear keys (admin only); applied immediately

Keys are stored in the single-row integration_settings table and override the
matching env var at runtime. See services/integration_settings_service.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserRole
from middleware.auth_middleware import require_role
from services.integration_settings_service import (
    integration_status,
    update_settings,
)

router = APIRouter(prefix="/api/admin", tags=["admin-integrations"])


class IntegrationUpdate(BaseModel):
    # Each field is optional: omit to leave unchanged, "" to clear, a value to set.
    elevenlabs_api_key: Optional[str] = None
    deepgram_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    heygen_api_key: Optional[str] = None


@router.get("/integrations")
async def get_integrations(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Masked per-provider configuration status (configured / masked / source)."""
    return {"providers": integration_status(db)}


@router.put("/integrations")
async def put_integrations(
    body: IntegrationUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Persist provided keys and apply them live; returns the refreshed status."""
    update_settings(
        db,
        elevenlabs_api_key=body.elevenlabs_api_key,
        deepgram_api_key=body.deepgram_api_key,
        claude_api_key=body.claude_api_key,
        heygen_api_key=body.heygen_api_key,
        updated_by=current_user.id,
    )
    return {"providers": integration_status(db)}
