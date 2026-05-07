"""Unit tests for SCORM manifest generation."""
import zipfile
import io
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.scorm_service import IMSMANIFEST_TEMPLATE, STYLES_CSS, ScormPackager


def test_manifest_template_has_required_elements():
    manifest = IMSMANIFEST_TEMPLATE.format(
        course_id="123",
        export_version=1,
        course_title="Test Course",
        pass_threshold=80,
        file_entries="      <file href=\"index.html\"/>",
    )
    assert "ADL SCORM" in manifest
    assert "1.2" in manifest
    assert "adlcp:masteryscore" in manifest
    assert "80" in manifest
    assert "Test Course" in manifest
    assert "LMS_COURSE_123_V1" in manifest


def test_styles_css_has_skip_link():
    assert "skip-link" in STYLES_CSS
    assert "focus" in STYLES_CSS


def test_styles_css_has_aria_live():
    # player shell uses aria-live; check CSS supports the live region
    assert "lms-slide" in STYLES_CSS
