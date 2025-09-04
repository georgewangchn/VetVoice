from fastmcp import Client
client = Client('server.py') 
case_id = "case_001" 
dialogue = "主人描述宠物呕吐，精神不振..." 
tab = "🩺 辅诊"
updated_case = client.run_pipeline(case_id, dialogue, tab)
