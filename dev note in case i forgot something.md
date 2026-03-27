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

Replace my name as your current Windows user name, always ensure the AutoIt DLL is installed!

> I assume you've installed Python 3.8-3.14, so do `pip install autoit` and it should install the `AutoItX3_x64.dll` for you!

### Option 2: Nuitka

```bash
python -m nuitka main.py --standalone --onefile --windows-console-mode=disable --windows-icon-from-ico=lib/official_release.ico --include-data-dir=lib=lib --include-data-file=C:\Users\Akitosama\AppData\Local\Programs\Python\Python312\Lib\site-packages\autoit\lib\AutoItX3_x64.dll=autoit\lib\AutoItX3_x64.dll --static-libpython=no --remove-output --output-filename=CoteabMacro.exe
```

---

## Optional Flags / Notes

- `--icon="lib/aga.ico"` — You can change `aga.ico` to your desired icon with `.ico` format, the macro will use your custom one!
- `--upx-dir "C:\Users\your_user_here\path_to_upx_folder"` — Optional flag for PyInstaller. This flag will compress the EXE size to be as small as possible. Otherwise, remove the `--upx` flag if you don't want to compress it.
