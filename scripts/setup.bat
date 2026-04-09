@echo off
:: PyTorch Buildings GUI — Environment Setup (Windows)
:: Installs all dependencies from the bundled neuromancer_repo.
:: No internet access to GitHub is required for neuromancer.

setlocal EnableDelayedExpansion

set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo ==========================================
echo  PyTorch Buildings GUI - Environment Setup
echo ==========================================
echo.

:: -----------------------------------------------
:: Python detection (3.10-3.12 supported)
:: -----------------------------------------------
set PYTHON_CMD=
for %%c in (python3.12 python3.11 python3.10 python3 python) do (
    where %%c >nul 2>&1
    if !errorlevel! == 0 (
        set PYTHON_CMD=%%c
        goto :found_python
    )
)
echo Error: Python 3.10 or newer is required but was not found.
echo Download from https://www.python.org/downloads/
exit /b 1

:found_python
for /f "tokens=2" %%v in ('!PYTHON_CMD! --version 2^>^&1') do set PYTHON_VERSION=%%v
echo [OK] Python !PYTHON_VERSION!
echo.

:: -----------------------------------------------
:: Virtual environment
:: -----------------------------------------------
echo Setting up virtual environment...
if not exist ".venv" (
    !PYTHON_CMD! -m venv .venv
    echo [OK] Created .venv
) else (
    echo [OK] Using existing .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
echo.

:: -----------------------------------------------
:: PyTorch (CPU build)
:: GPU users: replace with the appropriate command
:: from https://pytorch.org/get-started/locally/
:: -----------------------------------------------
echo Installing PyTorch stack...
pip install torch torchvision torchaudio -q
echo [OK] PyTorch installed
echo.

:: -----------------------------------------------
:: GUI + scientific dependencies
:: -----------------------------------------------
echo Installing GUI and scientific dependencies...
pip install PyQt6 numpy scipy matplotlib tqdm "beartype>=0.17.0" -q
echo [OK] Core dependencies installed
echo.

:: -----------------------------------------------
:: NeuroMANCER — bundled local copy
:: -----------------------------------------------
echo Installing bundled NeuroMANCER...
pip install torchdiffeq "networkx>=3,<4" "pydot==1.4.2" "plum-dispatch==1.7.3" "lightning>=2.0.0" -q
pip install -e "%ROOT%\neuromancer_repo" -q
echo [OK] NeuroMANCER installed from neuromancer_repo\
echo.

:: -----------------------------------------------
:: Verification
:: -----------------------------------------------
echo Verifying environment...
python -c ^
"import sys; " ^
"checks = [('torch', lambda: __import__('torch').__version__), ('torchdiffeq', lambda: __import__('torchdiffeq').__version__), ('numpy', lambda: __import__('numpy').__version__), ('matplotlib', lambda: __import__('matplotlib').__version__), ('PyQt6', lambda: __import__('PyQt6.QtCore', fromlist=['PYQT_VERSION_STR']).PYQT_VERSION_STR), ('neuromancer', lambda: __import__('neuromancer').__version__)];" ^
"[print(f'  OK {n}: {fn()}') for n, fn in checks];" ^
"from neuromancer.hvac.building_components import Envelope, RTU, VAVBox, SolarGains; print('  OK HVAC components importable');" ^
"print(chr(10) + 'All checks passed.')"
if errorlevel 1 (
    echo.
    echo Verification failed. Check the output above.
    exit /b 1
)

echo.
echo ==========================================
echo  Setup complete
echo ==========================================
echo.
echo Activate the environment:
echo   .venv\Scripts\activate
echo.
echo Run the application:
echo   python src\main.py
echo.
