# Building Executable

## Requirements
```bash
pip install pyinstaller
```

## Build Instructions

### Windows
```powershell
# Install PyInstaller
pip install pyinstaller

# Build executable (single-file)
pyinstaller --onefile build_exe.spec

# Output will be in dist/ (look for UNESWAWiFiAutoConnect.exe)
```

The executable will:
- Request admin privileges automatically (UAC prompt)
- Include all dependencies
- Be a single file (no folder needed)
- Be around 40-60MB (much smaller than Electron)

### Linux
```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller build_exe.spec

# Output will be in dist/UNESWAWiFiAutoConnect
```

## Notes
- First build takes 2-3 minutes
- Subsequent builds are faster
- UPX compression is enabled to reduce file size
- Admin elevation is built into the Windows executable
- Icon is included if assets/icon.ico exists

## Distribution
Just distribute the single executable file from the `build_output` or `dist/` folder. Users don't need Python installed.
