# orchestrator_mcp_planner.py
# -*- coding: utf-8 -*-
import os
import json
import asyncio
from typing import Any, Dict, List
from fastmcp import Client
from PySide6.QtCore import QObject, Signal

from openai import AsyncOpenAI
from settings import cfg

API_KEY = cfg.get("llm", "api_key").strip()
BASE_URL = cfg.get("llm", "api_base").strip()
MODEL = cfg.get("llm", "model").strip()

SYSTEM_PROMPT = """你是一个兽医诊疗流程编排助手。一个流程有4个阶段：问诊阶段 / 开检查阶段 / 查看检查结果阶段 / 确诊治疗阶段。你可以调用如下工具：
- stage_inquiry(case, dialogue): 问诊阶段：从对话中提取病例缺失字段，返回应写入的 fields（例如 complaint 等）。
- stage_checkup(case, dialogue): 开检查阶段：基于病例与对话，给出推荐检查，返回应写入的 fields（例如 checkup 等）。
- stage_view_results(case, dialogue): 查看检查结果阶段：从对话中提取检查结果，返回应写入的 fields（例如 results 等）。
- stage_diagnosis(case, dialogue): 确诊治疗阶段：从对话中提取诊断与治疗方案，返回应写入的 fields（例如 diagnosis、treatment 等）。
- fill_case_fields(case, fields): 填写病历：将 fields 合并进 case，并返回更新后的 case。

规则：
1) 你应当根据当前上下文自适应地选择调用哪些工具以及调用顺序；必要时可以重复调用某些工具。
2) 每当你通过某个 stage_* 得到新的字段，需要再调用 fill_case_fields 将其合并到 case。
3) 当你认为 case 已经完整到可以结束时，请直接给出最终总结（自然语言），不要再调用工具。
4) 不要臆造字段；当无法确定字段时可省略或标记为未知。
5) 不要臆造数据；所有字段值来源，应来自对话内容。
注意：当你调用工具时，请在 function_call.arguments 中以 JSON 明确包含 `case`（当前病例）和 `dialogue`；例如：{\"case\": {...}, \"dialogue\": \"...\"}。"},
"""

def _safe_json_loads(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s) if isinstance(s, str) else (s or {})
    except Exception:
        # 尝试修复常见 JSON 问题
        s2 = s.replace("\n", " ").replace("\t", " ")
        try:
            return json.loads(s2)
        except Exception:
            return {}

async def run_orchestrator(case: Dict[str, Any], dialogue: str,stream_signal:Signal,tab_name:str ) -> Dict[str, Any]:
    """
    自适应流程编排：
    - 让模型通过 function calling 选择调用哪个工具（stage_* 或 fill_case_fields）
    - 我们把调用转发给 MCP 同名工具
    - 模型不再调工具而直接回复时，流程结束
    """
    llm_client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    state_case = dict(case)  # 本地持有的病例状态

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"初始病例：case = {json.dumps(state_case, ensure_ascii=False)}\n对话：dialogue = {dialogue}"}
    ]
    
    stream_signal.emit(tab_name, "Step 判断当前病例所在阶段\n")
    async with Client("agent/mcp_server_case.py") as mcp_client:
        FUNCTIONS=[]
        tools = await mcp_client.list_tools()
        for tool in tools:
            FUNCTIONS.append({"name":tool.name,"description":tool.description,"parameters":tool.inputSchema})
            
        _case=None
        resp = await llm_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                functions=FUNCTIONS,
                function_call="auto",
                temperature=0.0,
                max_tokens=8072
            )
        msg = resp.choices[0].message

            # 如果模型选择调用某个工具
        if getattr(msg, "function_call", None):
                tool_name = msg.function_call.name
                raw_args = msg.function_call.arguments or "{}"
                args = _safe_json_loads(raw_args)

                # 执行 MCP 工具
                while tool_name:
                    stream_signal.emit(tab_name, f"Step 执行{tool_name}\n")
                    result = await mcp_client.call_tool(tool_name, args)
                    tool_name = result.data['next_tool']
                    args = result.data['params']
                tcase=args['case']
                stream_signal.emit(tab_name, f"完成,病例:\n{json.dumps(tcase, ensure_ascii=False, indent=2)}\n")
                
                return  tcase
        else:
             stream_signal.emit(tab_name, "失败，可能模型不支持mcp，无法获取function_call\n")
                
            

# # ========== DEMO ==========
# async def _demo():
#     case = {
#         "case_id": "20250905-001",
#         "pet_name": "旺财",
#         "phone": "13800001111"
#     }
#     dialogue = "主人：咳嗽两天，无发热。医生：建议血常规、胸部影像。结果：白细胞轻度升高，影像提示支气管纹理增多。考虑支气管炎，对症治疗。"
#     final_case = await run_orchestrator(case, dialogue)
#     print(json.dumps(final_case, ensure_ascii=False, indent=2))

# if __name__ == "__main__":
#     asyncio.run(_demo())
