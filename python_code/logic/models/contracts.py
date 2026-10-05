from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ContractDetails:
    contract_number: str = ""
    starting_date: str = ""
    ending_date: str = ""
    commercial_registration_number: str = ""
    authorized_signature_name: str = ""
    rent_value: str = ""
    currency_type: str = "OMR"
    open_issues: str = ""
    duration_years: str = ""
    renewable: str = ""
    first_party: str = ""
    second_party: str = ""


def normalize_contract_details(value: Any) -> Dict[str, str]:
    from logic.clients_management import normalize_duration_value, normalize_renewable_value

    contract_fields = {
        "contract_number": "",
        "starting_date": "",
        "ending_date": "",
        "commercial_registration_number": "",
        "authorized_signature_name": "",
        "rent_value": "",
        "currency_type": "OMR",
        "open_issues": "",
        "duration_years": "",
        "renewable": "",
        "first_party": "",
        "second_party": "",
    }

    if not isinstance(value, dict):
        return dict(contract_fields)

    normalized: Dict[str, str] = {}
    for key, default in contract_fields.items():
        raw_value = value.get(key, default)
        if raw_value is None:
            raw_value = default
        if key == "duration_years":
            normalized[key] = normalize_duration_value(raw_value)
        elif key == "renewable":
            normalized[key] = normalize_renewable_value(raw_value)
        else:
            normalized[key] = str(raw_value)
    return normalized
