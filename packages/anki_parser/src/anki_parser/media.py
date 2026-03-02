from __future__ import annotations

import zipfile
from pathlib import Path


def extract_media_files(apkg_path: str | Path, output_dir: str | Path) -> dict[str, Path]:
    """Extract media files from an .apkg ZIP to output_dir.

    Renames files from their numeric names to their original filenames using
    the media map stored in the archive.

    Returns a dict mapping original filename → extracted file path.
    """
    import json

    apkg_path = Path(apkg_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted: dict[str, Path] = {}

    with zipfile.ZipFile(apkg_path, "r") as zf:
        names = set(zf.namelist())

        # Load media map
        media_map: dict[str, str] = {}
        if "media" in names:
            try:
                media_map = json.loads(zf.read("media").decode("utf-8"))
            except Exception:
                pass

        for numeric_name, original_name in media_map.items():
            if numeric_name in names:
                dest = output_dir / original_name
                dest.write_bytes(zf.read(numeric_name))
                extracted[original_name] = dest

    return extracted
