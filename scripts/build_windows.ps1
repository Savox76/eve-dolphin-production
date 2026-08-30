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
& $Executable --self-check

if ($LASTEXITCODE -ne 0) {
    throw "Packaged client self-check failed with exit code $LASTEXITCODE."
}
