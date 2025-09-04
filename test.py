from fastmcp import Client
dialogue='''
 ('0', '喝以狗三个半就前两天拉肚肚一天拉六七次我跟你说')
('0', '阿姆西林比好好呃拉肚肚子拉的有点血丝不算太稀嗯')
('0', '嗯就没用最近受后去取没有一个月以前我已经决役了')
'''

case_snapshot={'name': '', 'phone': '', 'pet_name': '', 'species': '', 'breed': '', 'weight': '', 'deworming': '', 'sterilization': '', 'complaint': ''}
async def send():
    from inspect import signature

    async def call_tool_auto(client, tool_name, context):
        tool_func = getattr(client, tool_name)
        sig = signature(tool_func)
        params = {k: context[k] for k in sig.parameters if k in context}
        return await client.call_tool(tool_name, params)
    async with Client("server.py") as mcp_client:
        context = {
            "case": case_snapshot,
            "dialogue": dialogue,
            "tab": "问诊阶段"
        }

        # 循环执行每一步工具，直到 next_tool 为 None
        next_tool = "run_pipeline"
        while next_tool:
            tool_func = getattr(mcp_client, next_tool)
            sig = signature(tool_func)
            params = {k: context[k] for k in sig.parameters if k in context}
            
            result = mcp_client.call_tool(next_tool,params)
            data = result.data or {}
            print(f"[{next_tool}] 返回:", data)
            
            # 更新上下文，加入新提取的字段
            if "fields" in data:
                context["case"].update(data["fields"])
            
            next_tool = data.get("next_tool")  # 下一步工具


import asyncio
asyncio.run(send())