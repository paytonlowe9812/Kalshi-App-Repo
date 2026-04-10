@echo off
echo Building Kalshi Bot Builder...

cd /d "%~dp0..\.."

echo [1/3] Building frontend...
cd frontend
call npm install
call npm run build
cd ..

echo [2/3] Bundling with PyInstaller...
pip install pyinstaller
pyinstaller --onefile --add-data "frontend/dist;frontend/dist" --add-data "data;data" backend/main.py -n KalshiBotBuilder --distpath dist

echo [3/3] Build complete!
echo Executable: dist\KalshiBotBuilder.exe
pause
