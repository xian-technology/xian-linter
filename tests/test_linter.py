from xian_linter import lint_code_inline


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
