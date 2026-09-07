$ErrorActionPreference = "Stop"

$serviceName = "fueracontrolvuelta26"
$region = "europe-west1"
$serviceDir = Join-Path $PSScriptRoot "fueracontrol_service"
$sourceHtml = Join-Path $PSScriptRoot "fueracontrol.html"
$targetHtml = Join-Path $serviceDir "fueracontrol.html"

if (-not (Test-Path $sourceHtml)) {
    throw "No se encontró fueracontrol.html en $PSScriptRoot"
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud no está instalado o no está disponible en PATH"
}

gcloud auth list --filter=status:ACTIVE --format="value(account)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No hay una cuenta activa de Google Cloud. Ejecuta: gcloud auth login"
}

Write-Host "Sincronizando fueracontrol.html dentro de fueracontrol_service/..."
Copy-Item $sourceHtml $targetHtml -Force

Write-Host "Desplegando servicio Cloud Run '$serviceName' en $region..."
gcloud run deploy $serviceName `
    --source $serviceDir `
    --region $region `
    --allow-unauthenticated `
    --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Falló el despliegue de $serviceName"
}

$url = gcloud run services describe $serviceName --region $region --format="value(status.url)"
Write-Host "Despliegue completado correctamente."
Write-Host "URL: $url/fueracontrolvuelta26"
