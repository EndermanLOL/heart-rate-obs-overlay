@echo off
REM ============================================================
REM  build.bat - Compila Heart Rate OBS Overlay como .exe portable
REM  Debe ejecutarse en Windows con Python 3.9+ instalado.
REM ============================================================

echo === Heart Rate OBS Overlay - build script ===

python -m venv build_venv
call build_venv\Scripts\activate.bat

echo.
echo Instalando dependencias...
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Compilando con PyInstaller...

set ICON_ARG=
if exist "assets\icon.ico" (
    set ICON_ARG=--icon "assets\icon.ico"
)

pyinstaller --noconfirm --onefile --windowed ^
    --name "HeartRateOBSOverlay" ^
    %ICON_ARG% ^
    main.py

echo.
echo === Listo ===
echo El ejecutable esta en: dist\HeartRateOBSOverlay.exe
pause
