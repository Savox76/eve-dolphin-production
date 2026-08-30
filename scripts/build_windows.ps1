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
& $Executable --self-check

if ($LASTEXITCODE -ne 0) {
    throw "Packaged client self-check failed with exit code $LASTEXITCODE."
}
