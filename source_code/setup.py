from cx_Freeze import setup, Executable
executables = [
    Executable(
        "biome_activity_source.py",
        icon="NoteabBiomeTracker.ico",
        base=None,
        target_name="BiomeActivity.exe",
    ),
    Executable(
        "biome_notifier_source_gui.pyw",
        icon="NoteabBiomeTracker.ico",
        base="Win32GUI",
        target_name="BiomeNotifierGUI.exe",
    )
]


setup(
    name="Noteab Biome Tracker",
    version="1.5.0",
    description="Biome Activity Tracker Using Discord Rich Presence (Noteab)",
    executables=executables,
    options={
        "build_exe": {
            "packages": [
                "os", "ahk", "time", "win32gui", "win32con", "discord", 
                "asyncio", "json", "requests", "datetime", "dotenv", 
                "tkinter", "re"
            ],
            "include_files": ["config.json", ".env"],
        }
    }
)

## To build the exe file, run this command in the terminal (oh and yeah you can do your own custom tracker!)
## --> python setup.py build

