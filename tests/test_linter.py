import asyncio
import sys
from types import SimpleNamespace

import pytest

from xian_linter import (
    XIAN_VM_V1_MODE,
    LintErrorModel,
    LintResponse,
    PositionModel,
    lint_code_inline,
    lint_code_sync,
)
from xian_linter.linter import lint_code


def _valid_vm_source() -> str:
    return """
@export
def f() -> int:
    return 1
"""


def test_inline_contracting_error_is_structured():
    errors = lint_code_inline(
        """
class Bad:
    pass
"""
    )
    assert errors
    assert any(error.code == "E006" for error in errors)
    assert any(error.position is not None for error in errors)


def test_pyflakes_warning_survives_merge():
    errors = lint_code_inline(
        """
@export
def f(x: int):
    return missing_name
"""
    )
    assert any(error.code == "W001" for error in errors)


def test_pyflakes_syntax_warning_is_suppressed_by_structured_error():
    errors = lint_code_inline(
        """
def change it(test: str):
    return "TEST"
"""
    )

    assert any(error.code == "E020" for error in errors)
    assert not any(error.code == "W001" for error in errors)


def test_async_linter_suppresses_pyflakes_syntax_warning():
    errors = asyncio.run(
        lint_code(
            """
def change it(test: str):
    return "TEST"
"""
        )
    )

    assert any(error.code == "E020" for error in errors)
    assert not any(error.code == "W001" for error in errors)


def test_runtime_zk_name_is_whitelisted():
    errors = lint_code_inline(
        """
@export
def verify(vk_id: str, proof_hex: str, public_inputs: list):
    return zk.verify_groth16(vk_id, proof_hex, public_inputs)
"""
    )
    assert not any(error.code == "W001" for error in errors)


def test_log_event_indexed_name_is_whitelisted():
    errors = lint_code_inline(
        """
TransferEvent = LogEvent('Transfer', {'from': indexed(str), 'to': indexed(str), 'amount': (int, float, decimal)})
"""
    )

    assert not any(
        error.code == "W001" and "indexed" in error.message
        for error in errors
    )


def test_sync_helper_is_public_and_returns_structured_errors():
    errors = lint_code_sync(
        """
@export
def f(x: int):
    return missing_name
"""
    )
    assert errors
    assert all(isinstance(error, LintErrorModel) for error in errors)
    assert any(error.code == "W001" for error in errors)


def test_public_models_are_available_from_package_root():
    response = LintResponse(
        success=False,
        errors=[
            LintErrorModel(
                code="E999",
                message="example",
                position=PositionModel(
                    line=1,
                    col=0,
                    end_line=1,
                    end_col=7,
                ),
            )
        ],
    )

    assert response.errors[0].code == "E999"


def test_xian_vm_v1_mode_accepts_vm_lowerable_contract():
    errors = lint_code_inline(_valid_vm_source(), mode=XIAN_VM_V1_MODE)

    assert not errors


def test_xian_vm_v1_mode_reports_ir_lowering_errors():
    errors = lint_code_inline(
        """
value = 1

@export
def f() -> int:
    global value
    value = 2
    return value
""",
        mode=XIAN_VM_V1_MODE,
    )

    assert any(error.code == "XVM001" for error in errors)


def test_xian_vm_v1_mode_uses_native_validator_when_available(monkeypatch):
    calls: list[str] = []
    monkeypatch.setitem(
        sys.modules,
        "xian_vm_core",
        SimpleNamespace(
            validate_module_ir_json=lambda payload: calls.append(payload)
        ),
    )

    errors = lint_code_inline(_valid_vm_source(), mode=XIAN_VM_V1_MODE)

    assert not errors
    assert calls


def test_xian_vm_v1_mode_reports_native_validation_errors(monkeypatch):
    def fail_validation(_: str) -> None:
        raise RuntimeError("bad ir")

    monkeypatch.setitem(
        sys.modules,
        "xian_vm_core",
        SimpleNamespace(validate_module_ir_json=fail_validation),
    )

    errors = lint_code_inline(_valid_vm_source(), mode=XIAN_VM_V1_MODE)

    assert any(
        error.code == "XVM002" and "bad ir" in error.message for error in errors
    )


def test_unsupported_lint_mode_is_rejected():
    with pytest.raises(ValueError, match="Unsupported lint mode"):
        lint_code_inline(_valid_vm_source(), mode="unknown")
