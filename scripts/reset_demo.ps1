$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
$resetScript = Join-Path $repoRoot "scripts\reset_demo.py"

if (Test-Path -LiteralPath $venvPython) {
    & $venvPython $resetScript
} else {
    & python $resetScript
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
