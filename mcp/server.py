# mcp_server.py
from fastmcp import FastMCP
import json
from llm_client import call_llm_function_calling
from loguru import logger
mcp = FastMCP(name="宠物疾病诊疗流程 MCP")
@mcp.tool()
def determine_stage(case: dict, dialogue: str, tab: str):
    """
    判断病例当前阶段，调用 GPT function calling
    """
    prompt = f"""
    请根据病例信息和最新对话判断当前阶段：
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    Tab: {tab}
    可能阶段：问诊阶段 / 开检查阶段 / 查看检查结果阶段 / 确诊治疗阶段
    """
    response = call_llm_function_calling(prompt, functions=[
        {
            "name": "determine_stage",
            "description": "返回病例当前阶段",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {
                        "type": "string",
                        "enum": ["问诊阶段", "开检查阶段", "查看检查结果阶段", "确诊治疗阶段"]
                    }
                },
                "required": ["stage"]
            }
        }
    ])
    stage = response.get("stage", "问诊阶段")
    return stage

@mcp.tool()
def stage_inquiry(case: dict, dialogue: str):
    """
    问诊阶段：提取缺失的问诊字段
    """
    prompt = f"""
    请根据病例和对话提取缺失字段：
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    需要提取字段: name, phone, pet_name, species, breed, weight, deworming, sterilization, complaint
    """
    fields = call_llm_function_calling(prompt, functions=[
        {
            "name": "fill_case_fields",
            "description": "提取字段并返回 JSON",
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
def stage_checkup(case: dict, dialogue: str):
    prompt = f"""
    根据病例和对话生成推荐检查
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    """
    fields = call_llm_function_calling(prompt, functions=[
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
def stage_view_results(case: dict, dialogue: str):
    prompt = f"""
    根据病例和对话提取检查结果
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    """
    fields = call_llm_function_calling(prompt, functions=[
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
def stage_diagnosis(case: dict, dialogue: str):
    prompt = f"""
    根据病例和对话提取诊断和治疗
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    """
    fields = call_llm_function_calling(prompt, functions=[
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
def fill_case_fields(case: dict, fields: dict):
    """
    更新 case_store
    """
    case.update(fields)
    return case
@mcp.tool()
def run_pipeline(case: dict, dialogue: str, tab: str):
    stage = determine_stage(case, dialogue, tab)
    print(f"[MCP] 当前阶段: {stage}")
    if stage == "问诊阶段":
        fields = stage_inquiry(case, dialogue)
    elif stage == "开检查阶段":
        fields = stage_checkup(case, dialogue)
    elif stage == "查看检查结果阶段":
        fields = stage_view_results(case, dialogue)
    elif stage == "确诊治疗阶段":
        fields = stage_diagnosis(case, dialogue)
    else:
        fields = {}

    updated_case = fill_case_fields(case, fields)
    return updated_case


