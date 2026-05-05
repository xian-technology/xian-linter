"""Xian smart-contract linter.

This package stays thin on purpose: the authoritative contract-rule surface
comes from ``xian-contracting`` and is merged with PyFlakes warnings into a
single structured result list.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable
from functools import lru_cache
from io import StringIO

from contracting.compilation.compiler import ContractingCompiler
from contracting.compilation.linter import (
    Linter as ContractingLinter,
)
from contracting.compilation.linter import (
    LintError as ContractingLintError,
)
from contracting.compilation.vm import (
    XIAN_VM_V1_PROFILE,
    VmCompatibilityChecker,
)
from pydantic import BaseModel
from pyflakes.api import check as pyflakes_check
from pyflakes.reporter import Reporter

MAX_CODE_SIZE = 1_000_000
DEFAULT_LINT_MODE = "python"
XIAN_VM_V1_MODE = XIAN_VM_V1_PROFILE
SUPPORTED_LINT_MODES = frozenset({DEFAULT_LINT_MODE, XIAN_VM_V1_MODE})
XIAN_VM_LOWERING_ERROR_CODE = "XVM001"
XIAN_VM_NATIVE_VALIDATION_ERROR_CODE = "XVM002"

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


def normalize_lint_mode(mode: str | None = None) -> str:
    selected = mode or DEFAULT_LINT_MODE
    if selected not in SUPPORTED_LINT_MODES:
        supported = ", ".join(sorted(SUPPORTED_LINT_MODES))
        raise ValueError(
            f"Unsupported lint mode '{selected}'. Supported modes: {supported}"
        )
    return selected


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


def _parse_pyflakes(
    output: str, whitelist: frozenset[str]
) -> list[LintErrorModel]:
    errors: list[LintErrorModel] = []
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


def _run_contracting(code: str) -> list[LintErrorModel]:
    linter = ContractingLinter()
    errors = linter.check(code)
    if not errors:
        return []
    return [_contracting_to_model(error) for error in errors]


def _vm_error(code: str, message: str) -> LintErrorModel:
    return LintErrorModel(code=code, message=message)


def _run_native_vm_ir_validation(vm_ir_json: str) -> list[LintErrorModel]:
    try:
        from xian_vm_core import validate_module_ir_json
    except ModuleNotFoundError as exc:
        if exc.name == "xian_vm_core":
            return []
        return [
            _vm_error(
                XIAN_VM_NATIVE_VALIDATION_ERROR_CODE,
                f"Xian VM native validator could not be loaded: {exc}",
            )
        ]
    except ImportError as exc:
        return [
            _vm_error(
                XIAN_VM_NATIVE_VALIDATION_ERROR_CODE,
                f"Xian VM native validator could not be loaded: {exc}",
            )
        ]

    try:
        validate_module_ir_json(vm_ir_json)
    except Exception as exc:
        return [
            _vm_error(
                XIAN_VM_NATIVE_VALIDATION_ERROR_CODE,
                f"Xian VM native IR validation failed: {exc}",
            )
        ]
    return []


def _run_xian_vm_v1(code: str) -> list[LintErrorModel]:
    checker = VmCompatibilityChecker()
    report = checker.check(code, profile=XIAN_VM_V1_MODE)
    if report.errors:
        return [_contracting_to_model(error) for error in report.errors]

    compiler = ContractingCompiler(module_name="__main__")
    try:
        vm_ir_json = compiler.lower_to_ir_json(
            code,
            lint=False,
            vm_profile=XIAN_VM_V1_MODE,
        )
    except Exception as exc:
        return [
            _vm_error(
                XIAN_VM_LOWERING_ERROR_CODE,
                f"Xian VM IR lowering failed: {exc}",
            )
        ]

    return _run_native_vm_ir_validation(vm_ir_json)


def _run_contract_rules(code: str, mode: str) -> list[LintErrorModel]:
    if mode == XIAN_VM_V1_MODE:
        return _run_xian_vm_v1(code)
    return _run_contracting(code)


def _run_pyflakes(code: str, whitelist: frozenset[str]) -> list[LintErrorModel]:
    stdout = StringIO()
    stderr = StringIO()
    reporter = Reporter(stdout, stderr)
    pyflakes_check(code, "<string>", reporter)
    return _parse_pyflakes(stdout.getvalue() + stderr.getvalue(), whitelist)


def _sort_errors(errors: list[LintErrorModel]) -> list[LintErrorModel]:
    errors.sort(
        key=lambda error: (
            error.position.line if error.position else 0,
            error.position.col if error.position else 0,
        )
    )
    return errors


async def lint_code(
    code: str,
    whitelist: frozenset[str] | None = None,
    *,
    mode: str | None = DEFAULT_LINT_MODE,
) -> list[LintErrorModel]:
    whitelist = whitelist or DEFAULT_WHITELIST
    selected_mode = normalize_lint_mode(mode)
    loop = asyncio.get_running_loop()
    contract_rules_task = loop.run_in_executor(
        None,
        _run_contract_rules,
        code,
        selected_mode,
    )
    pyflakes_task = loop.run_in_executor(None, _run_pyflakes, code, whitelist)
    contract_rule_errors, pyflakes_errors = await asyncio.gather(
        contract_rules_task,
        pyflakes_task,
    )
    return _sort_errors(contract_rule_errors + pyflakes_errors)


def lint_code_sync(
    code: str,
    whitelist: frozenset[str] | None = None,
    *,
    mode: str | None = DEFAULT_LINT_MODE,
) -> list[LintErrorModel]:
    whitelist = whitelist or DEFAULT_WHITELIST
    selected_mode = normalize_lint_mode(mode)
    errors = _run_contract_rules(code, selected_mode) + _run_pyflakes(
        code,
        whitelist,
    )
    return _sort_errors(errors)


def lint_code_inline(
    code: str,
    whitelist_patterns: Iterable[str] | None = None,
    *,
    mode: str | None = DEFAULT_LINT_MODE,
) -> list[LintErrorModel]:
    whitelist = (
        frozenset(whitelist_patterns)
        if whitelist_patterns is not None
        else DEFAULT_WHITELIST
    )
    return lint_code_sync(code, whitelist, mode=mode)


@lru_cache(maxsize=100)
def get_whitelist_patterns(
    patterns_str: str | None = None,
) -> frozenset[str]:
    if not patterns_str:
        return DEFAULT_WHITELIST
    return frozenset(patterns_str.split(","))
