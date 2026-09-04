from __future__ import annotations

import hashlib
import time
from pathlib import Path

SOURCE = Path(r"C:\Users\ssssh\Documents\Document Manager\documents.txt")
TARGET = Path(r"C:\Users\ssssh\OneDrive\Documents\Marketing booster\python code\docs\documents.txt")


def sync_once() -> bool:
    if not SOURCE.exists():
        print(f"Source file not found: {SOURCE}")
        return False

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    source_bytes = SOURCE.read_bytes()
    if TARGET.exists() and TARGET.read_bytes() == source_bytes:
        return True

    TARGET.write_bytes(source_bytes)
    print(f"Synced: {SOURCE} -> {TARGET}")
    return True


def main() -> None:
    print(f"Watching for changes...\nSource: {SOURCE}\nTarget: {TARGET}")
    last_hash = None

    while True:
        if SOURCE.exists():
            source_bytes = SOURCE.read_bytes()
            current_hash = hashlib.sha256(source_bytes).hexdigest()
            if last_hash is None or current_hash != last_hash:
                last_hash = current_hash
                sync_once()
        time.sleep(2)


if __name__ == "__main__":
    sync_once()
    main()
