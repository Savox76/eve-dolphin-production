from __future__ import annotations

from pathlib import Path

import pytest

from eve_production_tool.app.bootstrap import build_context, main, run_self_check
from eve_production_tool.app.paths import AppPaths


def test_context_initializes_local_database(tmp_path: Path) -> None:
    paths = AppPaths.in_directory(tmp_path)

    context = build_context(paths, "en")

    assert context.database.is_current()
    assert context.characters.list_all() == ()
    assert context.translator.language == "en"
    assert paths.database_path.is_file()


def test_self_check_reports_version_and_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = run_self_check(AppPaths.in_directory(tmp_path))

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK (schema 1)" in captured.out


def test_cli_self_check_uses_temporary_profile(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--self-check"]) == 0
    assert "EVE Production Tool" in capsys.readouterr().out
