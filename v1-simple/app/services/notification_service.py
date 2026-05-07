import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Enrollment, Course, Notification

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)

MAIL_PROVIDER = os.environ.get("MAIL_PROVIDER", "log")   # log | postmark | ses
MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@example.com")
POSTMARK_TOKEN = os.environ.get("POSTMARK_TOKEN", "")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

EMAIL_SUBJECTS = {
    "assigned":  "You've been assigned: {course_title}",
    "due_soon":  "Reminder: {course_title} due in 7 days",
    "overdue":   "Overdue: {course_title}",
    "completed": "Course completed: {course_title}",
}


def _render(template_name: str, ctx: dict) -> str:
    tmpl = _jinja_env.get_template(f"{template_name}.html")
    return tmpl.render(**ctx)


async def _send_email(to: str, subject: str, html: str) -> bool:
    """Send via configured provider. Returns True on success."""
    if MAIL_PROVIDER == "log" or not to or "@" not in to:
        logger.info("EMAIL (log-only) to=%s subject=%s", to, subject)
        return True

    if MAIL_PROVIDER == "postmark":
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.postmarkapp.com/email",
                headers={"X-Postmark-Server-Token": POSTMARK_TOKEN, "Content-Type": "application/json"},
                json={"From": MAIL_FROM, "To": to, "Subject": subject, "HtmlBody": html},
            )
            if resp.status_code != 200:
                logger.error("Postmark send failed: %s %s", resp.status_code, resp.text)
                return False
            return True

    logger.warning("Unknown MAIL_PROVIDER=%s, email not sent", MAIL_PROVIDER)
    return False


async def send_notification(
    db: AsyncSession,
    user_id: str,
    user_email: str,
    kind: str,
    course_id: str,
    course_title: str,
    extra: dict | None = None,
) -> Notification:
    """Create a Notification record and attempt email send."""
    payload = {"course_title": course_title, **(extra or {})}
    notif = Notification(
        user_id=user_id,
        kind=kind,
        course_id=course_id,
        payload=payload,
    )
    db.add(notif)
    await db.flush()

    ctx = {
        "course_title": course_title,
        "course_url": f"{BASE_URL}/learn/{course_id}",
        **payload,
    }
    subject = EMAIL_SUBJECTS.get(kind, kind).format(**ctx)
    html = _render(kind, ctx)

    ok = await _send_email(user_email, subject, html)
    if ok:
        notif.sent_email_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(notif)
    return notif


async def run_due_soon_check(db: AsyncSession) -> int:
    """Send due_soon emails to learners whose due_date is in 6–8 days. Returns count sent."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now + timedelta(days=6)
    window_end = now + timedelta(days=8)

    stmt = (
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(
            Enrollment.due_date >= window_start,
            Enrollment.due_date <= window_end,
            Enrollment.completed == False,
        )
    )
    result = await db.execute(stmt)
    count = 0
    for enrollment, course in result.all():
        await send_notification(
            db,
            user_id=enrollment.user_id,
            user_email=enrollment.user_id,  # use user_id as email until Users table exists
            kind="due_soon",
            course_id=course.id,
            course_title=course.title,
            extra={"due_date": enrollment.due_date.strftime("%d %B %Y") if enrollment.due_date else ""},
        )
        count += 1
    return count


async def run_overdue_check(db: AsyncSession) -> int:
    """Send overdue emails for past-due incomplete enrollments. Returns count sent."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stmt = (
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(
            Enrollment.due_date < now,
            Enrollment.completed == False,
        )
    )
    result = await db.execute(stmt)
    count = 0
    for enrollment, course in result.all():
        await send_notification(
            db,
            user_id=enrollment.user_id,
            user_email=enrollment.user_id,
            kind="overdue",
            course_id=course.id,
            course_title=course.title,
            extra={"due_date": enrollment.due_date.strftime("%d %B %Y") if enrollment.due_date else ""},
        )
        count += 1
    return count
