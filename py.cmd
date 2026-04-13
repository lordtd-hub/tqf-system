@echo off
setlocal
set "PYTHON_LAUNCHER=%LocalAppData%\Programs\Python\Launcher\py.exe"
if not exist "%PYTHON_LAUNCHER%" (
    echo Python launcher not found at "%PYTHON_LAUNCHER%"
    exit /b 1
)
"%PYTHON_LAUNCHER%" %*
