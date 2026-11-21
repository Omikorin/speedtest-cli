"""
Guards the split between the program and library.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest
import speedtest.api

API_DIR = Path(speedtest.api.__file__).parent
PROGRAM_PACKAGES = {"cli", "utils", "exceptions", "__main__"}


def _imported_modules(path: Path) -> set[str]:
    """Absolute module names imported by a file; relative imports resolve inside the package."""

    imported: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module)
    return imported


API_FILES = sorted(API_DIR.rglob("*.py"))


def test_api_package_is_found() -> None:
    assert len(API_FILES) > 10


@pytest.mark.parametrize("path", API_FILES, ids=lambda p: str(p.relative_to(API_DIR)))
def test_api_module_does_not_import_the_program(path: Path) -> None:
    program = {f"speedtest.{name}" for name in PROGRAM_PACKAGES}
    offending = {m for m in _imported_modules(path) if any(m == p or m.startswith(f"{p}.") for p in program)}

    assert not offending, f"{path.name} imports program code: {sorted(offending)}"


@pytest.mark.parametrize("path", API_FILES, ids=lambda p: str(p.relative_to(API_DIR)))
def test_api_module_does_not_import_rich(path: Path) -> None:
    assert not {m for m in _imported_modules(path) if m == "rich" or m.startswith("rich.")}


def test_api_module_does_not_reach_back_into_the_parent_package() -> None:
    """`from speedtest import x` would tie the library to the program's package."""

    offending = {path.name for path in API_FILES if "speedtest" in _imported_modules(path)}

    assert not offending


def test_importing_the_api_loads_neither_rich_nor_the_program() -> None:
    """Checked in a fresh interpreter, because this process has already imported everything."""

    code = (
        "import sys, speedtest.api\n"
        "loaded = sorted(m for m in sys.modules if m == 'rich' or m.startswith(('rich.', 'speedtest.cli', "
        "'speedtest.utils', 'speedtest.exceptions')))\n"
        "print(','.join(loaded))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == ""
