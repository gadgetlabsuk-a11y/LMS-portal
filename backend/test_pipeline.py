"""Full pipeline test — course → slides → script → voiceover → player."""
import asyncio
import httpx
import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
BASE = "http://127.0.0.1:7000"

async def main():
    async with httpx.AsyncClient(timeout=300) as client:

        # 1. Login
        r = await client.post(f"{BASE}/api/auth/login",
                              json={"username": "admin", "password": "LMSadmin2026!"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✓ Logged in")

        # 2. Generate course (with wizard params)
        print("  Generating course (calling Claude)...")
        r = await client.post(f"{BASE}/api/courses/generate",
                              json={
                                  "topic": "Railway Safety Fundamentals",
                                  "num_modules": 1,
                                  "difficulty": "beginner",
                                  "videos_per_module": 1,
                                  "video_duration": "short",
                                  "tone": "formal",
                                  "target_audience": "new_starters",
                                  "include_assessment": True,
                              },
                              headers=headers)
        data = r.json()
        if "detail" in data:
            print(f"✗ Generation failed: {data['detail']}")
            return

        content = data.get("content", {})
        course = content.get("course", content)
        print(f"✓ Course generated: '{course.get('title', '?')}'")
        print(f"  Modules: {len(course.get('modules', []))}, Tokens: {data.get('tokens_used', 0)}")

        # 3. Save course
        r2 = await client.post(f"{BASE}/api/courses",
                               json={"title": course.get("title", "Test Course"),
                                     "description": course.get("description", "")},
                               headers=headers)
        if not r2.is_success:
            print(f"✗ Save failed: {r2.text}")
            return
        course_id = r2.json()["id"]
        print(f"✓ Course saved (ID: {course_id})")

        # 4. Attach content
        await client.put(f"{BASE}/api/courses/{course_id}",
                         json={"content": course}, headers=headers)
        print("✓ Content attached")

        # 5. Generate slides
        print("  Generating slides...")
        r4 = await client.post(f"{BASE}/api/courses/{course_id}/generate-slides", headers=headers)
        if r4.is_success:
            with open("/tmp/test_slides.pptx", "wb") as f: f.write(r4.content)
            print(f"✓ Slides: {len(r4.content)/1024:.1f} KB")
        else:
            print(f"✗ Slides failed: {r4.text[:200]}")

        # 6. Generate voiceover (ElevenLabs)
        print("  Generating voiceover (ElevenLabs)...")
        r5 = await client.post(f"{BASE}/api/courses/{course_id}/generate-voiceover", headers=headers)
        if r5.is_success:
            vdata = r5.json()
            print(f"✓ Voiceover: {len(vdata.get('audio_urls', {}))} audio files generated")
        else:
            print(f"✗ Voiceover failed: {r5.text[:300]}")

        # 7. Open player
        print("  Loading player...")
        r6 = await client.get(f"{BASE}/api/courses/{course_id}/player")
        if r6.is_success:
            with open("/tmp/test_player.html", "w") as f: f.write(r6.text)
            print(f"✓ Player: {len(r6.text)/1024:.1f} KB HTML → /tmp/test_player.html")
        else:
            print(f"✗ Player failed: {r6.text[:200]}")

        print(f"\n✓ Pipeline complete. Open player: http://127.0.0.1:7000/api/courses/{course_id}/player")

asyncio.run(main())
