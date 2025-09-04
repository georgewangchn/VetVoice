# llm_client.py
import openai
import os
import json

openai.api_key = os.environ.get("OPENAI_API_KEY")

def call_llm_function_calling(prompt: str, functions: list):
    """
    使用 OpenAI GPT function calling 调用 LLM
    """
    resp = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=[{"role": "user", "content": prompt}],
        functions=functions,
        function_call="auto"
    )
    choice = resp["choices"][0]
    if choice.get("message", {}).get("function_call"):
        args_str = choice["message"]["function_call"]["arguments"]
        try:
            return json.loads(args_str)
        except:
            return {}
    return {}
