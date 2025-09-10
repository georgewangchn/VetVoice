# mcp_server.py
from fastmcp import FastMCP
from openai import AsyncOpenAI
import json
from loguru import logger
import sys
from settings import cfg
API_KEY = cfg.get("llm", "api_key").strip()
BASE_URL = cfg.get("llm", "api_base").strip()
MODEL = cfg.get("llm", "model").strip()


logger.remove()  # 移除默认的 stdout handler
logger.add(sys.stderr, level="INFO")  # 指定输出到 stderr

mcp = FastMCP(name="LLM MCP")

@mcp.tool()
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
    msg = resp.choices[0].message
    if msg.function_call:
        args = msg.function_call.arguments
        return json.loads(args)  # 返回 dict
    return {}


if __name__ == "__main__":
    mcp.run()

