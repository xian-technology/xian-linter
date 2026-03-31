from xian_linter import (
    LintErrorModel,
    LintResponse,
    PositionModel,
    lint_code_inline,
    lint_code_sync,
)


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


def test_runtime_zk_name_is_whitelisted():
    errors = lint_code_inline(
        """
@export
def verify(vk_id: str, proof_hex: str, public_inputs: list):
    return zk.verify_groth16(vk_id, proof_hex, public_inputs)
"""
    )
    assert not any(error.code == "W001" for error in errors)


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
