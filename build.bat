@echo off
echo ============================================
echo   Маркорез — Сборка .exe для Windows
echo ============================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден! Установите Python 3.10+ с python.org
    pause
    exit /b 1
)

REM Установка зависимостей
echo [1/3] Установка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости
    pause
    exit /b 1
)

echo.
echo [2/3] Сборка .exe...
pyinstaller --onefile --windowed ^
    --name "Markorez" ^
    --collect-all customtkinter ^
    --add-data ".;." ^
    main.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось собрать .exe
    echo Попробуйте альтернативную команду:
    echo   pyinstaller --onefile --windowed --name "Markorez" --collect-all customtkinter main.py
    pause
    exit /b 1
)

echo.
echo [3/3] Готово!
echo ============================================
echo   Файл .exe находится в папке: dist\Markorez.exe
echo ============================================
echo.
pause
