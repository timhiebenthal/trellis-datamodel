"""Guard against duplicate test names that silently shadow earlier tests."""

import ast
from collections import Counter
from pathlib import Path

TESTS_DIR = Path(__file__).parent


def _duplicates(source: str, label: str) -> list[str]:
    """Return 'file: name' entries for names defined twice in the same scope."""
    tree = ast.parse(source)
    found: list[str] = []

    def check(body: list[ast.stmt], scope: str) -> None:
        names = [
            n.name
            for n in body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        for name, count in Counter(names).items():
            if count > 1:
                found.append(f"{label}: {scope}{name} defined {count} times")

    check(tree.body, "")
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            check(node.body, f"{node.name}.")
    return found


def test_no_duplicate_definitions_in_test_modules():
    offenders: list[str] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        offenders += _duplicates(path.read_text(encoding="utf-8"), path.name)
    assert not offenders, "Shadowed tests never run:\n" + "\n".join(offenders)


def test_detector_flags_duplicates(tmp_path):
    sample = tmp_path / "test_sample.py"
    sample.write_text(
        "class TestA:\n    def test_x(self): ...\n    def test_x(self): ...\n"
        "class TestA: ...\n"
        "def test_f(): ...\ndef test_f(): ...\n"
    )
    found = _duplicates(sample.read_text(), sample.name)
    assert len(found) == 3
    assert any("TestA.test_x" in f for f in found)
    assert any("TestA defined" in f for f in found)
    assert any("test_f" in f for f in found)
