$ErrorActionPreference = "Stop"

$serviceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $serviceRoot ".venv\Scripts\python.exe"
$pythonCommand = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $serviceRoot
try {
    & $pythonCommand -m pytest
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
