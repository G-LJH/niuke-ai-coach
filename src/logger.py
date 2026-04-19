import json
import os
import logging
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "module": getattr(record, "module_name", record.module),
            "message": record.getMessage(),
        }

        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def get_logger(module_name: str) -> logging.Logger:
    logger = logging.getLogger(f"niuke_ai_coach.{module_name}")

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        log_file = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y-%m-%d')}.log")

        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(module)s: %(message)s")
        )
        logger.addHandler(console_handler)

    return logger


def _log_record(logger: logging.Logger, module_name: str, message: str, extra_data: dict):
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "",
        0,
        message,
        (),
        None,
    )
    record.module_name = module_name
    record.extra_data = extra_data
    logger.handle(record)


def log_tool_call(
    logger: logging.Logger,
    tool_name: str,
    duration_ms: int,
    status: str,
    error: str = None,
):
    extra_data = {
        "tool": tool_name,
        "duration_ms": duration_ms,
        "status": status,
    }
    if error:
        extra_data["error"] = error
    _log_record(logger, "tool", f"Tool call: {tool_name}", extra_data)


def log_workflow_step(
    logger: logging.Logger,
    workflow_id: str,
    step: int,
    step_name: str,
    status: str,
):
    _log_record(logger, "workflow", f"Workflow step: {step_name}", {
        "workflow_id": workflow_id,
        "step": step,
        "step_name": step_name,
        "status": status,
    })


def log_api_call(
    logger: logging.Logger,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
    status: str = "success",
):
    _log_record(logger, "api", f"API call: {model_name}", {
        "model": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "status": status,
    })
