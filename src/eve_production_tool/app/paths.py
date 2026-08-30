"""Operating-system appropriate paths for local application data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "EVE Production Tool"
APP_AUTHOR = "Savox76"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """All mutable paths used by one local installation profile."""

    data_dir: Path
    database_path: Path
    backup_dir: Path
    log_dir: Path

    @classmethod
    def for_current_user(cls) -> AppPaths:
        """Resolve paths without writing relative to the installation directory."""

        directories = PlatformDirs(APP_NAME, APP_AUTHOR, roaming=False, ensure_exists=False)
        data_dir = Path(directories.user_data_path)
        return cls(
            data_dir=data_dir,
            database_path=data_dir / "eve-production-tool.sqlite3",
            backup_dir=data_dir / "backups",
            log_dir=Path(directories.user_log_path),
        )

    @classmethod
    def in_directory(cls, base_dir: Path) -> AppPaths:
        """Create deterministic paths for tests and explicit portable runs."""

        base_dir = base_dir.resolve()
        return cls(
            data_dir=base_dir,
            database_path=base_dir / "eve-production-tool.sqlite3",
            backup_dir=base_dir / "backups",
            log_dir=base_dir / "logs",
        )

    def ensure_directories(self) -> None:
        """Create mutable application directories if they do not exist."""

        for directory in (self.data_dir, self.backup_dir, self.log_dir):
            directory.mkdir(parents=True, exist_ok=True)
