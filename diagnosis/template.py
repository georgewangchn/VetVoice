DIAGNOSE_TEMPLATE = """
你是一名专业的宠物医生，擅长犬猫等小动物内外科疾病诊疗。
以下是一个接诊医生与宠物主人对话，基于对话内容，给出诊断结果:
对话内容:
{dialogue}
请根据对话内容，给出诊断结果，字数控制在50字以内。
诊断结果:"""

DIAGNOSE_TEMPLATE_REWRITE = """
你是一名专业的宠物医生。
以下是初步诊断结果，请你润色语言，使其更为专业精炼：
原始内容:
{dialogue}
润色后的诊断结果:"""

DIAGNOSE_TEMPLATE_FORMAT = """
你是一名专业的宠物医生。
请你将以下诊断内容进行标准格式化输出：
原始诊断内容:
{dialogue}
格式化后的诊断:"""

COMPLAINT_TEMPLATE = """
你是一名专业的宠物医生。
以下是医生与宠物主人的对话内容，请总结出主诉，用于电子病例填写。
对话内容:
{dialogue}
主诉:"""

COMPLAINT_TEMPLATE_REWRITE = """
你是一名专业的宠物医生。
请对以下主诉内容进行语言润色，使其更为清晰准确：
原始主诉:
{dialogue}
润色后的主诉:"""

COMPLAINT_TEMPLATE_FORMAT = """
你是一名专业的宠物医生。
请将以下主诉内容格式标准化，例如去除口语化词汇、调整语序等：
原始主诉:
{dialogue}
格式化后的主诉:"""

INFO_TEMPLATE = """
你是一名专业的宠物医生。
以下是医生与宠物主人的对话内容，请从中提取出宠物的基本信息，用于电子病例建档。
对话内容:
{dialogue}
请按以下格式返回 JSON：
{{
  "name": "", 
  "phone": "",
  "pet_name": "",
  "species": "",  // 枚举：猫/狗/其他
  "breed": "",    // 枚举：珂基/斗牛/其他
  "weight": "",   // 单位 kg
  "deworming": "",  // 是/否
  "sterilization": ""  // 是/否
}}"""

INFO_TEMPLATE_REWRITE = """
你是一名专业的宠物医生。
请对以下提取的基本信息进行合理润色与补全（如可能缺失的项补空字符串）：
原始信息:
{dialogue}
润色后的 JSON:"""

INFO_TEMPLATE_FORMAT = """
你是一名专业的宠物医生。
请对以下基本信息 JSON 内容进行格式检查和标准化输出：
原始内容:
{dialogue}
格式化后内容:"""


MEDICATION_TEMPLATE = """
你是一名专业的宠物医生。
以下是对话内容，请给出合理的用药建议。
对话内容:
{dialogue}
用药建议:"""

MEDICATION_TEMPLATE_REWRITE = """
你是一名专业的宠物医生。
请对以下用药建议进行专业化修饰，使其表述更准确规范：
原始建议:
{dialogue}
修饰后建议:"""

MEDICATION_TEMPLATE_FORMAT = """
你是一名专业的宠物医生。
请将以下用药建议内容格式标准化，例如分点列出药物和剂量：
原始内容:
{dialogue}
格式化建议:"""


QUALITY_CHECK_TEMPLATE = """
你是一名专业的宠物医生。
请根据医生与宠物主人的对话内容，输出质量检查建议。
对话内容:
{dialogue}
质量检查建议:"""

QUALITY_CHECK_TEMPLATE_REWRITE = """
你是一名专业的宠物医生。
请对以下质检建议进行语句优化和专业术语补充：
原始内容:
{dialogue}
修饰后的建议:"""

QUALITY_CHECK_TEMPLATE_FORMAT = """
你是一名专业的宠物医生。
请将以下质量检查建议标准化格式输出：
原始内容:
{dialogue}
格式化后建议:"""
