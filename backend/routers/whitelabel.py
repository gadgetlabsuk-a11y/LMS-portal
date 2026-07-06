"""
White label configuration routes for theming.
Provides theme customization, logo/favicon upload, and import/export.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
import json
import os
from pathlib import Path
import logging

from database import get_db
from models import User, WhiteLabelConfig
from middleware.auth_middleware import require_admin
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whitelabel", tags=["whitelabel"])


class WhiteLabelConfigUpdate(BaseModel):
    """White label config update model."""

    brand_name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    bg_color: Optional[str] = None
    text_color: Optional[str] = None
    font_family: Optional[str] = None
    heading_font: Optional[str] = None
    border_radius: Optional[str] = None
    button_style: Optional[str] = None
    custom_css: Optional[str] = None


class WhiteLabelConfigResponse(BaseModel):
    """White label config response model."""

    id: int
    brand_name: str
    logo_path: Optional[str]
    favicon_path: Optional[str]
    primary_color: str
    secondary_color: str
    accent_color: str
    bg_color: str
    text_color: str
    font_family: str
    heading_font: str
    border_radius: str
    button_style: str
    custom_css: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PreviewResponse(BaseModel):
    """CSS variables preview response."""

    css_variables: str


def _get_or_create_config(db: Session) -> WhiteLabelConfig:
    """Get or create default white label config."""
    config = db.query(WhiteLabelConfig).first()
    if not config:
        config = WhiteLabelConfig(
            brand_name="Learning Portal",
            primary_color="#2563EB",
            secondary_color="#1E3A8A",
            accent_color="#F59E0B",
            bg_color="#F8FAFC",
            text_color="#1E293B",
            font_family="system-ui, sans-serif",
            heading_font="system-ui, sans-serif",
            border_radius="0.5rem",
            button_style="rounded",
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _validate_color(color: str) -> bool:
    """Validate hex color format."""
    if not color.startswith("#") or len(color) != 7:
        return False
    try:
        int(color[1:], 16)
        return True
    except ValueError:
        return False


@router.get("/config", response_model=WhiteLabelConfigResponse)
async def get_config(
    db: Session = Depends(get_db),
) -> WhiteLabelConfig:
    """
    Get current white label configuration.

    Args:
        db: Database session

    Returns:
        Current configuration
    """
    config = _get_or_create_config(db)
    return config


@router.put("/config", response_model=WhiteLabelConfigResponse)
async def update_config(
    config_data: WhiteLabelConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> WhiteLabelConfig:
    """
    Update white label configuration.

    Args:
        config_data: Configuration update data
        db: Database session
        current_user: Current admin user

    Returns:
        Updated configuration

    Raises:
        HTTPException: If validation fails
    """
    config = _get_or_create_config(db)

    # Validate colors
    if config_data.primary_color and not _validate_color(config_data.primary_color):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid primary color format (use #RRGGBB)",
        )

    if config_data.secondary_color and not _validate_color(config_data.secondary_color):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid secondary color format",
        )

    if config_data.accent_color and not _validate_color(config_data.accent_color):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accent color format",
        )

    if config_data.bg_color and not _validate_color(config_data.bg_color):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid background color format",
        )

    if config_data.text_color and not _validate_color(config_data.text_color):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid text color format",
        )

    # Update fields
    if config_data.brand_name:
        config.brand_name = config_data.brand_name

    if config_data.primary_color:
        config.primary_color = config_data.primary_color

    if config_data.secondary_color:
        config.secondary_color = config_data.secondary_color

    if config_data.accent_color:
        config.accent_color = config_data.accent_color

    if config_data.bg_color:
        config.bg_color = config_data.bg_color

    if config_data.text_color:
        config.text_color = config_data.text_color

    if config_data.font_family:
        config.font_family = config_data.font_family

    if config_data.heading_font:
        config.heading_font = config_data.heading_font

    if config_data.border_radius:
        config.border_radius = config_data.border_radius

    if config_data.button_style:
        config.button_style = config_data.button_style

    if config_data.custom_css:
        config.custom_css = config_data.custom_css

    config.updated_at = datetime.now(timezone.utc)

    db.add(config)
    db.commit()
    db.refresh(config)

    logger.info(f"White label config updated by admin {current_user.id}")

    return config


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Upload logo file.

    Args:
        file: Logo file
        db: Database session
        current_user: Current admin user

    Returns:
        File path

    Raises:
        HTTPException: If file invalid or too large
    """
    # Validate file type
    if file.content_type not in ["image/png", "image/jpeg", "image/gif", "image/svg+xml"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: PNG, JPEG, GIF, SVG",
        )

    # Check file size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(exist_ok=True)

    filename = f"logo_{datetime.now(timezone.utc).timestamp()}.{file.filename.split('.')[-1]}"
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(contents)

    # Update config
    config = _get_or_create_config(db)
    config.logo_path = str(file_path)
    config.updated_at = datetime.now(timezone.utc)
    db.add(config)
    db.commit()

    logger.info(f"Logo uploaded by admin {current_user.id}")

    return {
        "message": "Logo uploaded successfully",
        "path": str(file_path),
    }


