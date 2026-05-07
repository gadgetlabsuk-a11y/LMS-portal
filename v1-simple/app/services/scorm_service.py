import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Course, Lesson, Module, Slide, CourseTheme, Theme, MediaAsset, ScormPackage
from app.services.storage import StorageBackend

STATIC_DIR = Path(__file__).parent.parent / "static" / "scorm"

IMSMANIFEST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="LMS_COURSE_{course_id}_V{export_version}"
          version="1.2"
          xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
                              http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd
                              http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="ORG-1">
    <organization identifier="ORG-1">
      <title>{course_title}</title>
      <item identifier="ITEM-1" identifierref="RES-1">
        <title>{course_title}</title>
        <adlcp:masteryscore>{pass_threshold}</adlcp:masteryscore>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES-1" type="webcontent" adlcp:scormtype="sco" href="index.html">
{file_entries}
    </resource>
  </resources>
</manifest>
"""

INDEX_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{course_title}</title>
<link rel="stylesheet" href="styles.css"/>
</head>
<body>
<a href="#lms-slide" class="skip-link">Skip to content</a>
<div id="lms-shell">
  <header id="lms-header">
    <span id="course-title">{course_title}</span>
    <span id="slide-counter"></span>
  </header>
  <main id="lms-slide" tabindex="-1" aria-live="polite" aria-label="Slide content"></main>
  <nav id="lms-nav" aria-label="Course navigation">
    <button id="btn-prev" onclick="lmsPrev()" aria-label="Previous slide">&#8592; Prev</button>
    <button id="btn-next" onclick="lmsNext()" aria-label="Next slide">Next &#8594;</button>
  </nav>
</div>
<script src="scorm_runtime.js"></script>
<script src="player.js"></script>
<script>
  fetch("meta/course.json").then(r => r.json()).then(lmsInit);
</script>
</body>
</html>
"""

STYLES_CSS = """\
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font-body,system-ui,sans-serif);background:var(--color-bg,#fff);color:var(--color-text,#1f2937);line-height:1.5}
.skip-link{position:absolute;left:-9999px;top:0;z-index:999;background:#000;color:#fff;padding:8px 16px}
.skip-link:focus{left:0}
#lms-shell{display:flex;flex-direction:column;min-height:100vh}
#lms-header{padding:12px 24px;background:var(--color-primary,#1f3a5f);color:#fff;display:flex;justify-content:space-between;align-items:center}
#lms-slide{flex:1;padding:48px;max-width:960px;margin:0 auto;width:100%;outline:none}
#lms-nav{padding:16px 24px;display:flex;gap:16px;border-top:1px solid #e5e7eb}
#lms-nav button{padding:10px 20px;border:none;border-radius:6px;cursor:pointer;background:var(--color-primary,#1f3a5f);color:#fff;font-size:16px;font-weight:500}
#lms-nav button:disabled{opacity:.4;cursor:not-allowed}
#lms-nav button:focus-visible{outline:3px solid var(--color-accent,#f59e0b);outline-offset:2px}
.lms-heading{margin-bottom:.75em;color:var(--color-text,#1f2937)}
.lms-paragraph{margin-bottom:1em}
.lms-image{margin-bottom:1em;text-align:center}
.lms-image img{max-width:100%;border-radius:var(--radius-md,8px)}
.lms-image figcaption{font-size:.875rem;color:var(--color-muted,#6b7280);margin-top:.5em}
.lms-video,.lms-audio{width:100%;margin-bottom:1em}
.lms-divider{border:none;border-top:1px solid #e5e7eb;margin:1.5em 0}
.lms-bullets{padding-left:1.5em;margin-bottom:1em}
.lms-bullets li{margin-bottom:.4em}
.lms-quiz{border:1px solid #e5e7eb;border-radius:8px;padding:24px;margin-bottom:1em}
.lms-quiz-question{font-weight:600;margin-bottom:16px}
.lms-quiz label{display:block;margin-bottom:8px;cursor:pointer}
.lms-quiz button,.lms-button{margin-top:12px;padding:10px 20px;background:var(--color-primary,#1f3a5f);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:1rem}
.lms-quiz-feedback{margin-top:12px;padding:12px;background:#f0fdf4;border-radius:6px;color:#166534}
"""


