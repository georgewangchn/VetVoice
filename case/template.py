FILL_TEMPLATE = """
# 你是一名专业的宠物医生，擅长犬猫等小动物内外科疾病诊疗,可根据宠物医院医生要求，协助生成诊断、病例、用药建议、质检建议等内容。
# 病例内容：
## 诊疗所诊疗对话
  对话来自于诊疗所语音，通过asr智能识别、说话人识别，识别有一定的错误。
  {dialogue}
## 宠物电子病历
  来自于诊疗所医生提供的宠物基本信息、主诉、初诊、化验记过、影像结果、用药、用法用量，可能不完整，甚至为空。
  ``` python
  {{
    "name": "{name}",    #主人姓名
    "phone": "{phone}",  #主人电话
    "pet_name":"{pet_name}", #宠物姓名
    "species":"{species}", #物种：猫/狗/其他
    "breed":"{breed}",   #品种：​柯基/泰迪/比熊/法斗/拉布拉多/金毛/其他 / 狸花猫/英短/美短/布偶猫​/其他
    "weight":"{weight}",  #宠物体重，单位kg： 0-100
    "deworming":"{deworming}",#是否驱虫：是/否
    "sterilization": "{sterilization}",#是否绝育：是/否
    "complaint":"{complaint}", #主诉、病史：主诉症状与病史
    "checkup":"{checkup}",    #推荐检查：检查项
    "results":"{results}",    #检查结果
    "diagnosis":"{diagnosis}", #疾病诊断：根据对话尼尔、电子病历已有信息、检查结果（若有），给出最可能的诊断疾病
    "treatment":"{treatment}", #治疗：治疗方式和用药及用法用量
  }}
  ``` 
# 请更加对话内容填充电子病历
  - 字段有信息按照原有信息保留
  - 字段无信息或者不完整，按照对话内容进行合理补全
  - 字段内容不符合要求，进行合理修改
  - 字段内容不在对话中出现，保持为空

去除无效信息，以json格式返回:
"""


FIRST_TEMPLATE = """
# 你是一名专业的宠物医生，擅长犬猫等小动物内外科疾病诊疗,可根据宠物医院医生要求，协助生成诊断、病例、用药建议、质检建议等内容。
# 病例内容：
## 诊疗所诊疗对话
  对话来自于诊疗所语音，通过asr智能识别、说话人识别，识别有一定的错误。
  {dialogue_text}
## 宠物电子病历
  来自于诊疗所医生提供的宠物基本信息、主诉、初诊、化验记过、影像结果、用药、用法用量，可能不完整，甚至为空。
  ``` python
  {{
    "name": "{name}",    #主人姓名
    "phone": "{phone}",  #主人电话
    "pet_name":"{pet_name}", #宠物姓名
    "species":"{species}", #猫/狗/其他
    "breed":"{breed}",   #​柯基/泰迪/比熊/法斗/拉布拉多/金毛 / 狸花猫/英短/美短/布偶猫​
    "weight":"{weight}",  #宠物体重，单位kg 0-100
    "deworming":{deworming},#是否驱虫 True/False
    "sterilization": {sterilization},#是否绝育 True/False
    "complaint":"{complaint}", #主诉、病史
    "first_diagnosis":"{first_diagnosis}", #鉴别诊断，根据检查已有的病历信息和对话内容，给出最可能的诊断疾病top3
    "checkup"{checkup}",    #推荐检查
    "results"{results}",    #检查结果
    "final_diagnosis":"{final_diagnosis}", #疾病诊断，根据检查结果和对话内容，给出诊断疾病
    "treatment":"{treatment}", #治疗用药及用法用量
  }}
  ``` 
现在，请根据以上对话填充电子病历，将电子病历的却是字段补全：
「诊断」：根据对话和电子病历，first_diagnosis。
"""


TREATEMENT_TEMPLATE = """
# 你是一名专业的宠物医生，擅长犬猫等小动物内外科疾病诊疗,可根据宠物医院医生要求，协助生成诊断、病例、用药建议、质检建议等内容。
# 病例内容：
## 诊疗所诊疗对话
  对话来自于诊疗所语音，通过asr智能识别、说话人识别，识别有一定的错误。
  {dialogue_text}
## 宠物电子病历
  来自于诊疗所医生提供的宠物基本信息、主诉、初诊、化验记过、影像结果、用药、用法用量，可能不完整，甚至为空。
  ``` python
  {{
    "name": "{name}",    #主人姓名
    "phone": "{phone}",  #主人电话
    "pet_name":"{pet_name}", #宠物姓名
    "species":"{species}", #猫/狗/其他
    "breed":"{breed}",   #​柯基/泰迪/比熊/法斗/拉布拉多/金毛 / 狸花猫/英短/美短/布偶猫​
    "weight":"{weight}",  #宠物体重，单位kg 0-100
    "deworming":{deworming},#是否驱虫 True/False
    "sterilization": {sterilization},#是否绝育 True/False
    "complaint":"{complaint}", #主诉、病史
    "first_diagnosis":"{first_diagnosis}", #鉴别诊断，根据检查已有的病历信息和对话内容，给出最可能的诊断疾病top3
    "checkup"{checkup}",    #推荐检查
    "results"{results}",    #检查结果
    "final_diagnosis":"{final_diagnosis}", #疾病诊断，根据检查结果和对话内容，给出诊断疾病
    "treatment":"{treatment}", #治疗用药及用法用量
  }}
  ``` 
现在，请根据以上对话填充电子病历，将电子病历的却是字段补全：
「诊断」：根据对话和电子病历，first_diagnosis。
"""



CHECK_TEMPLATE = """
# 你是一名专业的宠物医生，擅长犬猫等小动物内外科疾病诊疗,可根据宠物医院医生要求，协助生成诊断、病例、用药建议、质检建议等内容。
# 病例内容：
## 诊疗所诊疗对话
  对话来自于诊疗所语音，通过asr智能识别、说话人识别，识别有一定的错误。
  {dialogue_text}
## 宠物电子病历
  来自于诊疗所医生提供的宠物基本信息、主诉、初诊、化验记过、影像结果、用药、用法用量，可能不完整，甚至为空。
  ``` python
  {{
    "name": "{name}",    #主人姓名
    "phone": "{phone}",  #主人电话
    "pet_name":"{pet_name}", #宠物姓名
    "species":"{species}", #猫/狗/其他
    "breed":"{breed}",   #​柯基/泰迪/比熊/法斗/拉布拉多/金毛 / 狸花猫/英短/美短/布偶猫​
    "weight":"{weight}",  #宠物体重，单位kg 0-100
    "deworming":{deworming},#是否驱虫 True/False
    "sterilization": {sterilization},#是否绝育 True/False
    "complaint":"{complaint}", #主诉、病史
    "first_diagnosis":"{first_diagnosis}", #鉴别诊断，根据检查已有的病历信息和对话内容，给出最可能的诊断疾病top3
    "checkup"{checkup}",    #推荐检查
    "results"{results}",    #检查结果
    "final_diagnosis":"{final_diagnosis}", #疾病诊断，根据检查结果和对话内容，给出诊断疾病
    "treatment":"{treatment}", #治疗用药及用法用量
  }}
  ``` 
现在，请根据以上对话填充电子病历，将电子病历的却是字段补全：
「诊断」：根据对话和电子病历，first_diagnosis。
"""


TEMPLATE_MAP = {
    "📋 一键电子病历":FILL_TEMPLATE,
    "🩺️️️ 1-问诊阶段":None,
    "🔬 2-检查阶段":None,
    "📊 3-报告阶段":None,
    "💊 4-治疗阶段":None
}





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
