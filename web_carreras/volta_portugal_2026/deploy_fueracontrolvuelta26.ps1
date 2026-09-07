$ErrorActionPreference = "Stop"

# Reutiliza el bucket público existente (allUsers:objectViewer ya concedido a nivel de bucket)
$bucket = "gs://bbh-stats-32938080-1ff1d-fueracontrol"
$objectName = "fueracontrolvuelta26"
$file = Join-Path $PSScriptRoot "fueracontrol.html"
$url = "https://storage.googleapis.com/bbh-stats-32938080-1ff1d-fueracontrol/$objectName"

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

Write-Host "Subiendo fueracontrol.html como '$objectName' (sin extensión, Content-Type text/html)..."
gcloud storage cp $file "$bucket/$objectName" `
    --content-type="text/html; charset=utf-8" `
    --cache-control="no-cache,max-age=0"
if ($LASTEXITCODE -ne 0) {
    throw "Falló la subida de $objectName"
}

$response = Invoke-WebRequest -UseBasicParsing "${url}?updated=$([DateTimeOffset]::Now.ToUnixTimeMilliseconds())"
if ($response.StatusCode -ne 200) {
    throw "La URL pública respondió con HTTP $($response.StatusCode)"
}

Write-Host "Despliegue completado correctamente."
Write-Host "URL: $url"
Write-Host "El botón 'Tiempo ganador' usará como respaldo el backend Cloud Run fueracontrolvuelta26 (CORS habilitado)."
