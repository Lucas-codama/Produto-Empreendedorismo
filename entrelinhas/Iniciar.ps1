param([switch]$SemAbrirNavegador)
$ErrorActionPreference = 'Stop'
$projectFolder = $PSScriptRoot
$serverUrl = 'http://127.0.0.1:8765'
$pythonRuntime = 'C:\Users\Lucas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $pythonRuntime)) {
    $pythonRuntime = (Get-Command python -ErrorAction Stop).Source
}
$ready = $false
try {
    $health = Invoke-RestMethod -Uri ($serverUrl + '/api/health') -TimeoutSec 2
    $ready = $health.app -eq 'entrelinhas'
} catch {}
if (-not $ready) {
    $runtimeFolder = Join-Path $projectFolder '.runtime'
    New-Item -ItemType Directory -Path $runtimeFolder -Force | Out-Null
    $serverFile = Join-Path $projectFolder 'server.py'
    $serverProcess = Start-Process -FilePath $pythonRuntime -ArgumentList @('"' + $serverFile + '"') -WorkingDirectory $projectFolder -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeFolder 'server.log') -RedirectStandardError (Join-Path $runtimeFolder 'server-error.log')
    for ($attemptIndex = 0; $attemptIndex -lt 30; $attemptIndex++) {
        Start-Sleep -Milliseconds 300
        try {
            $health = Invoke-RestMethod -Uri ($serverUrl + '/api/health') -TimeoutSec 1
            if ($health.app -eq 'entrelinhas') { $ready = $true; break }
        } catch {}
        if ($serverProcess.HasExited) { break }
    }
    if ($ready) { $serverProcess.Id | Set-Content -LiteralPath (Join-Path $runtimeFolder 'server.pid') }
}
if (-not $ready) {
    throw 'Nao foi possivel iniciar o Entrelinhas. Confira .runtime\server-error.log ou se a porta 8765 esta ocupada.'
}
if (-not $SemAbrirNavegador) { Start-Process $serverUrl }
Write-Output ('Entrelinhas aberto em ' + $serverUrl)