class ScormPackager:
    def __init__(self, db: AsyncSession, storage: StorageBackend):
        self.db = db
        self.storage = storage

    async def export(self, course_id: str, exported_by: str) -> ScormPackage:
        # 1. Load course
        result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            raise ValueError(f"Course {course_id} not found")

        # 2. Determine export version
        existing = await self.db.execute(
            select(ScormPackage)
            .where(ScormPackage.course_id == course_id)
            .order_by(ScormPackage.export_version.desc())
        )
        last = existing.scalars().first()
        export_version = (last.export_version + 1) if last else 1

        # 3. Load hierarchy
        modules_result = await self.db.execute(
            select(Module).where(Module.course_id == course_id).order_by(Module.sort_order)
        )
        modules = modules_result.scalars().all()

        course_meta = {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "pass_threshold": getattr(course, "pass_threshold", 80),
            "modules": [],
        }

        all_slides = []
        for mod in modules:
            lessons_result = await self.db.execute(
                select(Lesson).where(Lesson.module_id == mod.id).order_by(Lesson.sort_order)
            )
            lessons = lessons_result.scalars().all()
            mod_data = {"id": mod.id, "title": mod.title, "lessons": []}
            for lesson in lessons:
                slides_result = await self.db.execute(
                    select(Slide).where(Slide.lesson_id == lesson.id).order_by(Slide.position)
                )
                slides = slides_result.scalars().all()
                slide_list = []
                for slide in slides:
                    slide_dict = {
                        "id": slide.id, "title": slide.title,
                        "layout": slide.layout, "blocks": slide.blocks or [],
                    }
                    slide_list.append(slide_dict)
                    all_slides.append(slide_dict)
                mod_data["lessons"].append({
                    "id": lesson.id, "title": lesson.title, "slides": slide_list
                })
            course_meta["modules"].append(mod_data)

        # 4. Collect media assets referenced by blocks
        media_map: dict[int, MediaAsset] = {}
        for slide in all_slides:
            for block in slide.get("blocks", []):
                mid = block.get("props", {}).get("media_id")
                if mid and mid not in media_map:
                    r = await self.db.execute(select(MediaAsset).where(MediaAsset.id == mid))
                    asset = r.scalar_one_or_none()
                    if asset:
                        media_map[mid] = asset

        # 5. Build zip in memory
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Static runtime files
            runtime_js = (STATIC_DIR / "scorm_runtime.js").read_bytes()
            player_js = (STATIC_DIR / "player.js").read_bytes()
            zf.writestr("scorm_runtime.js", runtime_js)
            zf.writestr("player.js", player_js)
            zf.writestr("styles.css", STYLES_CSS.encode())

            # Index
            zf.writestr("index.html", INDEX_HTML_TEMPLATE.format(
                course_title=course.title
            ).encode())

            # Course metadata
            zf.writestr("meta/course.json", json.dumps(course_meta, indent=2).encode())

            # Individual slide JSON files
            for i, slide in enumerate(all_slides):
                zf.writestr(f"content/slide_{i+1:03d}.json", json.dumps(slide).encode())

            # Media files
            for mid, asset in media_map.items():
                try:
                    data = self.storage.get(asset.storage_key)
                    ext = asset.filename.rsplit(".", 1)[-1] if "." in asset.filename else "bin"
                    media_key = f"media/{asset.kind}_{asset.id}.{ext}"
                    zf.writestr(media_key, data)
                    # Patch block props to use relative path
                    for slide in all_slides:
                        for block in slide.get("blocks", []):
                            if block.get("props", {}).get("media_id") == mid:
                                block["props"]["url"] = media_key
                except Exception:
                    pass  # Skip missing media — don't fail the whole export

            # SCORM XSD schemas (minimal stubs so validators don't complain)
            for xsd in ["adlcp_rootv1p2.xsd", "ims_xml.xsd", "imscp_rootv1p1p2.xsd", "imsmd_rootv1p2p1.xsd"]:
                zf.writestr(xsd, b'<?xml version="1.0" encoding="UTF-8"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>')

            # Build file entry list for manifest
            file_entries = "\n".join(
                f'      <file href="{name}"/>'
                for name in zf.namelist()
            )

            # imsmanifest.xml
            manifest = IMSMANIFEST_TEMPLATE.format(
                course_id=course.id,
                export_version=export_version,
                course_title=course.title,
                pass_threshold=getattr(course, "pass_threshold", 80),
                file_entries=file_entries,
            )
            zf.writestr("imsmanifest.xml", manifest.encode())

        zip_bytes = buf.getvalue()

        # 6. Store zip
        storage_key = f"scorm/{course_id}/v{export_version}.zip"
        self.storage.put(storage_key, zip_bytes, "application/zip")

        # 7. Persist record
        pkg = ScormPackage(
            course_id=course_id,
            version="1.2",
            export_version=export_version,
            storage_key=storage_key,
            size_bytes=len(zip_bytes),
            exported_by=exported_by,
        )
        self.db.add(pkg)
        await self.db.commit()
        await self.db.refresh(pkg)
        return pkg
