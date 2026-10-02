"""Application-wide logging setup and per-request correlation ids.

Every record carries the id of the HTTP request that produced it, so the lines
a single request writes across routers and services can be grepped together.
"""

import json
import logging
import logging.config
import re
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# client-supplied ids are echoed into logs and headers; only accept a safe charset
# so a caller can't forge log lines with newlines or control characters
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def resolve_request_id(incoming: str | None) -> str:
    if incoming and _REQUEST_ID_RE.match(incoming):
        return incoming
    return uuid.uuid4().hex


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for log collectors (CloudWatch, Loki, ...)."""

    # attributes every LogRecord has; anything else came in through `extra=`
    _RESERVED = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id"}

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    formatter = (
        {"()": JsonFormatter}
        if json_format
        else {
            "format": "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    )
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": RequestIdFilter}},
            "formatters": {"default": formatter},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                }
            },
            "root": {"level": level.upper(), "handlers": ["console"]},
            "loggers": {
                # route uvicorn through our handler; its access log is replaced
                # by the request middleware, which also knows the request id
                "uvicorn": {"handlers": [], "propagate": True},
                "uvicorn.error": {"handlers": [], "propagate": True},
                "uvicorn.access": {"handlers": [], "propagate": False, "level": "WARNING"},
                # SQL echo is far too noisy for the app level; opt in explicitly
                "sqlalchemy.engine": {"level": "WARNING"},
                "apscheduler": {"level": "WARNING"},
                "httpx": {"level": "WARNING"},
            },
        }
    )
