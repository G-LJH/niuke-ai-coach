import os
import time
from typing import Dict, Any, List
import PyPDF2

from src.logger import get_logger, log_tool_call

logger = get_logger("tools.resume")


def parse_resume_pdf(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "file_path": file_path}

    if not file_path.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported", "file_path": file_path}

    start_time = time.time()
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            raw_text = "".join(page.extract_text() or "" for page in reader.pages)

        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_call(logger, "parse_resume_pdf", duration_ms, "success")
        return {"raw_text": raw_text}

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_call(logger, "parse_resume_pdf", duration_ms, "failed", str(e))
        return {"error": str(e), "file_path": file_path}
