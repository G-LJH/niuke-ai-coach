import os
import base64
from typing import Dict, Any, List
import dashscope
from dashscope import MultiModalConversation
from dotenv import load_dotenv

from src.logger import get_logger, log_tool_call

load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

logger = get_logger("tools.jd")

SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}


def _image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_mime_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "image/jpeg")


def analyze_jd_screenshot(image_path: str) -> Dict[str, Any]:
    if not os.path.exists(image_path):
        return {"error": f"Image not found: {image_path}", "image_path": image_path}

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        return {"error": f"Unsupported format: {ext}", "image_path": image_path}

    start_time = 0
    try:
        import time
        start_time = time.time()

        base64_image = _image_to_base64(image_path)
        mime_type = _get_mime_type(image_path)
        image_data_uri = f"data:{mime_type};base64,{base64_image}"

        messages = [
            {
                "role": "system",
                "content": [{"text": "你是一个专业的JD分析助手，请从图片中提取职位信息。"}],
            },
            {
                "role": "user",
                "content": [
                    {"image": image_data_uri},
                    {"text": "请提取以下信息：公司名称、职位名称、任职要求、优先技能。以JSON格式返回：{\"company\": \"公司名\", \"position\": \"职位\", \"requirements\": [\"要求1\"], \"preferred_skills\": [\"技能1\"], \"raw_text\": \"完整文本\"}"},
                ],
            },
        ]

        response = MultiModalConversation.call(
            model="qwen-vl-max",
            messages=messages,
        )

        if response.status_code == 200:
            content = response.output.choices[0].message.content[0]["text"]
            import json
            import re
            
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
            else:
                return {"error": f"无法从响应中提取JSON: {content[:200]}"}
            
            result["raw_text"] = result.get("raw_text", content)
        else:
            return {"error": f"API error: {response.message}", "image_path": image_path}

        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_call(logger, "analyze_jd_screenshot", duration_ms, "success")
        return result

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0
        log_tool_call(logger, "analyze_jd_screenshot", duration_ms, "failed", str(e))
        return {"error": str(e), "image_path": image_path}
