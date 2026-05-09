"""
Generic file upload endpoint.
Stores uploaded files under uploads/{category}/ and returns a serving URL.
"""

import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel

from models import User
from middleware.auth_middleware import require_creator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".pdf", ".docx",
    ".mp4", ".mov", ".webm",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class UploadResponse(BaseModel):
    url: str
    filename: str
    size: int


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("general"),
    current_user: User = Depends(require_creator),
) -> UploadResponse:
    """
    Upload a file to uploads/{category}/ and return its serving URL.

    - Only allowed MIME extensions (images, docs, video) are accepted.
    - Files larger than 50 MB are rejected.
    - Requires creator or admin role.
    """
    # Validate extension
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed: '{suffix}'. Allowed types: images, pdf, docx, video.",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size: 50 MB.",
        )

    # Build a safe, collision-free filename
    original_name = file.filename or "file"
    safe_name = "".join(
        c if c.isalnum() or c in "._-" else "_" for c in original_name
    )
    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"

    # Persist to disk
    upload_dir = Path("uploads") / category
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / stored_name).write_bytes(data)

    url = f"/uploads/{category}/{stored_name}"
    logger.info("File uploaded: %s by user %s", url, current_user.id)

    return UploadResponse(
        url=url,
        filename=original_name,
        size=len(data),
    )
