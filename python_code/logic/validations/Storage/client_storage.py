import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Union

if TYPE_CHECKING:
    from logic.clients_management import Client


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
