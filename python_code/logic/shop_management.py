"""
Shop management core architecture skeleton.

Layers:
1. Data Model (ShopNumber)
2. Repository (ShopRepository)
3. Validation (ShopValidator)
4. Directory (DirectoryBuilder)
5. UI Integration (ShopManagementMixin)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Set, Tuple, Optional


# ------------------------------------------------------------
# 1. Data Model Layer
# ------------------------------------------------------------

class ShopNumber:
    """
    Core shop-number rules and normalization.

    - Valid range: 1–37
    - Office is mapped to 37
    - Input can be: str, int, list, tuple, set, dict with known keys
    """

    OFFICE_VALUE = 37
    VALID_MIN = 1
    VALID_MAX = 37

    SHOP_KEYS = (
        "shop_number",
        "shop_number_primary",
        "primary_shop",
        "selected_shop",
        "shop",
    )

    @classmethod
    def normalize(cls, value, *, unique: bool = True) -> List[str]:
        """
        Normalize any input into a list of unique string shop numbers ("1".."37").

        - Handles None, str, int, list, tuple, set, dict
        - Splits strings on [;,| whitespace]
        - Maps 'office' (any case) to '37'
        """
        if value is None:
            return []

        # Collections: recurse
        if isinstance(value, (list, tuple, set)):
            normalized: List[str] = []
            for item in value:
                for part in cls.normalize(item, unique=unique):
                    if not unique or part not in normalized:
                        normalized.append(part)
            return normalized

        # Dict: look for known keys
        if isinstance(value, dict):
            for key in cls.SHOP_KEYS:
                if key in value:
                    return cls.normalize(value[key], unique=unique)
            return []

        # Scalar: str/int/etc.
        text = str(value).strip()
        if not text:
            return []

        parts = re.split(r"[;,|\s]+", text)
        normalized: List[str] = []

        for part in parts:
            candidate = str(part).strip()
            if not candidate:
                continue

            # Office mapping
            if candidate.lower() == "office":
                candidate = str(cls.OFFICE_VALUE)

            if candidate.isdigit():
                if not unique or candidate not in normalized:
                    normalized.append(candidate)

        return normalized

    @classmethod
    def to_int(cls, shop: str) -> int:
        """
        Convert a normalized shop string to int.
        Assumes input is already normalized ("1".."37").
        """
        return int(shop)

    @classmethod
    def is_valid_value(cls, value: int) -> bool:
        """
        Check if an integer shop value is within valid range.
        """
        return cls.VALID_MIN <= value <= cls.VALID_MAX


def normalize_shop_numbers(value) -> List[str]:
    """Normalize shop input using the shared shop-number rules."""
    return ShopNumber.normalize(value)


# ------------------------------------------------------------
# 2. Repository Layer
# ------------------------------------------------------------

class ShopRepository:
    """
    Provides access to used and available shop numbers based on clients.

    Expects each client to have:
    - client.name: str
    - client.shop_number: raw value (str/list/etc.) to be normalized
    """

    def __init__(self, clients: Iterable):
        self.clients = list(clients)

    def get_used_shop_numbers(self, exclude_name: str = "") -> Set[int]:
        """
        Return a set of used shop numbers (as ints), optionally excluding a client by name.
        """
        exclude = (exclude_name or "").strip().lower()
        used: Set[int] = set()

        for client in self.clients:
            if client.name.lower() == exclude:
                continue

            shops = ShopNumber.normalize(client.shop_number)
            for shop in shops:
                value = ShopNumber.to_int(shop)
                if ShopNumber.is_valid_value(value):
                    used.add(value)

        return used

    def get_available_shop_numbers(self, exclude_name: str = "") -> List[str]:
        """
        Return a list of available shop numbers (as strings) from 1 to 37.
        """
        used = self.get_used_shop_numbers(exclude_name)
        return [
            str(number)
            for number in range(ShopNumber.VALID_MIN, ShopNumber.VALID_MAX + 1)
            if number not in used
        ]


# ------------------------------------------------------------
# 3. Validation Layer
# ------------------------------------------------------------

class ShopValidator:
    """
    Validates shop-number input against business rules:

    - Must be numeric or 'Office'
    - Must be within 1–37
    - Must not duplicate within the same input
    - Must not conflict with already used shops (via repository)
    """

    def __init__(self, repository: ShopRepository):
        self.repository = repository

    def validate(
        self,
        shop_input,
        exclude_name: str = "",
    ) -> Tuple[bool, str]:
        """
        Validate a shop input value.

        Returns:
            (True, "") if valid
            (False, "error message") if invalid
        """
        shops = ShopNumber.normalize(shop_input, unique=False)
        if not shops:
            return False, "Please enter valid shop numbers (1–37)."

        used = self.repository.get_used_shop_numbers(exclude_name)
        checked: Set[int] = set()

        for shop in shops:
            shop_str = str(shop).strip()

            # Office mapping (defensive, though normalize already did it)
            if shop_str.lower() == "office":
                value = ShopNumber.OFFICE_VALUE
            elif shop_str.isdigit():
                value = int(shop_str)
            else:
                return False, f"Shop number '{shop_str}' must be numeric or 'Office'."

            if not ShopNumber.is_valid_value(value):
                return False, f"Shop number '{shop_str}' must be between 1 and 37."

            if value in checked:
                return False, f"Shop number '{shop_str}' already exists in the list."
            checked.add(value)

            if value in used:
                remaining = self.repository.get_available_shop_numbers(exclude_name)
                preview = ", ".join(remaining[:12])
                suffix = " ..." if len(remaining) > 12 else ""
                return (
                    False,
                    f"Shop '{shop_str}' is already used. Available: {preview}{suffix}",
                )

        return True, ""


# ------------------------------------------------------------
# 4. Directory Layer
# ------------------------------------------------------------

class DirectoryBuilder:
    """
    Responsible only for building client directory paths and names.

    Expects:
    - base_path: Path
    - client.name: str
    - client.shop_number: raw value
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path

    @staticmethod
    def _safe_name(name: str) -> str:
        """
        Sanitize client name for filesystem use.
        """
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
        return safe or "Client"

    def create_client_directory(self, client) -> Path:
        """
        Create and return the directory path for a client.
        """
        root = self.base_path / "Clients"
        root.mkdir(parents=True, exist_ok=True)

        safe_name = self._safe_name(client.name)
        shops = ShopNumber.normalize(client.shop_number)

        if shops:
            folder_name = f"{safe_name}_{'_'.join(shops)}"
        else:
            folder_name = safe_name

        folder_path = root / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path


