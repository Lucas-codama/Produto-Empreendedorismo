$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot '.runtime\server.pid'
if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output 'Nao ha um servidor iniciado pelo atalho para encerrar.'
    exit
}
$serverProcessId = [int](Get-Content -LiteralPath $pidFile)
$processInfo = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $serverProcessId)
$expectedServer = Join-Path $PSScriptRoot 'server.py'
if ($processInfo -and $processInfo.CommandLine -and $processInfo.CommandLine.Contains($expectedServer)) {
    Stop-Process -Id $serverProcessId
    Write-Output 'Entrelinhas encerrado. Os materiais continuam guardados localmente.'
} else {
    Write-Output 'O processo registrado nao corresponde ao servidor deste projeto; nenhum processo foi encerrado.'
}
