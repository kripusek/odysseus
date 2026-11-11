@echo off
setlocal
cd /d "%~dp0"
set "ODYSSEUS_DATA_DIR=%LOCALAPPDATA%\Odysseus-kripusek-data"
set "AUTH_ENABLED=true"
set "LOCALHOST_BYPASS=false"
if exist "%LOCALAPPDATA%\Odysseus-kripusek-private\mobile-access.json" (
  set "COMPANION_BASE_URL=https://ai.kripusek.top"
  set "COMPANION_ACCESS_CREDENTIALS_FILE=%LOCALAPPDATA%\Odysseus-kripusek-private\mobile-access.json"
)
echo Odysseus: uruchamianie lokalnie na http://127.0.0.1:17011
echo Dane: %ODYSSEUS_DATA_DIR%
echo Pierwsze uruchomienie moze pobrac zaleznosci i poprosi o konto administratora.
echo Aby zakonczyc, nacisnij Ctrl+C.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-windows.ps1" -Port 17011 -BindHost 127.0.0.1
endlocal
