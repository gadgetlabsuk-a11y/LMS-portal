"""Business logic for departments: enrolment sync + per-type completion + status.

"Required" is derived from current membership + current assignments, never from the
presence of an enrolment/session. Enrolments are find-or-created for COURSE assignments so
progress/completion has somewhere to live; standalone broadcasts have no enrolment (a
BroadcastSession is created when the learner plays). Removing a member or unassigning content
never deletes enrolments or sessions.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models import User, Enrollment, BroadcastSession, DepartmentMember, DepartmentContent, Course


def _as_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalise a datetime to naive UTC so it compares safely with stored values."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# --------------------------------------------------------------------------- enrolment sync (courses only)

def ensure_enrollment(db: Session, user_id: int, course_id: int) -> Enrollment:
    """Find-or-create an enrolment for (user, course). Caller commits. Idempotent."""
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    if enrollment is None:
        course = db.query(Course).filter(Course.id == course_id).first()
        course_version = (course.version if course and course.version else 1)
        enrollment = Enrollment(user_id=user_id, course_id=course_id, course_version=course_version)
        db.add(enrollment)
        db.flush()
    return enrollment


def sync_assignment_enrollments(db: Session, department_id: int, course_id: int) -> None:
    """Ensure every current member of the department is enrolled in the course."""
    member_ids = [
        m.user_id
        for m in db.query(DepartmentMember).filter(DepartmentMember.department_id == department_id).all()
    ]
    for uid in member_ids:
        ensure_enrollment(db, uid, course_id)
    db.commit()


def sync_member_enrollments(db: Session, department_id: int, user_id: int) -> None:
    """Ensure a member is enrolled in every COURSE assigned to the department (broadcasts skipped)."""
    course_ids = [
        c.course_id
        for c in db.query(DepartmentContent)
        .filter(DepartmentContent.department_id == department_id, DepartmentContent.course_id.isnot(None))
        .all()
    ]
    for cid in course_ids:
        ensure_enrollment(db, user_id, cid)
    db.commit()


# --------------------------------------------------------------------------- due dates & status

def effective_due_date(content: DepartmentContent, anchor: Optional[datetime]) -> Optional[datetime]:
    """Deadline for one assignment. `anchor` is the user's department-join date (naive UTC)."""
    if not content.mandatory:
        return None
    if content.due_mode == "fixed":
        return _as_naive_utc(content.due_date)
    if content.due_mode == "relative" and content.due_days is not None and anchor is not None:
        return _as_naive_utc(anchor) + timedelta(days=content.due_days)
    return None


def status_for(completed: bool, started: bool, due: Optional[datetime],
               now: Optional[datetime] = None) -> str:
    """Return one of: not_started | in_progress | completed | overdue."""
    now = _as_naive_utc(now) if now is not None else datetime.utcnow()
    if completed:
        return "completed"
    if due is not None and due < now:
        return "overdue"
    if started:
        return "in_progress"
    return "not_started"


# --------------------------------------------------------------------------- per-type completion signals

def course_completed(db: Session, user_id: int, course_id: int) -> bool:
    e = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    return bool(e and e.completed)


def course_started(db: Session, user_id: int, course_id: int) -> bool:
    e = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    return bool(e and (e.progress or 0) > 0)


def broadcast_completed(db: Session, user_id: int, broadcast_id: int) -> bool:
    return (
        db.query(BroadcastSession)
        .filter(
            BroadcastSession.broadcast_id == broadcast_id,
            BroadcastSession.learner_id == user_id,
            BroadcastSession.completion_status == "completed",
        )
        .first()
        is not None
    )


def broadcast_started(db: Session, user_id: int, broadcast_id: int) -> bool:
    return (
        db.query(BroadcastSession)
        .filter(BroadcastSession.broadcast_id == broadcast_id, BroadcastSession.learner_id == user_id)
        .first()
        is not None
    )


def content_completed(db: Session, user_id: int, content: DepartmentContent) -> bool:
    if content.broadcast_id is not None:
        return broadcast_completed(db, user_id, content.broadcast_id)
    return course_completed(db, user_id, content.course_id)


def content_started(db: Session, user_id: int, content: DepartmentContent) -> bool:
    if content.broadcast_id is not None:
        return broadcast_started(db, user_id, content.broadcast_id)
    return course_started(db, user_id, content.course_id)


# --------------------------------------------------------------------------- cross-department resolution

