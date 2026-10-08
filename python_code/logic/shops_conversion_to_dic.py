import json
from pathlib import Path

try:
    from python_code.project_paths import ensure_source_on_path
except ImportError:  # pragma: no cover - direct script fallback
    from project_paths import ensure_source_on_path

ensure_source_on_path()

# Minimal emergency fallback for the shop-to-electric-meter mapping.
# The durable source of truth remains the JSON file in the project config folder,
# which is persisted across app restarts and can be extended with future shop
# additions.
DEFAULT_SHOP_METER_MAP = {
    "Office": "28609686",
    "37": "28609686",
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "config" / "Shops_Elect_meters.json",
    PROJECT_ROOT / "python_code" / "config" / "Shops_Elect_meters.json",
    Path(__file__).resolve().parent / "Shops_Elect_meters.json",
]
DATA_PATH = next((path for path in DATA_CANDIDATES if path.exists()), DATA_CANDIDATES[0])


def _load_authoritative_selected_shops():
    try:
        from python_code.logic.clients_management import ClientManager, resolve_clients_data_path
    except ImportError:
        return []

    file_path = resolve_clients_data_path()
    manager = ClientManager(file_path)
    manager.load_clients()
    selected = []
    for client in manager.clients:
        shop_number = str(getattr(client, "shop_number", "") or "").strip()
        if not shop_number:
            continue
        selected.append({
            "Shop": shop_number,
            "Elec meter": str(getattr(client, "electrical_meter", "") or getattr(client, "notes", "") or ""),
        })
    return selected


def _load_shop_meter_map():
    mapping = dict(DEFAULT_SHOP_METER_MAP)
    if not DATA_PATH.exists():
        return mapping

    try:
        with DATA_PATH.open("r", encoding="utf-8") as infile:
            shop_rows = json.load(infile)
    except (json.JSONDecodeError, OSError, TypeError):
        return mapping

    if not isinstance(shop_rows, list):
        return mapping

    for entry in shop_rows:
        if not isinstance(entry, dict):
            continue
        shop_key = str(entry.get("Shop") or entry.get("shop") or "").strip()
        meter_value = str(entry.get("Elec meter") or entry.get("Elec Meter") or "").strip()
        if shop_key and meter_value:
            mapping[shop_key] = meter_value

    return mapping


def format_shop_display_label(shop_number):
    shop_value = str(shop_number or "").strip()
    if not shop_value:
        return ""
    if shop_value.lower() == "office" or shop_value == "37":
        return "Office (37)"
    return shop_value


def resolve_shop_electrical_meter(shop_number, mapping=None):
    shop_value = str(shop_number or "").strip()
    if not shop_value:
        return ""
    lookup = mapping if mapping is not None else shop_meter_map
    if shop_value.lower() == "office":
        return str(lookup.get("Office", lookup.get("37", ""))).strip()
    if shop_value == "37":
        return str(lookup.get("37", lookup.get("Office", ""))).strip()
    return str(lookup.get(shop_value, "")).strip()


shop_meter_map = _load_shop_meter_map()


def validate_shop(shop, selected=None):
    shop = str(shop or "").strip()

    if not shop:
        return False, "Please enter a shop number between 1 and 37."

    if shop.lower() == "office":
        value = 37
    elif shop.isdigit():
        value = int(shop)
    else:
        return False, "Shop must be numeric or 'Office'."

    if not (1 <= value <= 37):
        return False, "Shop must be between 1 and 37."

    authoritative_selected = _load_authoritative_selected_shops()
    if authoritative_selected:
        selected = authoritative_selected
    elif selected is None:
        selected = []

    def normalize_selected_value(entry_value):
        raw = str(entry_value or "").strip()
        if not raw:
            return ""
        if raw.lower() == "office":
            return "37"
        return raw

    chosen = {
        normalize_selected_value(entry.get("Shop") or entry.get("shop") or "")
        for entry in selected or []
        if isinstance(entry, dict)
    }
    if str(value) in chosen:
        return False, "Shop already selected."

    return True, ""

def get_meter(shop, mapping):
    return mapping.get(shop, "")


