"""Настройка structured logging (JSON в stdout для Amvera)."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from pythonjsonlogger import jsonlogger

from .config import Settings


class _MessengerJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(
        self,
        log_record: dict[str, object],
        record: logging.LogRecord,
        message_dict: dict[str, object],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        if record.exc_info and "stack" not in log_record:
            log_record["stack"] = self.formatException(record.exc_info)


def setup_logging(settings: Settings) -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json_enabled:
        formatter: logging.Formatter = _MessengerJsonFormatter(
            fmt="%(timestamp)s %(level)s %(logger)s %(message)s",
            rename_fields={"levelname": "level", "name": "logger"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
