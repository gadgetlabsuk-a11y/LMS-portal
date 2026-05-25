"""Tests for the admin integration-settings (API-key) feature."""
import pytest

from config import settings
from routers.tts import tts_service
from services import integration_settings_service as svc


@pytest.fixture
def restore_settings():
    """Snapshot/restore the process-global API-key settings (apply_ mutates them)."""
    saved = (
        settings.ELEVENLABS_API_KEY,
        settings.DEEPGRAM_API_KEY,
        settings.CLAUDE_API_KEY,
    )
    # Reset any TTSService instance override so the property reads live settings.
    saved_override = tts_service._api_key_override
    tts_service._api_key_override = None
    yield
    (
        settings.ELEVENLABS_API_KEY,
        settings.DEEPGRAM_API_KEY,
        settings.CLAUDE_API_KEY,
    ) = saved
    tts_service._api_key_override = saved_override


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_get_integrations_requires_admin(client, creator_token):
    res = client.get("/api/admin/integrations", headers=_auth(creator_token))
    assert res.status_code == 403


def test_get_integrations_reports_unconfigured(client, admin_token, db, restore_settings):
    settings.ELEVENLABS_API_KEY = ""
    settings.DEEPGRAM_API_KEY = ""
    settings.CLAUDE_API_KEY = "sk-default-key"  # placeholder == not configured
    res = client.get("/api/admin/integrations", headers=_auth(admin_token))
    assert res.status_code == 200
    providers = res.json()["providers"]
    assert set(providers) == {"elevenlabs", "deepgram", "claude", "heygen"}
    assert providers["elevenlabs"]["configured"] is False
    assert providers["claude"]["configured"] is False
    # Never leak the raw key.
    assert providers["elevenlabs"]["masked"] is None


def test_put_sets_key_masked_and_live(client, admin_token, db, restore_settings):
    settings.ELEVENLABS_API_KEY = ""
    res = client.put(
        "/api/admin/integrations",
        json={"elevenlabs_api_key": "el-secret-abcd1234"},
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    el = res.json()["providers"]["elevenlabs"]
    assert el["configured"] is True
    assert el["source"] == "database"
    assert el["masked"].endswith("1234")
    assert "secret" not in el["masked"]  # body of key is masked
    # Applied live: settings + the TTSService singleton both see the new key.
    assert settings.ELEVENLABS_API_KEY == "el-secret-abcd1234"
    assert tts_service.api_key == "el-secret-abcd1234"


def test_put_requires_admin(client, creator_token):
    res = client.put(
        "/api/admin/integrations",
        json={"deepgram_api_key": "x"},
        headers=_auth(creator_token),
    )
    assert res.status_code == 403


def test_clearing_key_removes_db_value_and_reverts_live(client, admin_token, db, restore_settings):
    settings.DEEPGRAM_API_KEY = ""  # no env value in the test environment
    client.put(
        "/api/admin/integrations",
        json={"deepgram_api_key": "dg-key-9999"},
        headers=_auth(admin_token),
    )
    row = svc.get_or_create_settings(db)
    assert row.deepgram_api_key == "dg-key-9999"
    assert settings.DEEPGRAM_API_KEY == "dg-key-9999"  # applied live
    # Empty string clears it: DB row cleared AND the live value reverts to env ("").
    res = client.put(
        "/api/admin/integrations",
        json={"deepgram_api_key": ""},
        headers=_auth(admin_token),
    )
    db.refresh(row)
    assert row.deepgram_api_key is None
    assert settings.DEEPGRAM_API_KEY == ""  # stale override does not linger
    assert res.json()["providers"]["deepgram"]["configured"] is False
