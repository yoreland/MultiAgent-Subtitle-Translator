import requests
import json
from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

class LLMClient:
    def __init__(self):
        self.base_url = LLM_BASE_URL.rstrip('/')
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
    
    def translate(self, text: str, target_lang: str, context: str = "") -> str:
        prompt = f"""Translate the following subtitle text to {target_lang}.
Keep the translation natural and appropriate for subtitles.

Text to translate: {text}

Translation:"""
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000  # 降低输出token限制
                },
                timeout=90  # 降低超时时间
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                return content
            else:
                error_msg = f"API Error {response.status_code}: {response.text[:200]}"
                print(f"LLM API错误: {error_msg}")  # 添加错误日志
                return error_msg
                
        except requests.exceptions.Timeout:
            return "Translation timeout - please try again"
        except Exception as e:
            return f"Translation error: {str(e)}"
    
    def analyze_terminology(self, text: str) -> list:
        return []  # Simplified for now
