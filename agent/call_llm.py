# llm_client.py
import openai
import os
import json
import os
from openai import AsyncOpenAI
import openai
import requests
import time
import json
import time
from settings import cfg
API_KEY = cfg.get("llm", "api_key").strip()
BASE_URL = cfg.get("llm", "api_base").strip()
MODEL = cfg.get("llm", "model").strip()


async def call_llm_function_calling(prompt: str, functions: list):
    """
    使用 OpenAI GPT function calling 调用 LLM (async / 新接口)
    """
   
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    resp =  await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        functions=functions,
        function_call="auto"
    )
    print(resp)


    msg = resp.choices[0].message
    if msg.function_call:
        args = msg.function_call.arguments
        return json.loads(args)  # 返回 dict
    return {}