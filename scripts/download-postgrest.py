"""Fetch a pinned official release for the portable QA harness."""

import io
import os
import tarfile
import urllib.request
import zipfile
from pathlib import Path

version = "16.5"
directory = Path(".local/postgrest")
directory.mkdir(parents=True, exist_ok=True)
asset = (
    f"postgrest-v{version}-windows-x86-64.zip"
    if os.name == "nt"
    else f"postgrest-v{version}-linux-static-x86-64.tar.xz"
)
url = f"https://github.com/PostgREST/postgrest/releases/download/v{version}/{asset}"
with urllib.request.urlopen(url, timeout=60) as response:
    archive = io.BytesIO(response.read())
if os.name == "nt":
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            if Path(member.filename).name == "postgrest.exe":
                (directory / "postgrest.exe").write_bytes(handle.read(member))
else:
    with tarfile.open(fileobj=archive, mode="r:xz") as handle:
        for member in handle.getmembers():
            if Path(member.name).name == "postgrest" and member.isfile():
                file = handle.extractfile(member)
                if file:
                    (directory / "postgrest").write_bytes(file.read())
    (directory / "postgrest").chmod(0o755)
print(f"Installed official PostgREST {version} for portable QA.")
