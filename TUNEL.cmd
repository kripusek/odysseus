@echo off
setlocal
set "CF_EXE=%LOCALAPPDATA%\Odysseus-kripusek-runtime\cloudflared-2026.10.7.exe"
set "CF_TOKEN=%LOCALAPPDATA%\Odysseus-kripusek-private\tunnel-token.txt"
if not exist "%CF_EXE%" (
  echo Brak programu tunelu. Sprawdz dokumentacje dostepu zdalnego.
  exit /b 1
)
if not exist "%CF_TOKEN%" (
  echo Brak prywatnego pliku tunelu. Sprawdz dokumentacje dostepu zdalnego.
  exit /b 1
)
echo Uruchamianie prywatnego lacznika Cloudflare. Zamknij to okno, aby go zakonczyc.
"%CF_EXE%" --no-autoupdate tunnel run --token-file "%CF_TOKEN%"
exit /b %ERRORLEVEL%
