from typing import Any, List

from logic.shops_conversion_to_dic import format_shop_display_label
from logic.validations.Storage.client_storage import load_clients_from_file


def build_client_payment_report_text(client_name: str, manager: Any) -> str:
    if manager is None:
        return "Client Payment Report\n\nNo manager available."

    if hasattr(manager, "load_clients"):
        manager.load_clients()
        clients = getattr(manager, "clients", [])
    else:
        clients = load_clients_from_file(manager)

    target_name = str(client_name or "").strip()
    client = None
    for candidate in clients:
        if getattr(candidate, "name", "").lower() == target_name.lower():
            client = candidate
            break

    if client is None:
        return f"Client Payment Report\n\nNo client named '{target_name}' was found."

    contract_details = getattr(client, "contract_details", {}) or {}
    if not isinstance(contract_details, dict):
        contract_details = {}

    transactions: List[Any] = getattr(client, "transactions", []) or []
    if not isinstance(transactions, list):
        transactions = []

    nl = "\n"
    shop_labels = [format_shop_display_label(shop) for shop in getattr(client, "shop_number", []) or []]
    shop_text = ", ".join(shop_labels) if shop_labels else "N/A"

    lines = [
        "Client Payment Report",
        "====================",
        "",
        f"Client Name: {client.name}",
        f"Contact: {client.contact or 'N/A'}",
        f"Business: {client.business or 'N/A'}",
        f"Email: {client.email or 'N/A'}",
        f"Shop Number(s): {shop_text}",
        f"Contract Number: {contract_details.get('contract_number') or 'N/A'}",
        f"Contract Period: {contract_details.get('starting_date') or 'N/A'} to {contract_details.get('ending_date') or 'N/A'}",
        f"Rent Value: {contract_details.get('rent_value') or 'N/A'}",
        f"Currency Type: {contract_details.get('currency_type') or 'OMR'}",
        "",
        "Transactions:",
    ]

    if not transactions:
        lines.append("- No transaction history recorded.")
    else:
        for entry in transactions:
            if not isinstance(entry, dict):
                continue
            month = str(entry.get("month") or "").strip() or "Unknown month"
            status = str(entry.get("status") or "").strip() or "Pending"
            amount = str(entry.get("amount") or "").strip() or "0"
            method = str(entry.get("payment_method") or "").strip() or "Cash"
            due_date = str(entry.get("due_date") or "").strip()
            details = str(entry.get("bank_transaction_details") or entry.get("bank_detail") or "").strip()
            cheque_number = str(entry.get("cheque_number") or "").strip()
            line = f"- {month}: {status} | {amount} | {method}"
            if cheque_number:
                line += f" | Cheque: {cheque_number}"
            if details:
                line += f" | Details: {details}"
            if due_date:
                line += f" | Due: {due_date}"
            lines.append(line)

    return nl.join(lines) + nl
