from __future__ import annotations

from pathlib import Path

from eve_production_tool.app.paths import AppPaths


def test_explicit_paths_are_created_below_selected_directory(tmp_path: Path) -> None:
    paths = AppPaths.in_directory(tmp_path / "profile")

    paths.ensure_directories()

    assert paths.data_dir == (tmp_path / "profile").resolve()
    assert paths.database_path.parent == paths.data_dir
    assert paths.backup_dir.is_dir()
    assert paths.log_dir.is_dir()
