import os
import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.services.media_service import upload_media, list_media, delete_media, asset_to_dict
from app.services.storage import get_storage

router = APIRouter(prefix="/api", tags=["media"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_storage_dep():
    return get_storage()

def get_user(x_user_id: str = Header(default="system")) -> str:
    return x_user_id

# Lucide icon list — 50+ common icons
LUCIDE_ICONS = [
    {"name": "arrow-left", "category": "arrows"},
    {"name": "arrow-right", "category": "arrows"},
    {"name": "arrow-up", "category": "arrows"},
    {"name": "arrow-down", "category": "arrows"},
    {"name": "chevron-left", "category": "arrows"},
    {"name": "chevron-right", "category": "arrows"},
    {"name": "chevron-up", "category": "arrows"},
    {"name": "chevron-down", "category": "arrows"},
    {"name": "check", "category": "interface"},
    {"name": "x", "category": "interface"},
    {"name": "plus", "category": "interface"},
    {"name": "minus", "category": "interface"},
    {"name": "search", "category": "interface"},
    {"name": "settings", "category": "interface"},
    {"name": "menu", "category": "interface"},
    {"name": "home", "category": "interface"},
    {"name": "star", "category": "interface"},
    {"name": "heart", "category": "interface"},
    {"name": "bookmark", "category": "interface"},
    {"name": "edit", "category": "interface"},
    {"name": "trash", "category": "interface"},
    {"name": "copy", "category": "interface"},
    {"name": "eye", "category": "interface"},
    {"name": "eye-off", "category": "interface"},
    {"name": "play", "category": "media"},
    {"name": "pause", "category": "media"},
    {"name": "stop-circle", "category": "media"},
    {"name": "volume-2", "category": "media"},
    {"name": "volume-x", "category": "media"},
    {"name": "image", "category": "media"},
    {"name": "video", "category": "media"},
    {"name": "music", "category": "media"},
    {"name": "mic", "category": "media"},
    {"name": "camera", "category": "media"},
    {"name": "mail", "category": "communication"},
    {"name": "phone", "category": "communication"},
    {"name": "message-circle", "category": "communication"},
    {"name": "bell", "category": "communication"},
    {"name": "send", "category": "communication"},
    {"name": "share", "category": "communication"},
    {"name": "file", "category": "files"},
    {"name": "folder", "category": "files"},
    {"name": "download", "category": "files"},
    {"name": "upload", "category": "files"},
    {"name": "paperclip", "category": "files"},
    {"name": "link", "category": "files"},
    {"name": "monitor", "category": "devices"},
    {"name": "smartphone", "category": "devices"},
    {"name": "wifi", "category": "devices"},
    {"name": "sun", "category": "weather"},
    {"name": "moon", "category": "weather"},
    {"name": "cloud", "category": "weather"},
    {"name": "info", "category": "misc"},
    {"name": "alert-triangle", "category": "misc"},
    {"name": "lock", "category": "misc"},
    {"name": "unlock", "category": "misc"},
    {"name": "user", "category": "misc"},
    {"name": "users", "category": "misc"},
    {"name": "calendar", "category": "misc"},
    {"name": "clock", "category": "misc"},
    {"name": "map-pin", "category": "misc"},
    {"name": "globe", "category": "misc"},
    {"name": "zap", "category": "misc"},
]


@router.post("/courses/{course_id}/media")
async def upload_asset(
    course_id: str,
    file: UploadFile = File(...),
    alt_text: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    storage=Depends(get_storage_dep),
    user_id: str = Depends(get_user),
):
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    try:
        asset = await upload_media(db, storage, course_id, user_id, file.filename or "upload", data, mime, alt_text)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return asset_to_dict(asset, storage)


@router.get("/courses/{course_id}/media")
async def list_assets(course_id: str, db: AsyncSession = Depends(get_db), storage=Depends(get_storage_dep)):
    assets = await list_media(db, course_id)
    return [asset_to_dict(a, storage) for a in assets]


@router.delete("/media/{asset_id}")
async def delete_asset(asset_id: int, db: AsyncSession = Depends(get_db), storage=Depends(get_storage_dep)):
    try:
        await delete_media(db, storage, asset_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"status": "deleted"}


@router.get("/media/unsplash/search")
async def unsplash_search(q: str, page: int = 1, per_page: int = 12):
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        raise HTTPException(503, "Unsplash not configured")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.unsplash.com/search/photos",
            params={"query": q, "page": page, "per_page": per_page},
            headers={"Authorization": f"Client-ID {key}"},
        )
    return resp.json()


class UnsplashImport(BaseModel):
    unsplash_id: str
    download_url: str
    alt_text: str
    thumb_url: str


@router.post("/courses/{course_id}/media/from-unsplash")
async def import_from_unsplash(
    course_id: str,
    body: UnsplashImport,
    db: AsyncSession = Depends(get_db),
    storage=Depends(get_storage_dep),
    user_id: str = Depends(get_user),
):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(body.download_url)
        if resp.status_code != 200:
            raise HTTPException(502, "Failed to fetch image from Unsplash")
        data = resp.content
        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
    try:
        asset = await upload_media(
            db, storage, course_id, user_id,
            f"{body.unsplash_id}.jpg", data, content_type, body.alt_text,
        )
        asset.source = "unsplash"
        asset.source_ref = body.unsplash_id
        await db.commit()
        await db.refresh(asset)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return asset_to_dict(asset, storage)


@router.get("/media/lucide/search")
async def lucide_search(q: str = "", limit: int = 20):
    q_lower = q.lower()
    results = [i for i in LUCIDE_ICONS if not q_lower or q_lower in i["name"]]
    return results[:limit]
