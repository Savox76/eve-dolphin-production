"""Public release discovery and safe local update application."""

from eve_dolphin.updates.applier import apply_staged_update
from eve_dolphin.updates.client import GitHubReleaseClient
from eve_dolphin.updates.installer import UpdateInstaller, launch_staged_update
from eve_dolphin.updates.models import ReleaseAsset, ReleaseInfo, StagedUpdate

__all__ = [
    "GitHubReleaseClient",
    "ReleaseAsset",
    "ReleaseInfo",
    "StagedUpdate",
    "UpdateInstaller",
    "apply_staged_update",
    "launch_staged_update",
]
