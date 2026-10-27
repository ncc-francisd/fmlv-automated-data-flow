"""No file a person wrote may contain a control character.

**This has bitten three times, and silently every time.** A `\\b` that loses its backslash
— written into a non-raw string, or mangled by a shell heredoc on the way into a file —
becomes `\\x08`, a literal backspace. The regex then cannot match anything, and nothing
says so: `grep` renders the byte invisibly, so the line reads exactly right.

* `malibu.py` lost every van's length to one, 9 October 2026.
* `coachman.py` carried one in `_OPTIONAL_HEADING` for twelve days. Its optional-equipment
  sections could never be recognised, so the day Coachman published one it would have been
  read as standard equipment.
* `config/manufacturers.csv` held one in Panama's notes, where `\\10E Hybrid` had been
  written into a non-raw string and octal `\\10` *is* 0x08.

The last one is the lesson: it is not only `\\b`. Any short octal or hex escape does this,
and the result always looks like whatever surrounded it.

Captured fixtures are exempt, because mirroring the source document is their whole job.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

#: Every C0 control except tab, newline and carriage return, plus DEL. Built from code
#: points rather than written as escapes, so that this file cannot fall to the very bug it
#: exists to catch.
_FORBIDDEN = frozenset(
    chr(code) for code in [*range(0x00, 0x09), 0x0B, 0x0C, *range(0x0E, 0x20), 0x7F]
)

_ROOTS = ("src", "tests", "config", "docs")

#: A fixture's job is to mirror what a manufacturer published, byte for byte. Knaus's
#: extracted price lists carry fifteen form feeds because the PDF has fifteen page breaks,
#: and "fixing" that would make the fixture a worse record of the thing it stands in for.
_CAPTURED = ("fixtures",)

_SUFFIXES = {".py", ".md", ".csv", ".json", ".txt"}

_PROJECT = Path(__file__).resolve().parents[1]


def _source_files() -> list[Path]:
    """Every file a person wrote, which is where a stray control character is a fault."""
    found: list[Path] = []
    for root in _ROOTS:
        for path in (_PROJECT / root).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if any(part in _CAPTURED for part in path.parts):
                continue
            if path.suffix.lower() in _SUFFIXES:
                found.append(path)
    return sorted(found)


def test_there_are_files_to_check() -> None:
    """A guard that finds nothing is not a guard."""
    assert len(_source_files()) > 100


def test_the_guard_can_see_a_control_character(tmp_path: Path) -> None:
    """The check itself is the thing most likely to be broken by what it looks for."""
    planted = tmp_path / "planted.py"
    planted.write_text("x = re.compile(" + chr(0x08) + "bword)", encoding="utf-8")
    assert _FORBIDDEN & set(planted.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: str(p.name))
def test_no_control_characters(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        pytest.skip(f"{path} is not UTF-8 text")
    found = _FORBIDDEN & set(text)
    if not found:
        return
    character = next(iter(sorted(found)))
    line = text[: text.index(character)].count("\n") + 1
    pytest.fail(
        f"{path.relative_to(_PROJECT)} line {line} contains {character!r} — almost "
        f"certainly an escape that lost its backslash. A regex carrying one can never "
        f"match, and grep renders it invisibly. See this file's docstring."
    )