@router.post("/favicon")
async def upload_favicon(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Upload favicon file.

    Args:
        file: Favicon file
        db: Database session
        current_user: Current admin user

    Returns:
        File path

    Raises:
        HTTPException: If file invalid or too large
    """
    # Validate file type
    if file.content_type not in ["image/x-icon", "image/png", "image/svg+xml"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: ICO, PNG, SVG",
        )

    # Check file size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(exist_ok=True)

    filename = f"favicon_{datetime.now(timezone.utc).timestamp()}.{file.filename.split('.')[-1]}"
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(contents)

    # Update config
    config = _get_or_create_config(db)
    config.favicon_path = str(file_path)
    config.updated_at = datetime.now(timezone.utc)
    db.add(config)
    db.commit()

    logger.info(f"Favicon uploaded by admin {current_user.id}")

    return {
        "message": "Favicon uploaded successfully",
        "path": str(file_path),
    }


@router.get("/preview", response_model=PreviewResponse)
async def get_preview(
    db: Session = Depends(get_db),
) -> dict:
    """
    Get CSS variables preview.

    Args:
        db: Database session

    Returns:
        CSS variables string
    """
    config = _get_or_create_config(db)

    css_variables = f"""
:root {{
  --primary-color: {config.primary_color};
  --secondary-color: {config.secondary_color};
  --accent-color: {config.accent_color};
  --bg-color: {config.bg_color};
  --text-color: {config.text_color};
  --font-family: {config.font_family};
  --heading-font: {config.heading_font};
  --border-radius: {config.border_radius};
}}

body {{
  background-color: var(--bg-color);
  color: var(--text-color);
  font-family: var(--font-family);
}}

h1, h2, h3, h4, h5, h6 {{
  font-family: var(--heading-font);
}}

button {{
  border-radius: var(--border-radius);
}}

{config.custom_css or ''}
"""

    return {"css_variables": css_variables}


@router.post("/export")
async def export_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Export configuration as JSON.

    Args:
        db: Database session
        current_user: Current admin user

    Returns:
        Configuration as JSON
    """
    config = _get_or_create_config(db)

    export_data = {
        "brand_name": config.brand_name,
        "primary_color": config.primary_color,
        "secondary_color": config.secondary_color,
        "accent_color": config.accent_color,
        "bg_color": config.bg_color,
        "text_color": config.text_color,
        "font_family": config.font_family,
        "heading_font": config.heading_font,
        "border_radius": config.border_radius,
        "button_style": config.button_style,
        "custom_css": config.custom_css,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Config exported by admin {current_user.id}")

    return export_data


@router.post("/import")
async def import_config(
    import_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> WhiteLabelConfigResponse:
    """
    Import configuration from JSON.

    Args:
        import_data: Configuration data
        db: Database session
        current_user: Current admin user

    Returns:
        Updated configuration

    Raises:
        HTTPException: If validation fails
    """
    config = _get_or_create_config(db)

    # Validate colors
    for color_field in ["primary_color", "secondary_color", "accent_color", "bg_color", "text_color"]:
        if color_field in import_data and import_data[color_field]:
            if not _validate_color(import_data[color_field]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid {color_field} format",
                )

    # Update fields
    for field in ["brand_name", "primary_color", "secondary_color", "accent_color", "bg_color",
                  "text_color", "font_family", "heading_font", "border_radius", "button_style",
                  "custom_css"]:
        if field in import_data and import_data[field]:
            setattr(config, field, import_data[field])

    config.updated_at = datetime.now(timezone.utc)

    db.add(config)
    db.commit()
    db.refresh(config)

    logger.info(f"Config imported by admin {current_user.id}")

    return config
