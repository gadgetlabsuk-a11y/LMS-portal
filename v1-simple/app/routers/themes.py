"""Theme registry and course-theme assignment router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Theme
from app.services.theme_service import (
    get_course_theme,
    get_theme_by_slug,
    list_themes,
    set_course_theme,
    theme_to_dict,
)

router = APIRouter(prefix="/api", tags=["themes"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Pydantic bodies
# ---------------------------------------------------------------------------

class CourseThemeUpdate(BaseModel):
    theme_id: int
    overrides: dict | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/themes")
async def list_all_themes(db: AsyncSession = Depends(get_db)):
    themes = await list_themes(db)
    return [theme_to_dict(t) for t in themes]


@router.get("/themes/{slug}")
async def get_theme(slug: str, db: AsyncSession = Depends(get_db)):
    theme = await get_theme_by_slug(db, slug)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme_to_dict(theme)


@router.get("/courses/{course_id}/theme")
async def get_course_theme_route(course_id: str, db: AsyncSession = Depends(get_db)):
    result = await get_course_theme(db, course_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No theme assigned to this course")
    return result


@router.put("/courses/{course_id}/theme")
async def set_course_theme_route(
    course_id: str,
    body: CourseThemeUpdate,
    db: AsyncSession = Depends(get_db),
):
    # Verify the theme_id exists
    theme_result = await db.execute(select(Theme).where(Theme.id == body.theme_id))
    if theme_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Theme not found")

    await set_course_theme(db, course_id, body.theme_id, body.overrides)
    return {"status": "ok", "course_id": course_id, "theme_id": body.theme_id}
