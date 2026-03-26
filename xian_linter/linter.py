"""Xian smart-contract linter."""

from __future__ import annotations

import asyncio
import re
from functools import lru_cache
from io import StringIO
from typing import Iterable

from contracting.compilation.linter import (
    Linter as ContractingLinter,
)
from contracting.compilation.linter import (
    LintError as ContractingLintError,
)
from pydantic import BaseModel
from pyflakes.api import check as pyflakes_check
from pyflakes.reporter import Reporter

MAX_CODE_SIZE = 1_000_000

DEFAULT_WHITELIST = frozenset(
    {
        "Any",
        "ForeignHash",
        "ForeignVariable",
        "Hash",
        "LogEvent",
        "Variable",
        "block_hash",
        "block_num",
        "chain_id",
        "construct",
        "crypto",
        "ctx",
        "datetime",
        "decimal",
        "export",
        "hashlib",
        "importlib",
        "now",
        "random",
        "zk",
    }
)


class PositionModel(BaseModel):
    line: int
    col: int
    end_line: int
    end_col: int


class LintErrorModel(BaseModel):
    code: str
    message: str
    severity: str = "error"
    position: PositionModel | None = None


class LintResponse(BaseModel):
    success: bool
    errors: list[LintErrorModel]


def _contracting_to_model(error: ContractingLintError) -> LintErrorModel:
    return LintErrorModel(
        code=error.code.value,
        message=error.message,
        position=PositionModel(
            line=error.line,
            col=error.col,
            end_line=error.end_line,
            end_col=error.end_col,
        ),
    )


_PYFLAKES_PATTERN = re.compile(r"<string>:(\d+):(\d+):\s*(.+)")


def _parse_pyflakes(output: str, whitelist: frozenset[str]):
    errors = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _PYFLAKES_PATTERN.match(line)
        if not match:
            continue
        lineno, col, message = (
            int(match.group(1)),
            int(match.group(2)),
            match.group(3),
        )
        if any(pattern in message for pattern in whitelist):
            continue
        errors.append(
            LintErrorModel(
                code="W001",
                message=message,
                severity="warning",
                position=PositionModel(
                    line=lineno,
                    col=col - 1,
                    end_line=lineno,
                    end_col=col - 1,
                ),
            )
        )
    return errors


def _run_contracting(code: str):
    linter = ContractingLinter()
    errors = linter.check(code)
    if not errors:
        return []
    return [_contracting_to_model(error) for error in errors]


def _run_pyflakes(code: str, whitelist: frozenset[str]):
    stdout = StringIO()
    stderr = StringIO()
    reporter = Reporter(stdout, stderr)
    pyflakes_check(code, "<string>", reporter)
    return _parse_pyflakes(stdout.getvalue() + stderr.getvalue(), whitelist)


async def lint_code(code: str, whitelist: frozenset[str] | None = None):
    whitelist = whitelist or DEFAULT_WHITELIST
    loop = asyncio.get_running_loop()
    contracting_task = loop.run_in_executor(None, _run_contracting, code)
    pyflakes_task = loop.run_in_executor(None, _run_pyflakes, code, whitelist)
    contracting_errors, pyflakes_errors = await asyncio.gather(
        contracting_task,
        pyflakes_task,
    )
    errors = contracting_errors + pyflakes_errors
    errors.sort(
        key=lambda error: (
            error.position.line if error.position else 0,
            error.position.col if error.position else 0,
        )
    )
    return errors


def lint_code_sync(code: str, whitelist: frozenset[str] | None = None):
    whitelist = whitelist or DEFAULT_WHITELIST
    errors = _run_contracting(code) + _run_pyflakes(code, whitelist)
    errors.sort(
        key=lambda error: (
            error.position.line if error.position else 0,
            error.position.col if error.position else 0,
        )
    )
    return errors


def lint_code_inline(
    code: str,
    whitelist_patterns: Iterable[str] | None = None,
):
    whitelist = (
        frozenset(whitelist_patterns)
        if whitelist_patterns is not None
        else DEFAULT_WHITELIST
    )
    return lint_code_sync(code, whitelist)


@lru_cache(maxsize=100)
def get_whitelist_patterns(patterns_str: str | None = None):
    if not patterns_str:
        return DEFAULT_WHITELIST
    return frozenset(patterns_str.split(","))
