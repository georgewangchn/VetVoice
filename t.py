import httpx
import asyncio
import json

API_KEY = "sk-zk2b8e4b861c44e947efb87d06380a127a8659f5b74e66a2"
BASE_URL = "http://192.168.1.12:9988/v1"
MODEL = "gemini-2.5-flash-lite-thinking"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": MODEL,
    "messages": [{
        "role": "user",
        "content": "你好"
    }],
    "stream": True
}

async def main():
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", f"{BASE_URL}/chat/completions", headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                print(line)
                if line.startswith("data: "):
                    data = line[len("data: "):].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        print(delta, end="", flush=True)

asyncio.run(main())
