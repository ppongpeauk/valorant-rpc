python -O -m PyInstaller -F --name "rpc-extension" --hidden-import "pystray._win32" main.py --icon favicon.ico
pause