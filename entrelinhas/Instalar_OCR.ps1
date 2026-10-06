$ErrorActionPreference = 'Stop'
$ocrProjectRoot = $PSScriptRoot
$ocrInstallRoot = Join-Path $ocrProjectRoot '.runtime\tools\tesseract'
$ocrDataRoot = Join-Path $ocrProjectRoot '.runtime\tools\tessdata'
Write-Host 'Instala o OCR local Tesseract. Nenhum material será enviado a um serviço externo.'
Write-Host 'Se o Windows pedir autorização para instalar, confirme a janela para continuar.'
& winget install --id UB-Mannheim.TesseractOCR --exact --source winget --silent --disable-interactivity --location $ocrInstallRoot
if ($LASTEXITCODE -ne 0) { throw 'A instalação não foi concluída. O OCR permanece desativado.' }
New-Item -ItemType Directory -Path $ocrDataRoot -Force | Out-Null
foreach ($ocrLanguage in @('por','eng')) {
    $ocrDataFile = Join-Path $ocrDataRoot ($ocrLanguage + '.traineddata')
    if (-not (Test-Path -LiteralPath $ocrDataFile)) {
        Invoke-WebRequest -Uri ('https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/' + $ocrLanguage + '.traineddata') -OutFile $ocrDataFile
    }
}
Write-Host 'Dados oficiais de português e inglês preparados para reconhecimento clássico (--oem 0).'
Write-Host 'Execute os testes de OCR antes de considerar a função validada.'
