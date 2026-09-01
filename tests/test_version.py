from __future__ import annotations

import tomllib
from pathlib import Path

from eve_dolphin import __version__


def test_package_uses_single_dynamic_version_source() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["dynamic"] == ["version"]
    assert "version" not in project["project"]
    assert project["tool"]["hatch"]["version"]["path"] == "src/eve_dolphin/version.py"
    assert __version__ == "0.4.8"
