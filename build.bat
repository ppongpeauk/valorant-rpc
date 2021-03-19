rd /S /Q "build"
rd /S /Q "dist"
python -O -m PyInstaller -F --name "rpc-extension" --hidden-import "pystray._win32" "main.py" --icon "resources/favicon.ico"
Xcopy /E /I "resources" "dist/resources/"
copy "config.json" "dist"
copy "LICENSE" "dist"
pause