# Xian Contract Linter

[![PyPI version](https://badge.fury.io/py/xian-linter.svg)](https://badge.fury.io/py/xian-linter)
[![Python versions](https://img.shields.io/pypi/pyversions/xian-linter.svg)](https://pypi.org/project/xian-linter/)

A Python code linter specifically designed for Xian smart contracts. It combines
PyFlakes with the structured linter exposed by `xian-contracting`, so contract
rule violations include stable error codes and exact source positions.

The linter can be used in two ways:
- **Inline/Programmatic**: Import and use directly in your Python code without any server dependencies
- **Standalone Server**: Run as a FastAPI service with HTTP endpoints for remote linting

## Features

- Parallel execution of linters (PyFlakes + Xian Contracting)
- Configurable whitelist patterns for ignored errors
- Structured error reporting with codes and exact spans
- Base64 and Gzip encoded code input support (server mode)
- Input validation and size limits (server mode)

## Installation

### For Inline/Programmatic Usage

Install the base package without server dependencies:

```bash
pip install xian-linter
```

### For Standalone Server Mode

Install with the server extras to include FastAPI and uvicorn:

```bash
pip install xian-linter[server]
```

### From Source

```bash
# Clone the repository
git clone https://github.com/xian-network/xian-linter.git
cd xian-linter

# Install base dependencies with uv
uv sync

# Or install with server extras
uv sync --extra server
```

## Usage

### Inline/Programmatic Usage

Use the linter directly in your Python code without running a server:

```python
from xian_linter import lint_code_inline

# Your contract code as a string
contract_code = """
def transfer():
    sender_balance = balances[ctx.caller]
    balances[ctx.caller] -= amount
"""

# Lint the code
errors = lint_code_inline(contract_code)

# Check results
if errors:
    for error in errors:
        print(f"Line {error.position.line}: {error.message}")
else:
    print("No errors found!")
```

You can also provide custom whitelist patterns:

```python
errors = lint_code_inline(
    contract_code,
    whitelist_patterns=['custom_pattern', 'another_pattern']
)
```

### Standalone Server Mode

Run the linter as a FastAPI service (requires `[server]` extras):

#### Using the command-line script:
```bash
xian-linter
```

#### Using Python's module syntax:
```bash
python -m xian_linter
```

#### Using uvicorn directly:
```bash
uvicorn xian_linter.server:create_app --factory --host 0.0.0.0 --port 8000
```

#### From source:
```bash
uv run xian-linter
```

The server will start on `http://localhost:8000` by default.

### API Endpoints

#### POST /lint_base64
Expects base64-encoded Python code in the request body.

```bash
# Example using curl
base64 < contract.py > contract.py.b64
curl -X POST "http://localhost:8000/lint_base64" --data-binary "@contract.py.b64"
```

#### POST /lint_gzip
Expects gzipped Python code in the request body.

```bash
# Example using curl
gzip -c contract.py > contract.py.gz
curl -X POST "http://localhost:8000/lint_gzip" -H "Content-Type: application/gzip" --data-binary "@contract.py.gz"
```

### Query Parameters

- `whitelist_patterns`: Comma-separated list of patterns to ignore in lint errors. Default patterns are provided for common Contracting keywords.

### Response Format

```json
{
    "success": false,
    "errors": [
        {
            "code": "E006",
            "message": "Class definitions are not allowed",
            "severity": "error",
            "position": {
                "line": 3,
                "col": 0,
                "end_line": 4,
                "end_col": 4
            }
        }
    ]
}
```

The `position` field is optional and may not be present for global errors.

## Default Whitelist Patterns

The following patterns are ignored by default in Pyflakes checks:
- `export`, `construct`
- `Hash`, `Variable`, `ForeignHash`, `ForeignVariable`
- `ctx`, `now`, `block_num`, `block_hash`, `chain_id`
- `random`, `importlib`, `hashlib`, `datetime`, `crypto`, `decimal`
- `Any`, `LogEvent`
