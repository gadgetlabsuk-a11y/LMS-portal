"""Block/slide CRUD endpoints — P3 of the LMS platform."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Course, Module, Lesson, Slide
from app.services.block_service import validate_blocks
from app.services.slide_layouts import VALID_LAYOUTS

router = APIRouter(prefix="/api", tags=["courses"])


# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def get_current_user(x_user_id: str = Header(default="system")) -> str:
    return x_user_id


# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------

class CreateModuleBody(BaseModel):
    title: str
    position: int = 0


class PatchModuleBody(BaseModel):
    title: str | None = None
    position: int | None = None


class CreateLessonBody(BaseModel):
    title: str
    position: int = 0


class CreateSlideBody(BaseModel):
    title: str | None = None
    layout: str
    position: int = 0


class PatchSlideBody(BaseModel):
    title: str | None = None
    layout: str | None = None
    blocks: list[dict] | None = None
    notes: str | None = None


class ReorderItem(BaseModel):
    id: str
    position: int


class ReorderBody(BaseModel):
    modules: list[ReorderItem] = []
    lessons: list[ReorderItem] = []
    slides: list[ReorderItem] = []


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def slide_to_dict(slide: Slide) -> dict[str, Any]:
    return {
        "id": slide.id,
        "lesson_id": slide.lesson_id,
        "title": slide.title,
        "position": slide.position,
        "layout": slide.layout,
        "blocks": slide.blocks or [],
        "notes": slide.notes,
        "created_at": slide.created_at.isoformat() if slide.created_at else None,
        "updated_at": slide.updated_at.isoformat() if slide.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Module endpoints
# ---------------------------------------------------------------------------

@router.post("/courses/{course_id}/modules")
async def create_module(
    course_id: str,
    body: CreateModuleBody,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    # Verify course exists
    result = await db.execute(select(Course).where(Course.id == course_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Course not found")

    module = Module(
        id=str(uuid.uuid4()),
        course_id=course_id,
        title=body.title,
        sort_order=body.position,
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)

    return {
        "id": module.id,
        "course_id": module.course_id,
        "title": module.title,
        "position": module.sort_order,
    }


@router.patch("/courses/{course_id}/modules/{module_id}")
async def update_module(
    course_id: str,
    module_id: str,
    body: PatchModuleBody,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Module).where(Module.id == module_id, Module.course_id == course_id)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(404, "Module not found")

    if body.title is not None:
        module.title = body.title
    if body.position is not None:
        module.sort_order = body.position

    await db.commit()
    return {"status": "updated"}


@router.delete("/courses/{course_id}/modules/{module_id}")
async def delete_module(
    course_id: str,
    module_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Module).where(Module.id == module_id, Module.course_id == course_id)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(404, "Module not found")

    await db.delete(module)
    await db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Lesson endpoints
# ---------------------------------------------------------------------------

@router.post("/modules/{module_id}/lessons")
async def create_lesson(
    module_id: str,
    body: CreateLessonBody,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Module).where(Module.id == module_id))
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(404, "Module not found")

    lesson = Lesson(
        id=str(uuid.uuid4()),
        module_id=module_id,
        course_id=module.course_id,
        title=body.title,
        sort_order=body.position,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)

    return {
        "id": lesson.id,
        "module_id": lesson.module_id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "position": lesson.sort_order,
    }


# ---------------------------------------------------------------------------
# Slide endpoints
# ---------------------------------------------------------------------------

@router.post("/lessons/{lesson_id}/slides")
async def create_slide(
    lesson_id: str,
    body: CreateSlideBody,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    if body.layout not in VALID_LAYOUTS:
        raise HTTPException(400, f"Invalid layout: {body.layout!r}. Valid layouts: {sorted(VALID_LAYOUTS)}")

    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Lesson not found")

    slide = Slide(
        lesson_id=lesson_id,
        title=body.title,
        layout=body.layout,
        position=body.position,
        blocks=[],
    )
    db.add(slide)
    await db.commit()
    await db.refresh(slide)

    return slide_to_dict(slide)


@router.get("/slides/{slide_id}")
async def get_slide(
    slide_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Slide).where(Slide.id == slide_id))
    slide = result.scalar_one_or_none()
    if not slide:
        raise HTTPException(404, "Slide not found")
    return slide_to_dict(slide)


@router.patch("/slides/{slide_id}")
async def update_slide(
    slide_id: int,
    body: PatchSlideBody,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Slide).where(Slide.id == slide_id))
    slide = result.scalar_one_or_none()
    if not slide:
        raise HTTPException(404, "Slide not found")

    if body.layout is not None:
        if body.layout not in VALID_LAYOUTS:
            raise HTTPException(400, f"Invalid layout: {body.layout!r}. Valid layouts: {sorted(VALID_LAYOUTS)}")
        slide.layout = body.layout

    if body.title is not None:
        slide.title = body.title

    if body.notes is not None:
        slide.notes = body.notes

    if body.blocks is not None:
        try:
            validate_blocks(body.blocks)
        except ValueError as e:
            raise HTTPException(422, str(e))
        slide.blocks = body.blocks

    slide.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(slide)
    return slide_to_dict(slide)


@router.delete("/slides/{slide_id}")
async def delete_slide(
    slide_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Slide).where(Slide.id == slide_id))
    slide = result.scalar_one_or_none()
    if not slide:
        raise HTTPException(404, "Slide not found")

    await db.delete(slide)
    await db.commit()
    return {"status": "deleted"}


@router.post("/slides/{slide_id}/duplicate")
async def duplicate_slide(
    slide_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Slide).where(Slide.id == slide_id))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(404, "Slide not found")

    clone = Slide(
        lesson_id=original.lesson_id,
        title=original.title,
        layout=original.layout,
        position=original.position + 1,
        blocks=list(original.blocks) if original.blocks else [],
        notes=original.notes,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    return slide_to_dict(clone)


# ---------------------------------------------------------------------------
# Bulk reorder
# ---------------------------------------------------------------------------

@router.post("/courses/{course_id}/reorder")
async def reorder_course(
    course_id: str,
    body: ReorderBody,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict:
    # Verify course exists
    result = await db.execute(select(Course).where(Course.id == course_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Course not found")

    for item in body.modules:
        await db.execute(
            update(Module)
            .where(Module.id == item.id, Module.course_id == course_id)
            .values(sort_order=item.position)
        )

    for item in body.lessons:
        await db.execute(
            update(Lesson)
            .where(Lesson.id == item.id, Lesson.course_id == course_id)
            .values(sort_order=item.position)
        )

    for item in body.slides:
        # Convert id to int since Slide PK is Integer
        try:
            slide_id_int = int(item.id)
        except (ValueError, TypeError):
            raise HTTPException(400, f"Invalid slide id: {item.id!r}")
        await db.execute(
            update(Slide)
            .where(Slide.id == slide_id_int)
            .values(position=item.position)
        )

    await db.commit()
    return {"status": "reordered"}
