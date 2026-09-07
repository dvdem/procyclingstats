$ErrorActionPreference = "Stop"

$bucket = "gs://bbh-stats-32938080-1ff1d-fueracontrol"
$file = Join-Path $PSScriptRoot "fueracontrol.html"
$url = "https://storage.googleapis.com/bbh-stats-32938080-1ff1d-fueracontrol/fueracontrol.html"

if (-not (Test-Path $file)) {
    throw "No se encontró fueracontrol.html en $PSScriptRoot"
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud no está instalado o no está disponible en PATH"
}

gcloud auth list --filter=status:ACTIVE --format="value(account)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "No hay una cuenta activa de Google Cloud. Ejecuta: gcloud auth login"
}

Write-Host "Subiendo únicamente fueracontrol.html..."
gcloud storage cp $file "$bucket/fueracontrol.html" --cache-control="no-cache,max-age=0"
if ($LASTEXITCODE -ne 0) {
    throw "Falló la subida de fueracontrol.html"
}

$response = Invoke-WebRequest -UseBasicParsing "${url}?updated=$([DateTimeOffset]::Now.ToUnixTimeMilliseconds())"
if ($response.StatusCode -ne 200) {
    throw "La URL pública respondió con HTTP $($response.StatusCode)"
}

Write-Host "Despliegue completado correctamente."
Write-Host "URL: $url"
