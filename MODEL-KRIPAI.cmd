@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Najpierw uruchom START.cmd, aby przygotowac srodowisko Python.
  exit /b 1
)
"venv\Scripts\python.exe" scripts\kripai_llama_launcher.py
