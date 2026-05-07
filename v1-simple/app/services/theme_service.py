from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Theme, CourseTheme


async def list_themes(db: AsyncSession) -> list[Theme]:
    result = await db.execute(select(Theme).order_by(Theme.id))
    return result.scalars().all()


async def get_theme_by_slug(db: AsyncSession, slug: str) -> Theme | None:
    result = await db.execute(select(Theme).where(Theme.slug == slug))
    return result.scalar_one_or_none()


async def get_course_theme(db: AsyncSession, course_id: str) -> dict | None:
    """Returns merged theme tokens + overrides for a course, or None."""
    result = await db.execute(
        select(CourseTheme, Theme)
        .join(Theme, CourseTheme.theme_id == Theme.id)
        .where(CourseTheme.course_id == course_id)
    )
    row = result.first()
    if not row:
        return None
    ct, theme = row
    return {
        "theme_id": theme.id,
        "theme_slug": theme.slug,
        "theme_name": theme.name,
        "tokens": theme.tokens,
        "overrides": ct.overrides or {},
    }


async def set_course_theme(
    db: AsyncSession, course_id: str, theme_id: int, overrides: dict | None
) -> None:
    """Upsert CourseTheme for a course."""
    existing = await db.execute(
        select(CourseTheme).where(CourseTheme.course_id == course_id)
    )
    ct = existing.scalar_one_or_none()
    if ct:
        ct.theme_id = theme_id
        ct.overrides = overrides
    else:
        db.add(CourseTheme(course_id=course_id, theme_id=theme_id, overrides=overrides))
    await db.commit()


def theme_to_dict(theme: Theme) -> dict:
    return {
        "id": theme.id,
        "slug": theme.slug,
        "name": theme.name,
        "tokens": theme.tokens,
        "is_system": theme.is_system,
    }
