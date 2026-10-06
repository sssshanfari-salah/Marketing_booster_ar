from typing import Dict, Any


def normalize_reservation_status(value: Any) -> Dict[str, str]:
    from logic.clients_management import normalize_duration_value

    reservation_fields = {
        "client_name": "",
        "contact": "",
        "shop_number": "",
        "deposit_status": "",
        "contract_status": "",
        "contract_duration": "",
        "rent_value": "",
        "deposit_amount": "",
        "last_updated": "",
    }

    if not isinstance(value, dict):
        return dict(reservation_fields)

    normalized: Dict[str, str] = {}
    for key, default in reservation_fields.items():
        raw_value = value.get(key, default)
        if raw_value is None:
            raw_value = default
        if key == "contract_duration":
            normalized[key] = normalize_duration_value(raw_value)
        else:
            normalized[key] = str(raw_value)
    return normalized
