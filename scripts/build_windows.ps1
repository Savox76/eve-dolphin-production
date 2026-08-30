$ErrorActionPreference = "Stop"

uv run pyinstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "EVE-Production-Tool" `
    --paths "src" `
    --collect-all "keyring" `
    "src/eve_production_tool/__main__.py"

$Executable = "dist/EVE-Production-Tool/EVE-Production-Tool.exe"
& $Executable --self-check

if ($LASTEXITCODE -ne 0) {
    throw "Packaged client self-check failed with exit code $LASTEXITCODE."
}
