import json
import logging

from app.core.logging import JsonFormatter, RequestIdFilter, request_id_var, resolve_request_id


async def test_response_carries_generated_request_id(client):
    res = await client.get("/api/v1/stores/999999")
    request_id = res.headers["X-Request-ID"]
    assert len(request_id) == 32


async def test_valid_incoming_request_id_is_echoed(client):
    res = await client.get("/health", headers={"X-Request-ID": "trace-abc.123"})
    assert res.headers["X-Request-ID"] == "trace-abc.123"


async def test_unsafe_incoming_request_id_is_replaced(client):
    res = await client.get("/health", headers={"X-Request-ID": "x" * 65})
    assert res.headers["X-Request-ID"] != "x" * 65
    assert resolve_request_id("bad id\nINFO forged") != "bad id\nINFO forged"


async def test_request_is_logged_with_status_and_request_id(client, caplog):
    caplog.set_level(logging.INFO, logger="app.request")
    caplog.handler.addFilter(RequestIdFilter())
    res = await client.get("/api/v1/stores/999999", headers={"X-Request-ID": "req-1"})

    records = [r for r in caplog.records if r.name == "app.request"]
    assert len(records) == 1
    record = records[0]
    assert record.status == res.status_code
    assert record.path == "/api/v1/stores/999999"
    assert record.levelno == logging.WARNING  # 4xx
    assert record.duration_ms >= 0
    assert record.request_id == "req-1"


async def test_health_check_is_not_logged(client, caplog):
    caplog.set_level(logging.INFO, logger="app.request")
    await client.get("/health")
    assert not [r for r in caplog.records if r.name == "app.request"]


def test_json_formatter_includes_request_id_and_extras():
    token = request_id_var.set("req-42")
    try:
        record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "hello %s", ("빵",), None)
        record.status = 200
        RequestIdFilter().filter(record)
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)

    assert payload["request_id"] == "req-42"
    assert payload["message"] == "hello 빵"
    assert payload["status"] == 200
    assert payload["level"] == "INFO"
