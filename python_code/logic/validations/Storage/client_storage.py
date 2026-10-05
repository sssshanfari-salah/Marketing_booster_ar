import json
import os
from pathlib import Path
import sys
import tempfile
from typing import TYPE_CHECKING, Any, List, Union

if TYPE_CHECKING:
    from logic.clients_management import Client


def _read_client_records(path: Path) -> List[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (TypeError, ValueError, OSError):
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _client_identity(record: dict) -> tuple[str, str]:
    name = str(record.get("name") or record.get("Client Name") or "").strip().lower()
    contact = str(record.get("contact") or record.get("Contact") or "").strip()
    return name, contact


def _write_json_atomically(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def migrate_legacy_client_files(project_root: Union[str, Path]) -> bool:
    from logic.clients_management import resolve_clients_data_path

    root = Path(project_root).resolve()
    canonical_path = resolve_clients_data_path(project_root=root)
    legacy_paths = [
        root / "python_code" / "clients.json",
        Path.cwd() / "clients.json",
    ]
    if sys.executable:
        legacy_paths.append(Path(sys.executable).resolve().parent / "clients.json")

    canonical_records = _read_client_records(canonical_path) if canonical_path.exists() else []
    known_identities = {
        _client_identity(record)
        for record in canonical_records
        if any(_client_identity(record))
    }

    additions = []
    for legacy_path in dict.fromkeys(path.resolve() for path in legacy_paths):
        if legacy_path == canonical_path or not legacy_path.exists():
            continue
        for record in _read_client_records(legacy_path):
            identity = _client_identity(record)
            if not any(identity) or identity in known_identities:
                continue
            additions.append(record)
            known_identities.add(identity)

    if not additions:
        return False

    _write_json_atomically(canonical_path, canonical_records + additions)
    return True


def load_clients_from_file(path: Union[str, Path]) -> List["Client"]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (TypeError, ValueError, OSError):
        return []

    if not isinstance(payload, list):
        return []

    from logic.clients_management import Client

    return [Client.from_dict(item) for item in payload if isinstance(item, dict)]


def save_clients_to_file(path: Union[str, Path], clients: List["Client"]) -> None:
    p = Path(path)
    payload: List[Any] = [client.to_dict() for client in clients]
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
