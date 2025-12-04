param([string]$arg)

# Activate virtual environment
if (-not (Test-Path variable:VIRTUAL_ENV)) {
    .\.venv\Scripts\Activate.ps1
}

if ($arg -eq "-c") {
    pytest tests/backend --cov=backend --cov-report=term-missing -v --color=yes
} else {
    pytest -v --color=yes
}
