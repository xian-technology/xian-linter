from __future__ import annotations

import base64
import gzip

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from .linter import (
    MAX_CODE_SIZE,
    LintResponse,
    get_whitelist_patterns,
    lint_code,
)

app = FastAPI(title="Xian Contract Linter")


@app.post("/lint_base64")
async def lint_base64(request: Request) -> LintResponse:
    """Lint base64-encoded Python contract code."""
    raw_data = await request.body()

    if not raw_data:
        raise HTTPException(status_code=400, detail="Empty request body")
    if len(raw_data) > MAX_CODE_SIZE:
        raise HTTPException(status_code=400, detail="Code size too large")

    whitelist = get_whitelist_patterns(
        request.query_params.get("whitelist_patterns")
    )

    try:
        b64_text = raw_data.decode("utf-8", errors="replace")
        code = base64.b64decode(b64_text).decode("utf-8", errors="replace")
        if not code.strip():
            raise HTTPException(status_code=400, detail="Empty code")
        errors = await lint_code(code, whitelist)
        return LintResponse(success=len(errors) == 0, errors=errors)
    except HTTPException:
        raise
    except Exception as e:
        from .linter import LintErrorModel
        return LintResponse(
            success=False,
            errors=[LintErrorModel(code="E000", message=f"Processing error: {e}")],
        )


@app.post("/lint_gzip")
async def lint_gzip(request: Request) -> LintResponse:
    """Lint gzip-compressed Python contract code."""
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
    except Exception as e:
        from .linter import LintErrorModel
        return LintResponse(
            success=False,
            errors=[LintErrorModel(code="E000", message=f"Processing error: {e}")],
        )


@app.post("/lint")
async def lint_raw(request: Request) -> LintResponse:
    """Lint raw Python contract code (plain text body)."""
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
    except Exception as e:
        from .linter import LintErrorModel
        return LintResponse(
            success=False,
            errors=[LintErrorModel(code="E000", message=f"Processing error: {e}")],
        )


def run_server() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
