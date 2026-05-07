"""See exactly what Claude returns for course generation."""
import asyncio
import httpx
import json

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
API_KEY = open('.env').read()
for line in API_KEY.split('\n'):
    if line.startswith('CLAUDE_API_KEY='):
        API_KEY = line.split('=', 1)[1].strip()
        break

async def main():
    prompt = """Generate a course on Railway Safety with 2 modules for beginners.

Return ONLY a JSON object with this exact structure (no markdown, no explanation, just JSON):
{"title":"...","description":"...","difficulty":"beginner","modules":[{"id":1,"title":"...","lessons":[{"id":1,"title":"...","content":"...","learning_outcomes":["..."]}]}]}"""

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
                'x-api-key': API_KEY,
            },
            json={
                'model': 'claude-sonnet-4-6',
                'max_tokens': 2048,
                'messages': [{'role': 'user', 'content': prompt}]
            }
        )
        data = r.json()
        text = data.get('content', [{}])[0].get('text', '')
        print("=== First 500 chars of Claude response ===")
        print(repr(text[:500]))
        print("\n=== Starts with? ===")
        print("```json" in text, "```" in text, text.strip().startswith("{"))

asyncio.run(main())
