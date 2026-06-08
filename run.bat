@echo off
chcp 65001 >nul
title 스마팩 CMMS

echo.
echo  ██████╗███╗   ███╗███╗   ███╗███████╗
echo ██╔════╝████╗ ████║████╗ ████║██╔════╝
echo ██║     ██╔████╔██║██╔████╔██║███████╗
echo ██║     ██║╚██╔╝██║██║╚██╔╝██║╚════██║
echo ╚██████╗██║ ╚═╝ ██║██║ ╚═╝ ██║███████║
echo  ╚═════╝╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝
echo.
echo  스마트팩토리 CMMS v1.0
echo  ================================
echo.

:: Python 경로 찾기
set PYTHON=
for %%p in (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
    "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if exist %%p (
        set PYTHON=%%p
        goto :found
    )
)

where python >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON=python
    goto :found
)

echo [오류] Python을 찾을 수 없습니다.
echo https://www.python.org 에서 Python을 설치하세요.
pause
exit /b 1

:found
echo  Python: %PYTHON%
echo.

:: 패키지 확인 및 설치
echo  필요한 패키지를 확인합니다...
%PYTHON% -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo  패키지를 설치합니다 (최초 1회)...
    %PYTHON% -m pip install streamlit pandas plotly openpyxl --quiet
)

echo  앱을 시작합니다...
echo  브라우저에서 http://localhost:8501 로 접속하세요
echo.
echo  종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.
echo  ================================
echo.

cd /d "%~dp0"
%PYTHON% -m streamlit run app.py --server.port 8501 --server.headless false --browser.serverAddress localhost

pause
