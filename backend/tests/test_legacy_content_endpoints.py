"""Regression tests for the retired ``course.content`` endpoints.

The v1.0 milestone replaced the legacy JSON ``course.content`` blob with the
relational Module/Video/Slide/Block model, but the player and export endpoints
still expected the old shape. Because ``Course`` no longer has a ``content``
column, reading ``course.content`` raised ``AttributeError`` -> HTTP 500.

These tests pin the graceful-degradation behaviour: the player returns a clean
200 placeholder page and the export endpoints return a clear 400 (never a 500)
for courses built with the slide editor.
"""


def test_player_returns_placeholder_not_500(client, published_course):
    """The embedded player must degrade to a friendly 200 page, not 500."""
    resp = client.get(f"/api/courses/{published_course.id}/player")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text.lower()
    assert "preview" in body
    # The placeholder must not leak a server error / stack trace.
    assert "attributeerror" not in body
    assert "player generation failed" not in body


def test_player_missing_course_still_404(client):
    resp = client.get("/api/courses/999999/player")
    assert resp.status_code == 404


def test_generate_script_returns_clean_400(client, creator_course, creator_token):
    resp = client.post(
        f"/api/courses/{creator_course.id}/generate-script",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 400
    assert "slide editor" in resp.json()["detail"].lower()


def test_generate_slides_returns_clean_400(client, creator_course, creator_token):
    resp = client.post(
        f"/api/courses/{creator_course.id}/generate-slides",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 400
    assert "slide editor" in resp.json()["detail"].lower()


def test_generate_voiceover_returns_clean_400(client, creator_course, creator_token):
    resp = client.post(
        f"/api/courses/{creator_course.id}/generate-voiceover",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 400
    assert "slide editor" in resp.json()["detail"].lower()
