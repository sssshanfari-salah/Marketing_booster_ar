import calendar
from datetime import datetime
from typing import List, Optional


def generate_contract_months(start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[str]:
    start_value = str(start_date or "").strip()
    end_value = str(end_date or "").strip()
    if not start_value and not end_value:
        return []

    def parse_date(value: str) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    start_dt = parse_date(start_value)
    end_dt = parse_date(end_value)
    if start_dt is None and end_dt is not None:
        start_dt = end_dt.replace(day=1)
    if end_dt is None and start_dt is not None:
        end_dt = start_dt.replace(day=28)
    if start_dt is None or end_dt is None:
        return []
    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt

    months = []
    current = start_dt.replace(day=1)
    while current <= end_dt:
        months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    seen = set()
    unique_months = []
    for month in months:
        if month in seen:
            continue
        seen.add(month)
        unique_months.append(month)
    return unique_months


def get_month_index(month_value: str, month_options: List[str]) -> int:
    if not month_value or not month_options:
        return -1
    try:
        return month_options.index(month_value)
    except ValueError:
        return -1


def get_previous_month(month_value: str, month_options: List[str]) -> str:
    idx = get_month_index(month_value, month_options)
    if idx <= 0:
        return ""
    return month_options[idx - 1]


def coerce_due_date_for_month(month_value: str, due_date_value: str) -> str:
    month_text = str(month_value or "").strip()
    if not month_text:
        return str(due_date_value or "").strip()

    try:
        month_start = datetime.strptime(f"{month_text}-01", "%Y-%m-%d")
    except ValueError:
        return str(due_date_value or "").strip()

    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    month_end = datetime(month_start.year, month_start.month, last_day).strftime("%d-%m-%Y")

    value = str(due_date_value or "").strip()
    if not value:
        return month_end

    try:
        parsed = datetime.strptime(value, "%d-%m-%Y")
    except ValueError:
        try:
            parsed = datetime.fromisoformat(value)
            parsed = parsed if parsed else datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return month_end

    if parsed.year == month_start.year and parsed.month == month_start.month:
        return parsed.strftime("%d-%m-%Y")
    return month_end
