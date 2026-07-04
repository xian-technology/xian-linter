import base64
import os
import zlib
from collections.abc import AsyncIterator

from .linter import (
    MAX_CODE_SIZE,
    LintErrorModel,
    LintResponse,
    get_whitelist_patterns,
    lint_code,
    normalize_lint_mode,
)

MAX_GZIP_COMPRESSION_RATIO = 100
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 8000
SERVER_HOST_ENV = "XIAN_LINTER_HOST"
SERVER_PORT_ENV = "XIAN_LINTER_PORT"
CORS_ORIGINS_ENV = "XIAN_LINTER_CORS_ORIGINS"
LOCAL_CORS_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"


def _load_server_dependencies():
    try:
        import uvicorn
        from fastapi import FastAPI, HTTPException, Request
    except ImportError as exc:
        raise RuntimeError(
            "Install xian-linter with the 'server' extra to run the HTTP service."
        ) from exc

    return FastAPI, HTTPException, Request, uvicorn


def _request_lint_mode(request, HTTPException) -> str:
    mode = request.query_params.get("mode") or request.query_params.get("lint_mode")
    try:
        return normalize_lint_mode(mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _cors_middleware_config() -> dict[str, object]:
    configured_origins = os.getenv(CORS_ORIGINS_ENV)
    if configured_origins is None:
        return {
            "allow_origins": [],
            "allow_origin_regex": LOCAL_CORS_ORIGIN_REGEX,
        }

    origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    return {
        "allow_origins": origins,
        "allow_origin_regex": None,
    }


def _server_host() -> str:
    return os.getenv(SERVER_HOST_ENV, DEFAULT_SERVER_HOST).strip() or DEFAULT_SERVER_HOST


def _server_port() -> int:
    raw_port = os.getenv(SERVER_PORT_ENV)
    if raw_port is None or not raw_port.strip():
        return DEFAULT_SERVER_PORT
    return int(raw_port)


async def _read_limited_gzip_code(
    stream: AsyncIterator[bytes],
    HTTPException,
) -> str:
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    compressed_size = 0
    decompressed_size = 0
    output = bytearray()

    try:
        async for chunk in stream:
            if not chunk:
                continue

            compressed_size += len(chunk)
            if compressed_size > MAX_CODE_SIZE:
                raise HTTPException(status_code=400, detail="Code size too large")

            remaining = MAX_CODE_SIZE - decompressed_size
            data = decompressor.decompress(chunk, remaining + 1)
            decompressed_size += len(data)
            if decompressed_size > MAX_CODE_SIZE:
                raise HTTPException(status_code=400, detail="Code size too large")
            output.extend(data)

        remaining = MAX_CODE_SIZE - decompressed_size
        tail = decompressor.flush(remaining + 1)
    except zlib.error as exc:
        raise HTTPException(status_code=400, detail="Invalid gzip data") from exc

    decompressed_size += len(tail)
    if decompressed_size > MAX_CODE_SIZE:
        raise HTTPException(status_code=400, detail="Code size too large")
    output.extend(tail)

    if not decompressor.eof or decompressor.unused_data:
        raise HTTPException(status_code=400, detail="Invalid gzip data")
    if compressed_size == 0:
        raise HTTPException(status_code=400, detail="Empty request body")
    if decompressed_size > compressed_size * MAX_GZIP_COMPRESSION_RATIO:
        raise HTTPException(status_code=400, detail="Gzip compression ratio too high")

    return output.decode("utf-8", errors="replace")


def create_app():
    FastAPI, HTTPException, Request, _ = _load_server_dependencies()
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Xian Contract Linter")
    cors_config = _cors_middleware_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],
        allow_origin_regex=cors_config["allow_origin_regex"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/lint_base64")
    async def lint_base64(request: Request) -> LintResponse:
        raw_data = await request.body()

        if not raw_data:
            raise HTTPException(status_code=400, detail="Empty request body")
        if len(raw_data) > MAX_CODE_SIZE:
            raise HTTPException(status_code=400, detail="Code size too large")

        whitelist = get_whitelist_patterns(request.query_params.get("whitelist_patterns"))
        mode = _request_lint_mode(request, HTTPException)

        try:
            code = base64.b64decode(raw_data.decode("utf-8", errors="replace")).decode(
                "utf-8", errors="replace"
            )
            if not code.strip():
                raise HTTPException(status_code=400, detail="Empty code")
            errors = await lint_code(code, whitelist, mode=mode)
            return LintResponse(success=len(errors) == 0, errors=errors)
        except HTTPException:
            raise
        except Exception as exc:
            return LintResponse(
                success=False,
                errors=[
                    LintErrorModel(
                        code="E000",
                        message=f"Processing error: {exc}",
                    )
                ],
            )

    @app.post("/lint_gzip")
    async def lint_gzip(request: Request) -> LintResponse:
        whitelist = get_whitelist_patterns(request.query_params.get("whitelist_patterns"))
        mode = _request_lint_mode(request, HTTPException)

        try:
            code = await _read_limited_gzip_code(request.stream(), HTTPException)
            if not code.strip():
                raise HTTPException(status_code=400, detail="Empty code")
            errors = await lint_code(code, whitelist, mode=mode)
            return LintResponse(success=len(errors) == 0, errors=errors)
        except HTTPException:
            raise
        except Exception as exc:
            return LintResponse(
                success=False,
                errors=[
                    LintErrorModel(
                        code="E000",
                        message=f"Processing error: {exc}",
                    )
                ],
            )

    @app.post("/lint")
    async def lint_raw(request: Request) -> LintResponse:
        raw_data = await request.body()

        if not raw_data:
            raise HTTPException(status_code=400, detail="Empty request body")
        if len(raw_data) > MAX_CODE_SIZE:
            raise HTTPException(status_code=400, detail="Code size too large")

        whitelist = get_whitelist_patterns(request.query_params.get("whitelist_patterns"))
        mode = _request_lint_mode(request, HTTPException)

        try:
            code = raw_data.decode("utf-8", errors="replace")
            if not code.strip():
                raise HTTPException(status_code=400, detail="Empty code")
            errors = await lint_code(code, whitelist, mode=mode)
            return LintResponse(success=len(errors) == 0, errors=errors)
        except HTTPException:
            raise
        except Exception as exc:
            return LintResponse(
                success=False,
                errors=[
                    LintErrorModel(
                        code="E000",
                        message=f"Processing error: {exc}",
                    )
                ],
            )

    return app


def run_server() -> None:
    _, _, _, uvicorn = _load_server_dependencies()
    uvicorn.run(create_app(), host=_server_host(), port=_server_port())
