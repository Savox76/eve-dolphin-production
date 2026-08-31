"""Public release discovery and safe local update application."""

from eve_dolphin.updates.applier import apply_staged_update
from eve_dolphin.updates.client import GitHubReleaseClient
from eve_dolphin.updates.installer import (
    UpdateDownloadError,
    UpdateInstaller,
    UpdatePackageError,
    launch_staged_update,
)
from eve_dolphin.updates.models import ReleaseAsset, ReleaseInfo, StagedUpdate
from eve_dolphin.updates.status import (
    UpdateState,
    UpdateStateStatus,
    consume_update_result,
)

__all__ = [
    "GitHubReleaseClient",
    "ReleaseAsset",
    "ReleaseInfo",
    "StagedUpdate",
    "UpdateDownloadError",
    "UpdateInstaller",
    "UpdatePackageError",
    "UpdateState",
    "UpdateStateStatus",
    "apply_staged_update",
    "consume_update_result",
    "launch_staged_update",
]
