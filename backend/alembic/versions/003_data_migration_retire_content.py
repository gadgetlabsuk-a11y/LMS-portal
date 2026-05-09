"""Migrate Course.content JSON blob to relational Module/Video rows. Null out content column.

Revision ID: 003
Revises: 002
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def _migrate_course_content(connection, course_id, content_json):
    """Parse a Course.content JSON blob and insert Module/Video rows."""
    import json as json_lib

    if isinstance(content_json, str):
        try:
            content = json_lib.loads(content_json)
        except (json_lib.JSONDecodeError, TypeError):
            print(f"  WARNING: Course {course_id} content is not valid JSON — skipping")
            return
    elif isinstance(content_json, dict):
        content = content_json
    else:
        print(f"  WARNING: Course {course_id} content type {type(content_json)} — skipping")
        return

    modules = content.get('modules', [])
    if not modules:
        # No structured content — nothing to migrate
        return

    now = datetime.utcnow().isoformat()

    for mod_idx, module_data in enumerate(modules):
        if not isinstance(module_data, dict):
            continue
        title = module_data.get('title') or module_data.get('name') or f"Module {mod_idx + 1}"

        result = connection.execute(
            sa.text(
                "INSERT INTO modules (course_id, order_index, title, description, status, created_at) "
                "VALUES (:course_id, :order_index, :title, :description, 'draft', :created_at)"
            ),
            {
                'course_id': course_id,
                'order_index': mod_idx,
                'title': title[:500],
                'description': module_data.get('description'),
                'created_at': now,
            }
        )
        module_id = result.lastrowid

        # Content JSON uses 'lessons' key; also handle 'videos' for future compatibility
        videos = module_data.get('videos', module_data.get('lessons', []))
        for vid_idx, video_data in enumerate(videos):
            if not isinstance(video_data, dict):
                continue
            vid_title = video_data.get('title') or video_data.get('name') or f"Video {vid_idx + 1}"
            connection.execute(
                sa.text(
                    "INSERT INTO videos (module_id, order_index, title, description, video_type, status, created_at) "
                    "VALUES (:module_id, :order_index, :title, :description, 'slideshow_narrated', 'draft', :created_at)"
                ),
                {
                    'module_id': module_id,
                    'order_index': vid_idx,
                    'title': vid_title[:500],
                    'description': video_data.get('description'),
                    'created_at': now,
                }
            )


def upgrade() -> None:
    connection = op.get_bind()

    # Fetch all courses that still have content
    courses = connection.execute(
        sa.text("SELECT id, content FROM courses WHERE content IS NOT NULL")
    ).fetchall()

    print(f"\nData migration: {len(courses)} course(s) with content to migrate")

    for row in courses:
        course_id = row[0]
        content_json = row[1]
        print(f"  Migrating course {course_id}...")
        try:
            _migrate_course_content(connection, course_id, content_json)
        except Exception as exc:
            print(f"  WARNING: Course {course_id} migration failed: {exc} — content preserved, continuing")

    # Null out content on all rows (column still exists; drop happens in 004)
    connection.execute(sa.text("UPDATE courses SET content = NULL"))
    print("  content column nulled on all courses")


def downgrade() -> None:
    # Cannot restore JSON blobs — downgrade is a no-op for data
    # The content column is restored by 004's downgrade (add column back) and
    # 002's downgrade (tables dropped). Data is not recoverable without a backup.
    print("WARNING: 003 downgrade is a no-op — Course.content data is not recoverable from this migration alone")
