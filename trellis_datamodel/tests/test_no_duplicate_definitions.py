"""Guard against duplicate function/class definitions in application source.

A second ``def`` or ``class`` with the same name in the same scope silently
replaces the first one.
"""

import ast
from collections import defaultdict
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent.parent
EXCLUDED_DIRS = {"tests", "static"}


def _decorator_name(dec: ast.expr) -> str:
    """Return the trailing attribute/name of a decorator, e.g. 'setter'."""
    if isinstance(dec, ast.Call):
        dec = dec.func
    if isinstance(dec, ast.Attribute):
        return dec.attr
    if isinstance(dec, ast.Name):
        return dec.id
    return ""


def _is_intentional_redefinition(node: ast.AST) -> bool:
    """@overload stubs and @x.setter/@x.getter/@x.deleter reuse the name by design."""
    decorators = getattr(node, "decorator_list", [])
    return any(
        _decorator_name(d) in {"overload", "setter", "getter", "deleter"}
        for d in decorators
    )


def _duplicates(source: str, label: str) -> list[str]:
    """Return 'file: name defined at lines ...' entries for same-scope duplicates."""
    tree = ast.parse(source)
    found: list[str] = []

    def check(body: list[ast.stmt], scope: str) -> None:
        lines: dict[str, list[int]] = defaultdict(list)
        for n in body:
            if isinstance(
                n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ) and not _is_intentional_redefinition(n):
                lines[n.name].append(n.lineno)
        for name, linenos in lines.items():
            if len(linenos) > 1:
                where = ", ".join(str(i) for i in linenos)
                found.append(f"{label}: {scope}{name} defined at lines {where}")

    check(tree.body, "")
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            check(node.body, f"{node.name}.")
    return found


def _source_files() -> list[Path]:
    return sorted(
        p
        for p in PACKAGE_DIR.rglob("*.py")
        if not EXCLUDED_DIRS & set(p.relative_to(PACKAGE_DIR).parts)
    )


def test_no_duplicate_definitions_in_source():
    offenders: list[str] = []
    for path in _source_files():
        rel = path.relative_to(PACKAGE_DIR).as_posix()
        offenders += _duplicates(path.read_text(encoding="utf-8"), rel)
    assert not offenders, "Duplicate definitions shadow earlier ones:\n" + "\n".join(
        offenders
    )


def test_detector_flags_duplicates(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "class A:\n    def x(self): ...\n    def x(self): ...\n"
        "def f(): ...\n\n\nasync def f(): ...\n"
    )
    found = _duplicates(sample.read_text(), "sample.py")
    assert len(found) == 2
    assert any("A.x defined at lines 2, 3" in f for f in found)
    assert any("f defined at lines 4, 7" in f for f in found)


def test_detector_ignores_intentional_redefinitions():
    source = (
        "from typing import overload\n"
        "@overload\ndef g(a: int) -> int: ...\n"
        "@overload\ndef g(a: str) -> str: ...\n"
        "def g(a): return a\n"
        "class P:\n"
        "    @property\n    def v(self): ...\n"
        "    @v.setter\n    def v(self, value): ...\n"
        "try:\n    def h(): ...\nexcept ImportError:\n    def h(): ...\n"
        "if True:\n    def k(): ...\nelse:\n    def k(): ...\n"
    )
    assert _duplicates(source, "x.py") == []
