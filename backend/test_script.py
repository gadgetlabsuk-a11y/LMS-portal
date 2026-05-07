"""Debug script endpoint."""
import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post('http://127.0.0.1:7000/api/auth/login',
                         json={'username': 'admin', 'password': 'LMSadmin2026!'})
        token = r.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        # Check the course content exists
        r2 = await c.get('http://127.0.0.1:7000/api/courses/1', headers=headers)
        course = r2.json()
        print("Course title:", course.get('title'))
        print("Has content:", bool(course.get('content')))
        if course.get('content'):
            print("Content keys:", list(course['content'].keys())[:5])

        # Try script generation
        print("\nGenerating script...")
        r3 = await c.post('http://127.0.0.1:7000/api/courses/1/generate-script',
                          headers=headers)
        print("Status:", r3.status_code)
        if r3.is_success:
            print("Size:", len(r3.content), "bytes")
            with open('/tmp/test_script.docx', 'wb') as f:
                f.write(r3.content)
            print("Saved to /tmp/test_script.docx")
        else:
            print("Error:", r3.text[:500])

asyncio.run(main())
