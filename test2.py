# orchestrator_mcp_planner.py
# -*- coding: utf-8 -*-
import os
import json
import asyncio
from typing import Any, Dict, List
from fastmcp import Client

from openai import AsyncOpenAI
from mcp.client.sse import sse_client
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

async def run_orchestrator(case: Dict[str, Any], dialogue: str, max_steps: int = 12) -> Dict[str, Any]:
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
        {"role": "user", "content": f"初始病例：{json.dumps(state_case, ensure_ascii=False)}\n对话：{dialogue}"}
    ]
    

    

    async with Client("server.py") as mcp_client:
        FUNCTIONS=[]
        tools = await mcp_client.list_tools()
        for tool in tools:
            FUNCTIONS.append({"name":tool.name,"description":tool.description,"parameters":tool.inputSchema})
            
        _case=None
        for step in range(1, max_steps + 1):
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

                # 兜底：自动注入缺失的 case / dialogue
                if tool_name in {"stage_checkup", "stage_view_results", "stage_diagnosis"}:
                    args.setdefault("case", state_case)
                    args.setdefault("dialogue", dialogue)
                if tool_name == "fill_case_fields":
                    args.setdefault("case", state_case)
                    args.setdefault("fields", {})

                # 执行 MCP 工具
                try:
                    result = await mcp_client.call_tool(tool_name, args)
                except Exception as e:
                    result = {"error": f"MCP 调用失败: {e.__class__.__name__}: {e}"}

                # 同步本地病例状态（兼容不同返回格式）
                try:
                    if tool_name == "fill_case_fields":
                        # 你的 fill_case_fields 返回 {"next_tool":None, "params":{"case": updated_case}}
                        if isinstance(result, dict):
                            if "params" in result and isinstance(result["params"], dict) and "case" in result["params"]:
                                state_case = result["params"]["case"]
                            elif "case" in result:  # 或者直接返回 case
                                state_case = result["case"]
                    else:
                        # stage_* 可能直接返回 {"fields": {...}}，也可能只返回字段对象
                        if isinstance(result, dict):
                            fields_obj = result.get("fields", result)
                            if isinstance(fields_obj, dict) and fields_obj:
                                # 自动调用 fill_case_fields，把字段合入 case（由模型也可显式调用；这里做兜底）
                                merge_args = {"case": state_case, "fields": fields_obj}
                                merged = await mcp.call("fill_case_fields", merge_args)
                                if isinstance(merged, dict):
                                    if "params" in merged and isinstance(merged["params"], dict) and "case" in merged["params"]:
                                        state_case = merged["params"]["case"]
                                    elif "case" in merged:
                                        state_case = merged["case"]
                except Exception:
                    pass

                # 把“工具调用”与“工具返回”都放回对话上下文，便于模型继续规划
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "function_call": {"name": tool_name, "arguments": json.dumps(args, ensure_ascii=False)}
                })
                messages.append({
                    "role": "function",
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=False)
                })
                # 同步最新病例到对话，便于模型下一步决策
                messages.append({
                    "role": "system",
                    "content": f"（系统提示）病例已更新：{json.dumps(state_case, ensure_ascii=False)}"
                })
                continue

            # 没有再调用工具 => 模型给出最终文本总结，结束
            final_text = msg.content or ""
            return {
                "final_case": state_case,
                "assistant_summary": final_text.strip(),
                "steps": step
            }

        # 超过步数仍未结束
        return {
            "final_case": state_case,
            "assistant_summary": "达到最大步骤上限，已返回当前病例状态。",
            "steps": max_steps
        }

# ========== DEMO ==========
async def _demo():
    case = {
        "case_id": "20250905-001",
        "pet_name": "旺财",
        "phone": "13800001111"
    }
    dialogue = "主人：咳嗽两天，无发热。医生：建议血常规、胸部影像。结果：白细胞轻度升高，影像提示支气管纹理增多。考虑支气管炎，对症治疗。"
    res = await run_orchestrator(case, dialogue)
    print("\n=== 模型总结 ===")
    print(res["assistant_summary"])
    print("\n=== 最终病例 ===")
    print(json.dumps(res["final_case"], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(_demo())
