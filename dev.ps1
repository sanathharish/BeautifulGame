# Development helper script for Windows PowerShell
# Usage:
#  .\dev.ps1 test       # run pytest
#  .\dev.ps1 lint       # run a simple lint (flake8) if available
param(
    [string]$task = 'test'
)

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-Not (Test-Path $python)) {
    Write-Host "Python executable not found at $python. Ensure the virtual env exists or adjust the path." -ForegroundColor Yellow
}

switch ($task) {
    'test' {
        & $python -m pytest -q
    }
    'lint' {
        & $python -m flake8 .
    }
    default {
        Write-Host "Unknown task: $task" -ForegroundColor Red
    }
}
