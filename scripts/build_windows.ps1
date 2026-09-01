$ErrorActionPreference = "Stop"

uv run pyinstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "EVE-Dolphin" `
    --paths "src" `
    --collect-all "keyring" `
    "src/eve_dolphin/__main__.py"

$Executable = "dist/EVE-Dolphin/EVE-Dolphin.exe"
$Version = uv run python -c "from eve_dolphin import __version__; print(__version__)"
$BuildInfo = @{
    version = $Version.Trim()
    distribution_repository = "Savox76/eve-dolphin-production"
} | ConvertTo-Json
$BuildInfo | Set-Content -Path "dist/EVE-Dolphin/build-info.json" -Encoding utf8
$InitialCheck = Start-Process `
    -FilePath $Executable `
    -ArgumentList "--self-check" `
    -Wait `
    -PassThru
if ($InitialCheck.ExitCode -ne 0) {
    throw "Packaged client self-check failed with exit code $($InitialCheck.ExitCode)."
}

# Exercise the real out-of-process directory replacement on Windows. A marker
# in the target proves that the complete installation, not just the EXE, was
# replaced before the updated client is validated.
$UpdateTestRoot = Join-Path $env:RUNNER_TEMP "eve-dolphin-update-e2e"
if (Test-Path $UpdateTestRoot) {
    Remove-Item -Recurse -Force $UpdateTestRoot
}
$UpdateSource = Join-Path $UpdateTestRoot "updates/v$($Version.Trim())"
$UpdateTarget = Join-Path $UpdateTestRoot "installed"
New-Item -ItemType Directory -Path (Split-Path $UpdateSource) -Force | Out-Null
Copy-Item -Recurse "dist/EVE-Dolphin" $UpdateSource
Copy-Item -Recurse "dist/EVE-Dolphin" $UpdateTarget
"old-installation" | Set-Content (Join-Path $UpdateTarget "obsolete-marker.txt")
$ShortLivedParent = Start-Process powershell.exe -ArgumentList @(
    "-NoProfile", "-Command", "Start-Sleep -Milliseconds 750"
) -PassThru -WindowStyle Hidden
$UpdaterProcess = Start-Process `
    -FilePath (Join-Path $UpdateSource "EVE-Dolphin.exe") `
    -ArgumentList @(
        "--apply-update",
        "--update-source", "`"$UpdateSource`"",
        "--update-target", "`"$UpdateTarget`"",
        "--wait-pid", $ShortLivedParent.Id
    ) `
    -Wait `
    -PassThru
if ($UpdaterProcess.ExitCode -ne 0) {
    throw "Packaged update end-to-end test failed with exit code $($UpdaterProcess.ExitCode)."
}
if (Test-Path (Join-Path $UpdateTarget "obsolete-marker.txt")) {
    throw "Packaged update end-to-end test did not replace the installation."
}
$UpdatedCheck = Start-Process `
    -FilePath (Join-Path $UpdateTarget "EVE-Dolphin.exe") `
    -ArgumentList "--self-check" `
    -Wait `
    -PassThru
if ($UpdatedCheck.ExitCode -ne 0) {
    throw "Updated package self-check failed with exit code $($UpdatedCheck.ExitCode)."
}
Remove-Item -Recurse -Force $UpdateTestRoot
