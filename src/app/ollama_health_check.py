# python
import os
import asyncio
import httpx

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip('/')

async def health_check():
    print("OLLAMA_HOST =", OLLAMA_HOST)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # check root
            r = await client.get(OLLAMA_HOST + "/")
            print("GET / ->", r.status_code, r.text[:400])
        except Exception as e:
            print("GET / failed:", e)

        try:
            payload = {"model": "greek_ollama_model:1.0.0", "prompt": "καλὸς ὁ ἀγών", "stream": False}
            r = await client.post(OLLAMA_HOST + "/api/generate", json=payload)
            print("POST /api/generate ->", r.status_code)
            print("Response headers:", dict(r.headers))
            print("Body (first 1000 chars):", r.text[:1000])
        except Exception as e:
            print("POST failed:", type(e), e)

if __name__ == "__main__":
    asyncio.run(health_check())
