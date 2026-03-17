from __future__ import annotations

import base64
import gzip

from .linter import (
    MAX_CODE_SIZE,
    LintErrorModel,
    LintResponse,
    get_whitelist_patterns,
    lint_code,
)


def _load_server_dependencies():
    try:
        import uvicorn
        from fastapi import FastAPI, HTTPException, Request
    except ImportError as exc:
        raise RuntimeError(
            "Install xian-linter with the 'server' extra to run the HTTP service."
        ) from exc

    return FastAPI, HTTPException, Request, uvicorn


def create_app():
    FastAPI, HTTPException, Request, _ = _load_server_dependencies()
    app = FastAPI(title="Xian Contract Linter")

    @app.post("/lint_base64")
    async def lint_base64(request: Request) -> LintResponse:
        raw_data = await request.body()

        if not raw_data:
            raise HTTPException(status_code=400, detail="Empty request body")
        if len(raw_data) > MAX_CODE_SIZE:
            raise HTTPException(status_code=400, detail="Code size too large")

        whitelist = get_whitelist_patterns(
            request.query_params.get("whitelist_patterns")
        )

        try:
            code = base64.b64decode(
                raw_data.decode("utf-8", errors="replace")
            ).decode("utf-8", errors="replace")
            if not code.strip():
                raise HTTPException(status_code=400, detail="Empty code")
            errors = await lint_code(code, whitelist)
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
        raw_data = await request.body()

        if not raw_data:
            raise HTTPException(status_code=400, detail="Empty request body")
        if len(raw_data) > MAX_CODE_SIZE:
            raise HTTPException(status_code=400, detail="Code size too large")

        whitelist = get_whitelist_patterns(
            request.query_params.get("whitelist_patterns")
        )

        try:
            code = gzip.decompress(raw_data).decode("utf-8", errors="replace")
            if not code.strip():
                raise HTTPException(status_code=400, detail="Empty code")
            errors = await lint_code(code, whitelist)
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

        whitelist = get_whitelist_patterns(
            request.query_params.get("whitelist_patterns")
        )

        try:
            code = raw_data.decode("utf-8", errors="replace")
            if not code.strip():
                raise HTTPException(status_code=400, detail="Empty code")
            errors = await lint_code(code, whitelist)
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
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