# ------------------------------------------------------------
# 5. UI / Form Integration Layer (Mixin)
# ------------------------------------------------------------

class ShopManagementMixin:
    """
    Mixin to integrate shop management into a UI class (e.g., Tkinter form).

    Expects the host class to provide:
    - self.clients: list of client objects
    - self.file_path: Path (base file path)
    - self.shop_entry: widget or method to get shop input (e.g., self.shop_entry.get())
    """

    def get_shop_repository(self) -> ShopRepository:
        return ShopRepository(self.clients)

    def get_shop_validator(self) -> ShopValidator:
        return ShopValidator(self.get_shop_repository())

    def get_directory_builder(self) -> DirectoryBuilder:
        return DirectoryBuilder(self.file_path.parent)

    def get_used_shop_numbers(self, exclude_name: str = "") -> Set[int]:
        return self.get_shop_repository().get_used_shop_numbers(exclude_name)

    def get_available_shop_numbers(self, exclude_name: str = "") -> List[str]:
        return self.get_shop_repository().get_available_shop_numbers(exclude_name)

    def validate_shop_number(self, shop_input, exclude_name: str = "") -> Tuple[bool, str]:
        return self.get_shop_validator().validate(shop_input, exclude_name)

    def create_client_directory(self, client) -> Path:
        return self.get_directory_builder().create_client_directory(client)
