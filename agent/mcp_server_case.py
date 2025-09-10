# mcp_server.py
from fastmcp import FastMCP
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from loguru import logger

logger.remove()  # 移除默认的 stdout handler
logger.add(sys.stderr, level="INFO")  # 指定输出到 stderr
from agent.call_llm import  call_llm_function_calling

mcp = FastMCP(name="宠物疾病诊疗流程 MCP")

@mcp.tool()
async def stage_inquiry(case: dict, dialogue: str):
    """
    问诊阶段工具：从对话中提取病例缺失字段，并指定下一步调用的工具。

    参数:
        case (dict): 当前电子病历字段及已知的值，例如:
            {
                "name": "",s
                "phone": "",
                "pet_name": "",
                "species": "",
                "breed": "",
                "weight": "",
                "deworming": "",
                "sterilization": "",
                "complaint": ""
            }
        dialogue (str): 医生与宠物主的对话文本。

    返回:
        dict: 一个包含以下键的字典:
            - next_tool (str): 下一个需要调用的工具名，例如 "fill_case_fields"。
            - params
                - case 输入的case直接原始返回
                - fields (dict): 通过dialogue可以提取提取出的字段与值，例如 {"name": "张三", "pet_name": "小黑"}。

    """
    prompt = f"""
    请根据病例和对话提取缺失字段：
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    需要提取字段: name, phone, pet_name, species, breed, weight, deworming, sterilization, complaint
    其中：specide:狗/猫/其他
        deworming:是/否
        sterilization：是/否
        

    """
    fields = await call_llm_function_calling(prompt, functions=[
        {
            "name": "get_case_fields",
            "description": "提取字段并返回 JSON 字典",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "pet_name": {"type": "string"},
                    "species": {"type": "string"},
                    "breed": {"type": "string"},
                    "weight": {"type": "string"},
                    "deworming": {"type": "string"},
                    "sterilization": {"type": "string"},
                    "complaint": {"type": "string"}
                },
                "required": []
            }
        }
    ])
    
    # 返回一个字典，包含字段和下一步工具名
    return {
        "next_tool": "fill_case_fields",
        "params":{"case":case,"fields":fields}
    }

@mcp.tool()
async def stage_checkup(case: dict, dialogue: str):
    prompt = f"""
    根据病例和对话生成推荐检查
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    """
    fields = await call_llm_function_calling(prompt, functions=[
        {
            "name": "fill_case_fields",
            "description": "生成推荐检查",
            "parameters": {
                "type": "object",
                "properties": {
                    "fields": {"type": "object"}
                },
                "required": ["fields"]
            }
        }
    ])
    return fields.get("fields", {})

@mcp.tool()
async def stage_view_results(case: dict, dialogue: str):
    prompt = f"""
    根据病例和对话提取检查结果
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    """
    fields = await call_llm_function_calling(prompt, functions=[
        {
            "name": "fill_case_fields",
            "description": "提取检查结果字段",
            "parameters": {
                "type": "object",
                "properties": {
                    "fields": {"type": "object"}
                },
                "required": ["fields"]
            }
        }
    ])
    return fields.get("fields", {})
@mcp.tool()
async def stage_diagnosis(case: dict, dialogue: str):
    prompt = f"""
    根据病例和对话提取诊断和治疗
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    """
    fields = await call_llm_function_calling(prompt, functions=[
        {
            "name": "fill_case_fields",
            "description": "提取诊断和治疗字段",
            "parameters": {
                "type": "object",
                "properties": {
                    "fields": {"type": "object"}
                },
                "required": ["fields"]
            }
        }
    ])
    return fields.get("fields", {})
@mcp.tool()
async def fill_case_fields(case: dict, fields: dict):
    """
    填充病例字段工具
    - case: 当前病例字典
    - fields: 待更新的字段字典
    返回：
    - 更新后的病例字典
    - next_tool: None 表示流程结束
    """
    # 更新病例
    for k,v in fields.items():
        if not v or not v.strip():
            continue
        case[k]=v

    # 返回更新后的病例和下一步工具（None表示结束）
    return {
        "next_tool": None,
        "params":{"case": case}
    }

if __name__ == "__main__":
    mcp.run()

