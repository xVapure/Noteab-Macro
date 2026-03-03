import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LATEST_RELEASE_API = "https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest"
ASSET_NAME = "CoteabMacro.exe"
USER_AGENT = "noteab-macro-bootstrapper"

print("Downloading the latest release of CoteabMacro.exe please wait :robot: :money_mouth_face:")
def get_latest_release_data() -> dict:
    request = Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub API returned HTTP {response.status}")
        return json.load(response)


def find_asset_url(release_data: dict, asset_name: str) -> str:
    for asset in release_data.get("assets", []):
        if asset.get("name") == asset_name:
            download_url = asset.get("browser_download_url")
            if download_url:
                return download_url
    raise RuntimeError(f"Asset '{asset_name}' was not found in the latest release.")


def download_file(url: str, output_path: Path) -> None:
    request = Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request, timeout=120) as response, output_path.open("wb") as output_file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output_file.write(chunk)


def run_executable(exe_path: Path) -> None:
    subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))


def main() -> int:
    try:
        release_data = get_latest_release_data()
        asset_url = find_asset_url(release_data, ASSET_NAME)
    except (HTTPError, URLError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Failed to get release information: {error}")
        return 1

    output_path = Path(__file__).resolve().parent / ASSET_NAME
    try:
        download_file(asset_url, output_path)
    except (HTTPError, URLError, OSError) as error:
        print(f"Failed to download {ASSET_NAME}: {error}")
        return 1

    try:
        run_executable(output_path)
    except OSError as error:
        print(f"Downloaded but failed to run {ASSET_NAME}: {error}")
        return 1

    print(f"""Downloaded and launched: {output_path} please wait for le macro to open
          If you wish you can delete all the python depencencies and this script now, they are not needed anymore""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
