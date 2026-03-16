"""Xian smart-contract linter.

Combines the contracting linter (security / contract rules) with
PyFlakes (undefined names, unused imports) into a single result set.

The contracting linter is the authoritative source — its errors are
structured ``LintError`` objects with exact positions and error codes.
PyFlakes errors are parsed from its text output and merged in.
"""

from __future__ import annotations

import asyncio
import re
from functools import lru_cache
from io import StringIO
from typing import Iterable

from pydantic import BaseModel
from pyflakes.api import check as pyflakes_check
from pyflakes.reporter import Reporter

from contracting.compilation.linter import (
    ErrorCode,
    LintError as ContractingLintError,
    Linter as ContractingLinter,
)


# ── Settings ──────────────────────────────────────────────────────

MAX_CODE_SIZE: int = 1_000_000  # 1 MB

# PyFlakes reports about names that are injected by the contracting
# runtime.  Suppress any diagnostic whose message contains one of
# these substrings.
DEFAULT_WHITELIST: frozenset[str] = frozenset({
    "export", "construct",
    "Hash", "Variable", "ForeignHash", "ForeignVariable",
    "ctx", "now", "block_num", "block_hash", "chain_id",
    "random", "importlib", "hashlib", "datetime", "crypto",
    "decimal", "Any", "LogEvent",
})


# ── Response models ───────────────────────────────────────────────

class PositionModel(BaseModel):
    line: int       # 1-based
    col: int        # 0-based
    end_line: int   # 1-based
    end_col: int    # 0-based


class LintErrorModel(BaseModel):
    code: str
    message: str
    severity: str = "error"
    position: PositionModel | None = None


class LintResponse(BaseModel):
    success: bool
    errors: list[LintErrorModel]


# ── Conversion helpers ────────────────────────────────────────────

def _contracting_to_model(err: ContractingLintError) -> LintErrorModel:
    return LintErrorModel(
        code=err.code.value,
        message=err.message,
        position=PositionModel(
            line=err.line,
            col=err.col,
            end_line=err.end_line,
            end_col=err.end_col,
        ),
    )


_PYFLAKES_RE = re.compile(r"<string>:(\d+):(\d+):\s*(.+)")


def _parse_pyflakes(
    output: str, whitelist: frozenset[str]
) -> list[LintErrorModel]:
    errors = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _PYFLAKES_RE.match(line)
        if not m:
            continue
        lineno, col, message = int(m.group(1)), int(m.group(2)), m.group(3)
        if any(pat in message for pat in whitelist):
            continue
        errors.append(LintErrorModel(
            code="W001",
            message=message,
            severity="warning",
            position=PositionModel(
                line=lineno,
                col=col - 1,
                end_line=lineno,
                end_col=col - 1,
            ),
        ))
    return errors


# ── Core lint functions ───────────────────────────────────────────

def _run_contracting(code: str) -> list[LintErrorModel]:
    linter = ContractingLinter()
    errors = linter.check(code)
    if not errors:
        return []
    return [_contracting_to_model(e) for e in errors]


def _run_pyflakes(code: str, whitelist: frozenset[str]) -> list[LintErrorModel]:
    stdout = StringIO()
    stderr = StringIO()
    reporter = Reporter(stdout, stderr)
    pyflakes_check(code, "<string>", reporter)
    combined = stdout.getvalue() + stderr.getvalue()
    return _parse_pyflakes(combined, whitelist)


async def lint_code(
    code: str,
    whitelist: frozenset[str] | None = None,
) -> list[LintErrorModel]:
    """Run contracting + PyFlakes linters and return merged results."""
    wl = whitelist or DEFAULT_WHITELIST
    loop = asyncio.get_event_loop()

    contracting_task = loop.run_in_executor(None, _run_contracting, code)
    pyflakes_task = loop.run_in_executor(None, _run_pyflakes, code, wl)

    contracting_errors, pyflakes_errors = await asyncio.gather(
        contracting_task, pyflakes_task
    )

    all_errors = contracting_errors + pyflakes_errors
    all_errors.sort(key=lambda e: (
        e.position.line if e.position else 0,
        e.position.col if e.position else 0,
    ))
    return all_errors


def lint_code_sync(
    code: str,
    whitelist: frozenset[str] | None = None,
) -> list[LintErrorModel]:
    """Synchronous version of ``lint_code``."""
    wl = whitelist or DEFAULT_WHITELIST
    contracting_errors = _run_contracting(code)
    pyflakes_errors = _run_pyflakes(code, wl)
    all_errors = contracting_errors + pyflakes_errors
    all_errors.sort(key=lambda e: (
        e.position.line if e.position else 0,
        e.position.col if e.position else 0,
    ))
    return all_errors


# ── Backward-compatible inline API ────────────────────────────────

def lint_code_inline(
    code: str,
    whitelist_patterns: Iterable[str] | None = None,
) -> list[LintErrorModel]:
    """Lint a contract and return errors.  Synchronous, no event loop needed."""
    wl = (
        frozenset(whitelist_patterns)
        if whitelist_patterns is not None
        else DEFAULT_WHITELIST
    )
    return lint_code_sync(code, wl)


@lru_cache(maxsize=100)
def get_whitelist_patterns(patterns_str: str | None = None) -> frozenset[str]:
    if not patterns_str:
        return DEFAULT_WHITELIST
    return frozenset(patterns_str.split(","))
