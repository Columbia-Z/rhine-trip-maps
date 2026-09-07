"""Build allowlisted portable or App Service ZIPs with stable metadata."""

import argparse
from io import BytesIO
from pathlib import Path
from stat import S_IFREG
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from app import DOWNLOAD_NAME, PORTABLE_ASSETS, PUBLIC_ASSETS


ROOT = Path(__file__).resolve().parents[1]


def archive_bytes(files):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, path in sorted(files.items()):
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Archive input must be a regular file: {name}")
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (S_IFREG | 0o644) << 16
            # Stored entries also reproduce byte-for-byte across zlib versions.
            entry.compress_type = ZIP_STORED
            archive.writestr(entry, path.read_bytes())
    return buffer.getvalue()


def portable_zip(root=ROOT):
    return archive_bytes({name: root / "public" / name for name in PORTABLE_ASSETS})


def deployment_zip(root=ROOT):
    download = root / "public" / DOWNLOAD_NAME
    if download.read_bytes() != portable_zip(root):
        raise ValueError("Portable ZIP is stale; run python -m scripts.build_zip")
    files = {name: root / name for name in ("app.py", "requirements.txt")}
    files.update({f"public/{name}": root / "public" / name for name in PUBLIC_ASSETS})
    return archive_bytes(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Fail if the portable ZIP is stale")
    mode.add_argument("--deployment", action="store_true", help="Build dist/app-service.zip")
    args = parser.parse_args()

    if args.deployment:
        content = deployment_zip()
        output = ROOT / "dist" / "app-service.zip"
    else:
        content = portable_zip()
        output = ROOT / "public" / DOWNLOAD_NAME

    if args.check:
        if not output.is_file() or output.read_bytes() != content:
            parser.exit(1, "Portable ZIP is missing or stale; run python -m scripts.build_zip\n")
        print("Portable ZIP is up to date.")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        print(f"Built {output.relative_to(ROOT)} ({len(content)} bytes).")


if __name__ == "__main__":
    main()
