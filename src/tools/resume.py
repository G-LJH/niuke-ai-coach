import os
from typing import Dict, Any, List
import PyPDF2

from src.logger import get_logger, log_tool_call

logger = get_logger("tools.resume")


def parse_resume_pdf(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "file_path": file_path}

    if not file_path.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported", "file_path": file_path}

    start_time = 0
    try:
        import time
        start_time = time.time()

        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            raw_text = ""
            for page in reader.pages:
                raw_text += page.extract_text() or ""

        result = {
            "raw_text": raw_text,
        }

        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_call(logger, "parse_resume_pdf", duration_ms, "success")
        return result

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0
        log_tool_call(logger, "parse_resume_pdf", duration_ms, "failed", str(e))
        return {"error": str(e), "file_path": file_path}


def _extract_name(text: str) -> str:
    lines = text.strip().split("\n")
    if lines:
        return lines[0].strip()
    return ""


def _extract_phone(text: str) -> str:
    import re
    match = re.search(r"1[3-9]\d{9}", text)
    return match.group() if match else ""


def _extract_email(text: str) -> str:
    import re
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group() if match else ""


def _extract_education(text: str) -> List[Dict[str, str]]:
    return []


def _extract_skills(text: str) -> List[str]:
    return []


def _extract_projects(text: str) -> List[Dict[str, str]]:
    return []


def _extract_work_experience(text: str) -> List[Dict[str, str]]:
    return []
