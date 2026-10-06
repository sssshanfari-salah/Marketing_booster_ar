from typing import List, Dict, Any

from logic.models.transactions import Transaction, normalize_transaction_entry
from logic.months import generate_contract_months, coerce_due_date_for_month
from logic.validations.payment_rules import (
    normalize_payment_method,
    is_payment_completed,
    can_complete_payment,
)


class FinanceManager:
    def __init__(self, client):
        self.client = client
        self._ensure_transactions_list()

    def _ensure_transactions_list(self) -> None:
        if not hasattr(self.client, "transactions") or not isinstance(self.client.transactions, list):
            self.client.transactions = []

    @property
    def transactions(self) -> List[Dict[str, str]]:
        return list(getattr(self.client, "transactions", []) or [])

    def get_month_options(self) -> List[str]:
        contract_details = getattr(self.client, "contract_details", {}) or {}
        start_date = str(contract_details.get("starting_date") or "").strip()
        end_date = str(contract_details.get("ending_date") or "").strip()
        months = generate_contract_months(start_date, end_date)
        return months or []

    def normalize_all_transactions(self) -> List[Transaction]:
        return [Transaction.from_dict(entry) for entry in self.transactions]

    def add_transaction_for_month(self, month_value: str) -> Transaction:
        entry = normalize_transaction_entry({})
        entry["month"] = month_value
        entry["status"] = "Pending"
        entry["payment_method"] = "Cash"
        self.client.transactions.append(entry)
        return Transaction.from_dict(entry)

    def update_month(self, entry: Dict[str, str], new_month: str) -> None:
        entry["month"] = str(new_month or "").strip()
        self.update_due_date(entry, entry.get("due_date", ""))

    def update_due_date(self, entry: Dict[str, str], due_date: str) -> str:
        entry["due_date"] = coerce_due_date_for_month(entry.get("month", ""), due_date)
        return entry["due_date"]

    def update_payment_method(self, entry: Dict[str, str], new_method: str) -> None:
        entry["payment_method"] = normalize_payment_method(new_method)
        if entry["payment_method"] != "Cheque":
            entry["cheque_number"] = ""
        if entry["payment_method"] != "Bank Transaction":
            entry["bank_transaction_details"] = ""

    def mark_status(self, entry: Dict[str, str], completed: bool) -> bool:
        month_options = self.get_month_options()
        if not completed:
            entry["status"] = "Pending"
            return False

        if not can_complete_payment(entry, month_options, self.transactions):
            entry["status"] = "Pending"
            return False

        entry["status"] = "Paid"
        return True

    def is_completed(self, entry: Dict[str, str]) -> bool:
        return is_payment_completed(entry)
