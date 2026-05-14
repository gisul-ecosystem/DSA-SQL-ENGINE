import json
import logging
import os
import sys
import time
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "service": os.getenv("SERVICE_NAME", "execution-engine"),
            "message": record.getMessage(),
            "pid": record.process,
        }

        for key in (
            "job_id",
            "language",
            "mode",
            "verdict",
            "route",
            "status_code",
            "duration_seconds",
            "queue_wait_seconds",
            "error_type",
            "image",
            "operation",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(default_level: str = "INFO") -> None:
    level = os.getenv("LOG_LEVEL", default_level).upper()
    use_json = os.getenv("LOG_FORMAT", "json").lower() == "json"

    handler = logging.StreamHandler(sys.stdout)
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [pid=%(process)d] %(message)s")
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
