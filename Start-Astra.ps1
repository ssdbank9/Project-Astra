param(
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$astraData = Join-Path $PSScriptRoot 'data'
$astraDatabase = Join-Path $astraData 'astra.sqlite3'
$astraPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'

if (-not (Test-Path -LiteralPath $astraDatabase -PathType Leaf)) {
    throw "Astra database missing: $astraDatabase. Restore the existing database before starting."
}
if (-not (Test-Path -LiteralPath $astraPython -PathType Leaf)) {
    throw "Astra Python environment missing: $astraPython."
}

Write-Output "Astra data: $astraData"
Write-Output 'Local address: http://127.0.0.1:8765'
if ($Check) {
    return
}

$astraPreviousHome = [Environment]::GetEnvironmentVariable('ASTRA_HOME', 'Process')
try {
    $env:ASTRA_HOME = $astraData
    & $astraPython -m astra serve --host 127.0.0.1 --port 8765
    if ($LASTEXITCODE -ne 0) {
        throw "Astra exited with code $LASTEXITCODE."
    }
}
finally {
    [Environment]::SetEnvironmentVariable('ASTRA_HOME', $astraPreviousHome, 'Process')
}
