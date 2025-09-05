from fastmcp import Client
dialogue='''
 ('0', '喝以狗三个半就前两天拉肚肚一天拉六七次我跟你说')
('0', '阿姆西林比好好呃拉肚肚子拉的有点血丝不算太稀嗯')
('0', '嗯就没用最近受后去取没有一个月以前我已经决役了')
'''

case_snapshot={'name': '', 'phone': '', 'pet_name': '', 'species': '', 'breed': '', 'weight': '', 'deworming': '', 'sterilization': '', 'complaint': ''}
async def send():
    from inspect import signature

    async with Client("server.py") as mcp_client:
       
        tools = await mcp_client.list_tools()
        print(tools)
        _case=None

        next_tool = "run_pipeline"
        params = {"case": case_snapshot,"dialogue": dialogue,"tab": "问诊阶段"}
        
        while next_tool:
           
            result =await  mcp_client.call_tool(next_tool,params)
            data = result.data or {}
            print(f"[{next_tool}] 返回:", data)
            
            
            next_tool = data.get("next_tool") 
            params = data.get("params") 
            _case=params['case']
            
        print("over:"+str(_case))
            
        


import asyncio
asyncio.run(send())