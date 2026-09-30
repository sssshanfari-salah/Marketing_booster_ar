import json
from pathlib import Path

# Minimal emergency fallback for the shop-to-electric-meter mapping.
# The durable source of truth remains the JSON file in this folder, which is
# persisted across app restarts and can be extended with future shop additions.
DEFAULT_SHOP_METER_MAP = {
    "Office": "28609686",
}

DATA_PATH = Path(__file__).resolve().parent / "Shops_Elect_meters.json"


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


shop_meter_map = _load_shop_meter_map()

def validate_shop(shop, selected):
    shop = shop.strip()

    if not shop.isdigit():
        return False, "Shop must be numeric."

    if not (1 <= int(shop) <= 36):
        return False, "Shop must be between 1 and 36."

    if shop in {entry["Shop"] for entry in selected}:
        return False, "Shop already selected."

    return True, ""

def get_meter(shop, mapping):
    return mapping.get(shop, "")


