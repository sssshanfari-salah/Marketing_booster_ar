from typing import Dict, List


PAYMENT_METHOD_CHOICES = ("Cash", "Cheque", "Bank Transaction")


def normalize_payment_method(value: str) -> str:
    if value is None:
        return "Cash"

    normalized = str(value).strip()
    if not normalized:
        return "Cash"

    lookup = {choice.lower(): choice for choice in PAYMENT_METHOD_CHOICES}
    if normalized.lower() in lookup:
        return lookup[normalized.lower()]

    for choice in PAYMENT_METHOD_CHOICES:
        if normalized.lower() in choice.lower():
            return choice

    return "Cash"


def is_payment_completed(entry: Dict[str, str]) -> bool:
    status = str(entry.get("status", "") or "").strip().lower()
    return status in {"paid", "completed", "complete", "success", "successful", "yes", "true", "1"}


def can_complete_payment(
    entry: Dict[str, str],
    month_options: List[str],
    client_transactions: List[Dict[str, str]],
) -> bool:
    from logic.months import get_month_index, get_previous_month

    if not entry:
        return False

    month = str(entry.get("month", "") or "").strip()
    amount = str(entry.get("amount", "") or "").strip()
    payment_method = normalize_payment_method(entry.get("payment_method", "Cash"))
    due_date = str(entry.get("due_date", "") or "").strip()
    cheque_number = str(entry.get("cheque_number", "") or "").strip()
    bank_detail = str(entry.get("bank_transaction_details", "") or "").strip()

    if not month or not amount or not due_date:
        return False

    if payment_method == "Cheque":
        if not cheque_number:
            return False
        return bool(cheque_number)
    elif payment_method == "Bank Transaction":
        if not bank_detail:
            return False
        return bool(bank_detail)

    current_index = get_month_index(month, month_options)
    if current_index <= 0:
        return True

    previous_month = get_previous_month(month, month_options)
    if not previous_month:
        return True

    for candidate in client_transactions:
        if str(candidate.get("month", "") or "").strip() != previous_month:
            continue
        if not is_payment_completed(candidate):
            return False
        break
    else:
        return False

    return True
