import asyncio

async def fill_case_fields(dialogue: str, case: dict):
    """
    根据对话和已有电子病历，补全或修改字段
    """
    print(f"[fill_case_fields] 收到病例 → {case}")
    print(f"[fill_case_fields] 对话 → {dialogue[:50]}...")

    # 简化逻辑：把 complaint/diagnosis 补全
    updated = case.copy()
    if not updated.get("complaint"):
        updated["complaint"] = "咳嗽两天，伴随体温升高"
    if not updated.get("diagnosis"):
        updated["diagnosis"] = "上呼吸道感染"

    # 模拟耗时
    await asyncio.sleep(0.2)
    print(f"[fill_case_fields] 返回更新结果 → {updated}")
    return {"status": "ok", "updated_case": updated}
