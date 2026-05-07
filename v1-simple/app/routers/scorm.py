from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import ScormPackage
from app.services.scorm_service import ScormPackager
from app.services.storage import get_storage
import io

router = APIRouter(prefix="/api", tags=["scorm"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_user(x_user_id: str = Header(default="system")) -> str:
    return x_user_id


@router.post("/courses/{course_id}/scorm/export")
async def trigger_export(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
):
    storage = get_storage()
    packager = ScormPackager(db, storage)
    try:
        pkg = await packager.export(course_id, user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {
        "id": pkg.id,
        "course_id": pkg.course_id,
        "version": pkg.version,
        "export_version": pkg.export_version,
        "size_bytes": pkg.size_bytes,
        "exported_at": pkg.exported_at.isoformat() if pkg.exported_at else None,
    }


@router.get("/courses/{course_id}/scorm/packages")
async def list_packages(course_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScormPackage)
        .where(ScormPackage.course_id == course_id)
        .order_by(ScormPackage.export_version.desc())
    )
    pkgs = result.scalars().all()
    return [
        {
            "id": p.id, "version": p.version, "export_version": p.export_version,
            "size_bytes": p.size_bytes,
            "exported_at": p.exported_at.isoformat() if p.exported_at else None,
        }
        for p in pkgs
    ]


@router.get("/scorm/packages/{package_id}/download")
async def download_package(package_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScormPackage).where(ScormPackage.id == package_id))
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(404, "Package not found")
    storage = get_storage()
    try:
        data = storage.get(pkg.storage_key)
    except Exception:
        raise HTTPException(404, "Package file not found in storage")
    filename = f"course_{pkg.course_id}_v{pkg.export_version}.zip"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
