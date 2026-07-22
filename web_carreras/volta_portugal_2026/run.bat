@echo off
cd /d "%~dp0"
echo Iniciando servidor para Volta a Portugal 2026...
echo Abre http://127.0.0.1:8080 en tu navegador
echo Presiona Ctrl+C para detener
"C:\Users\echav\AppData\Local\Programs\Python\Python313\python.exe" -m http.server 8080
pause
