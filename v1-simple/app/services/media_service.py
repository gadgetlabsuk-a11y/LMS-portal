import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import MediaAsset
from app.services.storage import StorageBackend

ALLOWED_KINDS = {
    "image": {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"},
    "video": {"video/mp4", "video/webm"},
    "audio": {"audio/mpeg", "audio/wav", "audio/ogg"},
    "document": {"application/pdf"},
}

MAX_SIZES = {
    "image":    20 * 1024 * 1024,
    "video":   500 * 1024 * 1024,
    "audio":   100 * 1024 * 1024,
    "document": 50 * 1024 * 1024,
}

def detect_kind(mime_type: str) -> str:
    for kind, mimes in ALLOWED_KINDS.items():
        if mime_type in mimes:
            return kind
    raise ValueError(f"Unsupported file type: {mime_type}")

async def upload_media(
    db: AsyncSession,
    storage: StorageBackend,
    course_id: str,
    uploader_id: str,
    filename: str,
    data: bytes,
    mime_type: str,
    alt_text: str | None = None,
) -> MediaAsset:
    kind = detect_kind(mime_type)
    if len(data) > MAX_SIZES[kind]:
        raise ValueError(f"File exceeds size limit for {kind}")
    sha = hashlib.sha256(data).hexdigest()[:16]
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    key = f"courses/{course_id}/{kind}/{sha}.{ext}"
    storage.put(key, data, mime_type)
    asset = MediaAsset(
        course_id=course_id, uploader_id=uploader_id, kind=kind,
        filename=filename, storage_key=key, mime_type=mime_type,
        size_bytes=len(data), alt_text=alt_text, source="upload",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset

async def list_media(db: AsyncSession, course_id: str) -> list[MediaAsset]:
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.course_id == course_id)
        .order_by(MediaAsset.created_at.desc())
    )
    return result.scalars().all()

async def delete_media(db: AsyncSession, storage: StorageBackend, asset_id: int) -> None:
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise ValueError("Asset not found")
    storage.delete(asset.storage_key)
    await db.delete(asset)
    await db.commit()

def asset_to_dict(asset: MediaAsset, storage: StorageBackend) -> dict:
    return {
        "id": asset.id, "course_id": asset.course_id, "kind": asset.kind,
        "filename": asset.filename, "mime_type": asset.mime_type,
        "size_bytes": asset.size_bytes, "alt_text": asset.alt_text,
        "source": asset.source, "source_ref": asset.source_ref,
        "url": storage.signed_url(asset.storage_key),
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }
