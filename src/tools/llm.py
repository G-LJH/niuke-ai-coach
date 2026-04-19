import os
import time
import json
import re
from typing import Dict, Any
import dashscope
from dashscope import Generation
from dotenv import load_dotenv

from src.logger import get_logger, log_api_call

load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

logger = get_logger("tools.llm")

MAX_RETRIES = 3
RETRY_DELAY = 5
REQUEST_TIMEOUT = 60


def _extract_json(text: str) -> Dict[str, Any]:
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json.loads(json_match.group(0))
    return json.loads(text)


def call_llm(
    prompt: str,
    system_prompt: str = None,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> Dict[str, Any]:
    start_time = time.time()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(MAX_RETRIES):
        try:
            response = Generation.call(
                model="qwen-max",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if response.status_code == 200:
                if not response.output:
                    return {"error": f"API返回空响应, code={response.code}, message={response.message}"}

                output = response.output
                content = None

                if hasattr(output, 'text') and output.text:
                    content = output.text
                elif hasattr(output, 'choices') and output.choices:
                    message = output.choices[0].message
                    if message and hasattr(message, 'content') and message.content:
                        content = message.content
                        if isinstance(content, list):
                            content = content[0].get("text", "") if content else ""

                if not content:
                    return {"error": f"API返回空消息, output={output}"}

                usage = response.usage

                duration_ms = int((time.time() - start_time) * 1000)
                log_api_call(
                    logger,
                    "qwen-max",
                    usage.input_tokens,
                    usage.output_tokens,
                    duration_ms,
                )

                try:
                    parsed = _extract_json(content)
                    return {
                        "content": json.dumps(parsed, ensure_ascii=False),
                        "usage": {
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                        },
                    }
                except (json.JSONDecodeError, AttributeError) as e:
                    return {
                        "error": f"JSON解析失败: {str(e)}, 原始内容: {content[:200]}"
                    }

            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", RETRY_DELAY))
                time.sleep(retry_after)
                continue
            else:
                return {
                    "error": f"API error: {response.message}",
                    "retry_after": RETRY_DELAY,
                }

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return {"error": str(e), "retry_after": RETRY_DELAY}

    return {"error": "Max retries exceeded", "retry_after": RETRY_DELAY}
