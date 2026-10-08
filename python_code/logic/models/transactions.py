import calendar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class Transaction:
    month: str = ""
    status: str = ""
    amount: str = ""
    payment_method: str = "Cash"
    cheque_number: str = ""
    due_date: str = ""
    bank_name: str = ""
    bank_transaction_details: str = ""

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "Transaction":
        normalized = normalize_transaction_entry(value)
        return cls(**normalized)

    def to_dict(self) -> Dict[str, str]:
        return {
            "month": self.month,
            "status": self.status,
            "amount": self.amount,
            "payment_method": self.payment_method,
            "cheque_number": self.cheque_number,
            "due_date": self.due_date,
            "bank_name": self.bank_name,
            "bank_transaction_details": self.bank_transaction_details,
        }


def normalize_transaction_entry(value: Any) -> Dict[str, str]:
    transaction_fields = {
        "month": "",
        "status": "",
        "amount": "",
        "payment_method": "",
        "cheque_number": "",
        "due_date": "",
        "bank_name": "",
        "bank_transaction_details": "",
    }

    if not isinstance(value, dict):
        return dict(transaction_fields)

    normalized: Dict[str, str] = {}
    for key, default in transaction_fields.items():
        raw_value = value.get(key, default)
        if raw_value is None:
            raw_value = default
        normalized[key] = str(raw_value)
    return normalized
