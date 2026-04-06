# Dev Note (In case i forgot something)

> **IMPORTANT (PLEASE DO THIS FIRST LOW-ATTENTION SPAN USER)**
> You need to get Node.js (for npm command): https://nodejs.org/en/download

## 1. Create Frontend Template

```bash
cmd.exe /c "npx create-tauri-app@latest . --manager npm --template react-ts -y --force"
```

No need to create if `frontend` folder already exists.

## 2. Create the Dist Build

Run inside the `frontend` folder:

```bash
npm install
```

> This installs all the `node_modules` dependencies. You **must** run this at least once before building, or whenever you delete the `node_modules` folder / clone fresh.

Then build:

```bash
npm run build
```

This compiles the modern UI into `index.html` and requires `main.py` to find that `index.html` from the `dist` folder and use it.

> Remember to move the whole `dist` folder inside `frontend` folder to `lib` folder.

> **ALWAYS COMPILE THE DIST BUILD FIRST WHENEVER YOU CHANGE SOMETHING TO THE FRONTEND/TSX FILE OTHERWISE THE PYTHON WILL ONLY LOOK FOR THE OLD DIST FILE**

---

## Useful Commands

### Find any string or function name (in case you're so lost smh)

Run this terminal command inside the `biome_tracker` folder so it would tell you the thing in relevant `.py` files:

```bash
findstr /s /n /i "stuff u want to find" *.py
```

---

## Python Setup

- If you haven't installed Python, install it here: https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
- Install the Python requirements for macro development **(IMPORTANT/run it inside the development source folder so it could find the requirements.txt)**:

```bash
pip install -r requirements.txt
```

---

## Compile `main.py` to EXE

### Option 1: PyInstaller (must use Python 3.8-3.14)

```bash
pyinstaller --name="CoteabMacro" --noconsole --onefile --icon="lib/official_release.ico" --add-data "lib;lib" --add-data "C:\Users\Akitosama\AppData\Local\Programs\Python\Python312\Lib\site-packages\autoit\lib\AutoItX3_x64.dll;autoit\lib" --collect-all webview --collect-all discord --upx-dir "C:\Users\Akitosama\Documents\upx-5.1.0-win64" main.py
```

### Option 1.2: PyInstaller in isolated enviroment (aka venv) (must use Python 3.8-3.14)

> This is the recommended method. Using a venv keeps your build dependencies isolated from your system Python (making the macro when compiles to ".exe" in smaller size yippie)

**Step 1:** Fix PowerShell policy (runs this in CMD or powershell, this might prevents "script cannot be loaded" error):

```bash
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

**Step 2:** Create the venv (skip if `venv_build` folder already exists):

```bash
python -m venv venv_build
```

**Step 3:** Activate the venv:

```bash
.\venv_build\Scripts\activate
```

> You should see `(venv_build)` at the start of your terminal prompt. If you don't, the venv is not active!

**Step 4:** Install all dependencies inside the venv (skip if already installed):

```bash
pip install -r requirements.txt
pip install pyinstaller
```

> This installs everything the macro needs + PyInstaller itself into the venv.

**Step 5:** Build the frontend dist (skip if `lib/dist` is already up to date):

```bash
cd frontend
npm run build
```

> Then copy/move the `frontend/dist` folder into the `lib` folder.

**Step 6:** Compile the EXE:

```bash
pyinstaller --name="CoteabMacro" --noconsole --onefile --icon="lib/official_release.ico" --add-data "lib;lib" --add-data "venv_build\Lib\site-packages\autoit\lib\AutoItX3_x64.dll;autoit\lib" --collect-all webview --collect-all discord --upx-dir "C:\Users\Akitosama\Documents\upx-5.1.0-win64" main.py
```

> Replace my user `Akitosama` with your Windows username and your current directory one mine is "C:\Users\Akitosama\Documents\" for example. The compiled EXE will be in `dist/CoteabMacro.exe`.

**Step 7:** Deactivate the venv when done (optional):

```bash
deactivate
```

> Make sure AutoIt is installed in the venv! Run `pip install autoit` inside the activated venv if it's missing.

### Option 2: Nuitka

```bash
python -m nuitka main.py --onefile --windows-console-mode=disable --windows-icon-from-ico=lib/official_release.ico --include-data-dir=lib=lib --include-data-file=C:\Users\Akitosama\AppData\Local\Programs\Python\Python312\Lib\site-packages\autoit\lib\AutoItX3_x64.dll=autoit\lib\AutoItX3_x64.dll --static-libpython=no --output-filename=CoteabMacro.exe --remove-output --jobs=0 --python-flag=no_docstrings
```

---

## Optional Flags / Notes

- `--icon="lib/aga.ico"` — You can change `aga.ico` to your desired icon with `.ico` format, the macro will use your custom one!
- `--upx-dir "C:\Users\your_user_here\path_to_upx_folder"` — Optional flag for PyInstaller. This flag will compress the EXE size to be as small as possible. Otherwise, remove the `--upx` flag if you don't want to compress it.
