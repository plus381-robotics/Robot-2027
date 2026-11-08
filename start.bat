@echo off
rem Eurosim (simulator i editor taktika) iz ovog repoa, bez instaliranja Python-a.
rem Prvi put uv skine Python i biblioteke (~1 min, treba internet); posle radi i bez interneta.
rem Uvek je ovo najnovija verzija iz repoa: posle "git pull" (ili Repo, Pull latest u aplikaciji) samo ponovo pokreni.
cd /d "%~dp0"
set "UV="
where uv >nul 2>nul && set "UV=uv"
if not defined UV if exist ".tools\uv.exe" set "UV=.tools\uv.exe"
if not defined UV (
  echo Treba uv ^(jedan fajl, bez admin prava^): https://docs.astral.sh/uv/
  choice /M "Da ga skinem u .tools u ovom repou"
  if errorlevel 2 exit /b 1
  powershell -NoProfile -ExecutionPolicy ByPass -Command "$env:UV_INSTALL_DIR=%~dp0.tools; $env:UV_NO_MODIFY_PATH=1; irm https://astral.sh/uv/install.ps1 | iex"
  set "UV=.tools\uv.exe"
)
"%UV%" run --project simulator python simulator\sim.py serve %*
if errorlevel 1 pause
