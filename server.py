# mcp_server.py
from fastmcp import FastMCP
import json
from llm_client import  call_llm_function_calling
from loguru import logger
import sys

logger.remove()  # 移除默认的 stdout handler
logger.add(sys.stderr, level="INFO")  # 指定输出到 stderr

mcp = FastMCP(name="宠物疾病诊疗流程 MCP")
# @mcp.tool()
# def determine_stage(case: dict, dialogue: str, tab: str):
#     """
#     判断病例当前阶段，调用 GPT function calling
#     """
#     prompt = f"""
#     请根据病例信息和最新对话判断当前阶段：
#     Case: {json.dumps(case, ensure_ascii=False)}
#     Dialogue: {dialogue}
#     Tab: {tab}
#     可能阶段：问诊阶段 / 开检查阶段 / 查看检查结果阶段 / 确诊治疗阶段
#     """
#     response = await call_llm_function_calling(prompt, functions=[
#         {
#             "name": "determine_stage",
#             "description": "返回病例当前阶段",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "stage": {
#                         "type": "string",
#                         "enum": ["问诊阶段", "开检查阶段", "查看检查结果阶段", "确诊治疗阶段"]
#                     }
#                 },
#                 "required": ["stage"]
#             }
#         }
#     ])
#     stage = response.get("stage", "问诊阶段")
#     return stage

@mcp.tool()
async def stage_inquiry(case: dict, dialogue: str):
    """
    问诊阶段：提取缺失的问诊字段，并指定下一步工具
    """
    prompt = f"""
    请根据病例和对话提取缺失字段：
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    需要提取字段: name, phone, pet_name, species, breed, weight, deworming, sterilization, complaint
    """
    fields = await call_llm_function_calling(prompt, functions=[
        {
            "name": "fill_case_fields",
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
        "fields": fields,
        "next_tool": "fill_case_fields"
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
    case.update(fields or {})

    # 返回更新后的病例和下一步工具（None表示结束）
    return {
        "fileds": case,
        "next_tool": None
    }
@mcp.tool()
async def run_pipeline(case: dict, dialogue: str, tab: str):
    """
    运行病例推理流水线
    """
    prompt = f"""
    请根据病例信息和最新对话判断当前阶段：
    Case: {json.dumps(case, ensure_ascii=False)}
    Dialogue: {dialogue}
    Tab: {tab}
    可能阶段：问诊阶段 / 开检查阶段 / 查看检查结果阶段 / 确诊治疗阶段
    """
    response = await call_llm_function_calling(prompt, functions=[
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
    """运行病例推理流水线"""
   
    logger.info(f"[MCP] 当前阶段: {stage}")

    next_tool_map = {
    "问诊阶段": "stage_inquiry",
    "开检查阶段": "stage_checkup",
    "查看检查结果阶段": "stage_view_results",
    "确诊治疗阶段": "stage_diagnosis"
}
    next_tool = next_tool_map.get(stage, None)

    return {"stage": stage, "next_tool": next_tool}
if __name__ == "__main__":
    mcp.run()

