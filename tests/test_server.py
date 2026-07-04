import asyncio
import gzip

import pytest

from xian_linter import server
from xian_linter.linter import MAX_CODE_SIZE

fastapi = pytest.importorskip("fastapi")
starlette_requests = pytest.importorskip("starlette.requests")
Request = starlette_requests.Request


async def _call_lint_gzip(body: bytes):
    app = server.create_app()
    endpoint = next(
        route.endpoint for route in app.routes if getattr(route, "path", None) == "/lint_gzip"
    )
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/lint_gzip",
            "query_string": b"",
            "headers": [],
        },
        receive,
    )
    return await endpoint(request)


def test_lint_gzip_rejects_oversized_decompressed_payload(monkeypatch):
    seen_lengths: list[int] = []

    async def fake_lint_code(code, whitelist, *, mode=None):
        seen_lengths.append(len(code.encode("utf-8")))
        return []

    monkeypatch.setattr(server, "lint_code", fake_lint_code)
    payload = gzip.compress(b"a" * (MAX_CODE_SIZE + 40))

    assert len(payload) < MAX_CODE_SIZE
    with pytest.raises(fastapi.HTTPException) as exc_info:
        asyncio.run(_call_lint_gzip(payload))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Code size too large"
    assert seen_lengths == []


def test_lint_gzip_rejects_extreme_compression_ratio(monkeypatch):
    seen_lengths: list[int] = []

    async def fake_lint_code(code, whitelist, *, mode=None):
        seen_lengths.append(len(code.encode("utf-8")))
        return []

    monkeypatch.setattr(server, "lint_code", fake_lint_code)
    payload = gzip.compress(b"a" * 200_000)

    assert len(payload) * server.MAX_GZIP_COMPRESSION_RATIO < 200_000
    with pytest.raises(fastapi.HTTPException) as exc_info:
        asyncio.run(_call_lint_gzip(payload))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Gzip compression ratio too high"
    assert seen_lengths == []


def test_lint_gzip_accepts_valid_bounded_payload(monkeypatch):
    seen_code: list[str] = []

    async def fake_lint_code(code, whitelist, *, mode=None):
        seen_code.append(code)
        return []

    monkeypatch.setattr(server, "lint_code", fake_lint_code)
    source = "@export\ndef f():\n    return 1\n"

    response = asyncio.run(_call_lint_gzip(gzip.compress(source.encode("utf-8"))))

    assert response.success is True
    assert response.errors == []
    assert seen_code == [source]


def test_lint_gzip_rejects_invalid_gzip():
    with pytest.raises(fastapi.HTTPException) as exc_info:
        asyncio.run(_call_lint_gzip(b"not gzip"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid gzip data"


def test_cors_defaults_to_local_browser_origins(monkeypatch):
    monkeypatch.delenv(server.CORS_ORIGINS_ENV, raising=False)

    config = server._cors_middleware_config()

    assert config["allow_origins"] == []
    assert config["allow_origin_regex"] == server.LOCAL_CORS_ORIGIN_REGEX


def test_cors_can_be_explicitly_configured(monkeypatch):
    monkeypatch.setenv(
        server.CORS_ORIGINS_ENV,
        "https://ide.example, http://localhost:5173",
    )

    config = server._cors_middleware_config()

    assert config["allow_origins"] == ["https://ide.example", "http://localhost:5173"]
    assert config["allow_origin_regex"] is None


def test_run_server_defaults_to_loopback(monkeypatch):
    calls = []

    class FakeUvicorn:
        @staticmethod
        def run(app, *, host, port):
            calls.append({"app": app, "host": host, "port": port})

    monkeypatch.delenv(server.SERVER_HOST_ENV, raising=False)
    monkeypatch.delenv(server.SERVER_PORT_ENV, raising=False)
    monkeypatch.setattr(
        server, "_load_server_dependencies", lambda: (None, None, None, FakeUvicorn)
    )
    monkeypatch.setattr(server, "create_app", lambda: "app")

    server.run_server()

    assert calls == [{"app": "app", "host": "127.0.0.1", "port": 8000}]


def test_run_server_allows_explicit_host_and_port(monkeypatch):
    calls = []

    class FakeUvicorn:
        @staticmethod
        def run(app, *, host, port):
            calls.append({"app": app, "host": host, "port": port})

    monkeypatch.setenv(server.SERVER_HOST_ENV, "0.0.0.0")
    monkeypatch.setenv(server.SERVER_PORT_ENV, "9000")
    monkeypatch.setattr(
        server, "_load_server_dependencies", lambda: (None, None, None, FakeUvicorn)
    )
    monkeypatch.setattr(server, "create_app", lambda: "app")

    server.run_server()

    assert calls == [{"app": "app", "host": "0.0.0.0", "port": 9000}]
