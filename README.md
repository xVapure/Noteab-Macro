# Coteab Macro

Coteab Macro is a Windows macro app with a Python backend and a React frontend.

## Download

The compiled Windows build is published as:

- `CoteabMacro.exe`

## Source

Main project files:

- `main.py` starts the desktop app.
- `biome_tracker/` contains the macro logic.
- `frontend/` contains the React UI.
- `lib/dist/` contains the built frontend loaded by the Python app.

## Build

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Build the frontend:

```powershell
cd frontend
npm install
npm run build
```

Compile the executable with PyInstaller:

```powershell
pyinstaller --name="CoteabMacro" --noconsole --onefile --icon="lib/official_release.ico" --add-data "lib;lib" --collect-all webview --collect-all discord main.py
```

The output executable is usually created at `dist/CoteabMacro.exe`.

## Publish

From the source repo, run:

```powershell
.\scripts\publish-public.ps1
```

That script publishes only the latest `CoteabMacro.exe` to the public `mattstellar/Coteab` repo, commits, and pushes it.