def _memberships(db: Session, user_id: int) -> Dict[int, Optional[datetime]]:
    """{department_id: added_at} for the user's current memberships."""
    return {
        m.department_id: m.added_at
        for m in db.query(DepartmentMember).filter(DepartmentMember.user_id == user_id).all()
    }


def mandatory_assignments_for_user(
    db: Session, user_id: int, *, course_id: Optional[int] = None, broadcast_id: Optional[int] = None
) -> List[Tuple[DepartmentContent, Optional[datetime]]]:
    """Mandatory assignments of a target across the user's departments, paired with that
    department's join date (the relative-deadline anchor)."""
    joins = _memberships(db, user_id)
    if not joins:
        return []
    q = db.query(DepartmentContent).filter(
        DepartmentContent.department_id.in_(list(joins.keys())),
        DepartmentContent.mandatory.is_(True),
    )
    if course_id is not None:
        q = q.filter(DepartmentContent.course_id == course_id)
    if broadcast_id is not None:
        q = q.filter(DepartmentContent.broadcast_id == broadcast_id)
    return [(row, joins[row.department_id]) for row in q.all()]


def is_mandatory_for_user(db: Session, user_id: int, *, course_id: Optional[int] = None,
                          broadcast_id: Optional[int] = None) -> bool:
    return len(mandatory_assignments_for_user(db, user_id, course_id=course_id, broadcast_id=broadcast_id)) > 0


def effective_due_for_user(db: Session, user_id: int, *, course_id: Optional[int] = None,
                           broadcast_id: Optional[int] = None) -> Optional[datetime]:
    """Earliest deadline across the user's departments for a mandatory target."""
    dues = [
        effective_due_date(row, anchor)
        for row, anchor in mandatory_assignments_for_user(
            db, user_id, course_id=course_id, broadcast_id=broadcast_id
        )
    ]
    dues = [d for d in dues if d is not None]
    return min(dues) if dues else None


def required_training_for_user(db: Session, user_id: int, now: Optional[datetime] = None) -> List[dict]:
    """The user's mandatory assignments across all their departments, deduped by target
    (course/broadcast), each with the earliest effective deadline and a computed status."""
    pairs = mandatory_assignments_for_user(db, user_id)
    by_target: dict = {}
    for content, anchor in pairs:
        key = ("broadcast", content.broadcast_id) if content.broadcast_id is not None else ("course", content.course_id)
        due = effective_due_date(content, anchor)
        entry = by_target.setdefault(key, {"content": content, "dues": []})
        if due is not None:
            entry["dues"].append(due)
    out: List[dict] = []
    for (kind, _tid), e in by_target.items():
        content = e["content"]
        due = min(e["dues"]) if e["dues"] else None
        completed = content_completed(db, user_id, content)
        started = content_started(db, user_id, content)
        if kind == "broadcast":
            title = content.broadcast.title if content.broadcast else ""
            is_podcast = True
        else:
            title = content.course.title if content.course else ""
            is_podcast = bool(content.course.ilb_published) if content.course else False
        out.append({
            "content_type": kind,
            "course_id": content.course_id,
            "broadcast_id": content.broadcast_id,
            "title": title,
            "is_podcast": is_podcast,
            "due_date": due,
            "status": status_for(completed, started, due, now),
        })
    return out


def training_reminders(db: Session, within_days: int = 7, now: Optional[datetime] = None) -> List[dict]:
    """Per-user mandatory items that are OVERDUE or due within `within_days` (and not completed),
    across all departments. Each row carries the user's contact info. Foundation for the future
    email reminder job; also serves an admin 'who's behind' report."""
    now = now or datetime.utcnow()
    window_end = now + timedelta(days=within_days) if within_days is not None else None
    member_ids = {m.user_id for m in db.query(DepartmentMember).all()}
    if not member_ids:
        return []
    users = {u.id: u for u in db.query(User).filter(User.id.in_(member_ids)).all()}
    out: List[dict] = []
    for uid in member_ids:
        u = users.get(uid)
        if u is None:
            continue
        for item in required_training_for_user(db, uid, now):
            if item["status"] == "completed":
                continue
            due = item["due_date"]
            is_overdue = item["status"] == "overdue"
            is_due_soon = due is not None and window_end is not None and now <= due <= window_end
            if is_overdue or is_due_soon:
                out.append({
                    "user_id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "content_type": item["content_type"],
                    "course_id": item["course_id"],
                    "broadcast_id": item["broadcast_id"],
                    "title": item["title"],
                    "due_date": item["due_date"],
                    "status": item["status"],
                })
    return out
