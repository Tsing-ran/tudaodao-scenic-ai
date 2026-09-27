# Pack project for AutoDL upload
# Run from the project root or just double-click in Explorer
# Output: D:\Desktop\digital-human-deploy.zip

$src     = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$stage   = Join-Path $env:TEMP "dh_deploy_stage\digital-human"
$zipPath = Join-Path ([System.IO.Path]::GetDirectoryName($src)) "digital-human-deploy.zip"

Write-Host "Source: $src"
Write-Host "Output: $zipPath"
Write-Host "Staging files..."

$stageParent = Split-Path $stage -Parent
if (Test-Path $stageParent) { Remove-Item $stageParent -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null

robocopy "$src\backend"       "$stage\backend"       /E /NP /NFL /NDL /NJH /NJS /XD __pycache__ | Out-Null
robocopy "$src\frontend\dist" "$stage\frontend\dist" /E /NP /NFL /NDL /NJH /NJS              | Out-Null
robocopy "$src\deploy"        "$stage\deploy"        /E /NP /NFL /NDL /NJH /NJS              | Out-Null

Write-Host "Compressing..."
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $stage -DestinationPath $zipPath

Remove-Item $stageParent -Recurse -Force

$mb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "Done: $zipPath"
Write-Host "Size: $mb MB"
