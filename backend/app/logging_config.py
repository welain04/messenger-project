"""Настройка structured logging (JSON Lines в stdout для Amvera)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from .config import Settings

_LOG_RECORD_SKIP = frozenset(
    {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
        "message",
    }
)


class JsonLineFormatter(logging.Formatter):
    """Одна строка = один JSON-объект (удобно для Amvera и grep)."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if message.startswith("{") and message.endswith("}"):
            try:
                json.loads(message)
                return message
            except json.JSONDecodeError:
                pass

        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        if record.exc_info:
            payload["stack"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _LOG_RECORD_SKIP and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(settings: Settings) -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json_enabled:
        formatter: logging.Formatter = JsonLineFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
