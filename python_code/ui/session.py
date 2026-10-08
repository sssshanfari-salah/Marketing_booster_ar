"""Shared session, user-profile, and guest-profile logic for the app UI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from config.language_compat import T, refresh_translatable_widgets

APP_ROOT = Path(__file__).resolve().parents[2]
USERS_FILE = APP_ROOT / "users.json"
GUESTS_FILE = APP_ROOT / "guests.json"
LEGACY_USER_PROFILE_FILE = APP_ROOT / "user_profile.json"
CURRENT_SESSION_PROFILE = {"name": "", "email": ""}


def _normalize_session_profile(profile):
    if not isinstance(profile, dict):
        profile = {}

    name = str(profile.get("name") or profile.get("user_name") or "").strip()
    email = str(profile.get("email") or profile.get("email_account") or "").strip()

    if not name and not email:
        return {"name": "", "email": ""}

    normalized_name = name.lower()
    normalized_email = email.lower()
    if normalized_name == "guest" or normalized_email == "guest":
        return {"name": "Guest", "email": "Guest"}

    return {"name": name, "email": email}


def _read_json_file(file_path):
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        return None


def _write_json_file(file_path, payload):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as outfile:
        json.dump(payload, outfile, ensure_ascii=False, indent=2)
        outfile.flush()
        os.fsync(outfile.fileno())
    os.replace(temp_path, file_path)


def _normalize_user_record(payload):
    if not isinstance(payload, dict):
        return {"name": "", "email": ""}
    return {
        "name": str(payload.get("name") or payload.get("user_name") or payload.get("user") or "").strip(),
        "email": str(payload.get("email") or payload.get("email_account") or "").strip(),
    }


def load_registered_users():
    payload = _read_json_file(USERS_FILE)

    if isinstance(payload, dict):
        users = payload.get("users") if isinstance(payload.get("users"), list) else payload.get("registered_users")
        if isinstance(users, list):
            return [_normalize_user_record(item) for item in users if isinstance(item, dict)]
        single_user = _normalize_user_record(payload)
        if single_user["name"] or single_user["email"]:
            return [single_user]
        return []

    if isinstance(payload, list):
        return [_normalize_user_record(item) for item in payload if isinstance(item, dict)]

    return []


def verify_registered_user(user_name, email_account):
    name = str(user_name or "").strip()
    email = str(email_account or "").strip().lower()
    if not name or not email:
        return False

    normalized_name = name.lower()
    for user in load_registered_users():
        user_name_value = str(user.get("name", "") or "").strip().lower()
        user_email_value = str(user.get("email", "") or "").strip().lower()
        if user_name_value == normalized_name and user_email_value == email:
            return True
    return False


def get_registered_user_name(user_name, email_account):
    """Return the user name exactly as saved in the registered users list.

    Falls back to the provided ``user_name`` (stripped) when no matching
    registered user is found, so the login status always shows the
    authoritative saved spelling/casing for a verified login.
    """
    name = str(user_name or "").strip()
    email = str(email_account or "").strip().lower()
    if not name or not email:
        return name

    normalized_name = name.lower()
    for user in load_registered_users():
        user_name_value = str(user.get("name", "") or "").strip()
        user_email_value = str(user.get("email", "") or "").strip().lower()
        if user_name_value.lower() == normalized_name and user_email_value == email:
            return user_name_value or name
    return name


def is_admin_registration_allowed(user_name, email_account):
    name = str(user_name or "").strip().lower()
    email = str(email_account or "").strip().lower()
    return name == "admin" and email == "admin"


def is_registration_submission_allowed(user_name, email_account):
    name = str(user_name or "").strip()
    email = str(email_account or "").strip()
    if not name or not email:
        return False
    return True


def load_user_profile():
    for file_path in (USERS_FILE, LEGACY_USER_PROFILE_FILE):
        payload = _read_json_file(file_path)
        if payload is None:
            continue

        if isinstance(payload, dict):
            if isinstance(payload.get("users"), list):
                for item in payload["users"]:
                    if isinstance(item, dict):
                        profile = _normalize_user_record(item)
                        if profile["name"] or profile["email"]:
                            return profile
            profile = _normalize_user_record(payload)
            if profile["name"] or profile["email"]:
                return profile

        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    profile = _normalize_user_record(item)
                    if profile["name"] or profile["email"]:
                        return profile

    return {"name": "", "email": ""}


def user_registeration(user_name, email_account):
    profile = {
        "name": str(user_name or "").strip(),
        "email": str(email_account or "").strip(),
    }

    if not is_registration_submission_allowed(profile["name"], profile["email"]):
        return {"name": "", "email": ""}

    users = load_registered_users()
    if profile["name"] or profile["email"]:
        existing_index = next(
            (
                index
                for index, item in enumerate(users)
                if item.get("name", "").strip().lower() == profile["name"].lower()
                and item.get("email", "").strip().lower() == profile["email"].lower()
            ),
            None,
        )
        if existing_index is not None:
            users[existing_index] = profile
        else:
            users.append(profile)

    _write_json_file(USERS_FILE, {"users": users})
    return profile


def user_registration(user_name, email_account):
    return user_registeration(user_name, email_account)


def save_user_profile(name, email):
    return user_registeration(name, email)


def _normalize_guest_record(payload):
    if not isinstance(payload, dict):
        return {"name": "", "email": ""}
    return {
        "name": str(payload.get("name") or payload.get("guest_name") or "").strip(),
        "email": str(payload.get("email") or payload.get("guest_email") or "").strip(),
    }


def load_guest_profiles():
    payload = _read_json_file(GUESTS_FILE)

    if isinstance(payload, dict):
        guests = payload.get("guests") if isinstance(payload.get("guests"), list) else []
        if isinstance(guests, list):
            return [_normalize_guest_record(item) for item in guests if isinstance(item, dict)]
        single_guest = _normalize_guest_record(payload)
        if single_guest["name"] or single_guest["email"]:
            return [single_guest]
        return []

    if isinstance(payload, list):
        return [_normalize_guest_record(item) for item in payload if isinstance(item, dict)]

    return []


def save_guest_profile(name, email):
    profile = {
        "name": str(name or "").strip() or "Guest",
        "email": str(email or "").strip() or "Guest",
    }
    guests = load_guest_profiles()

    existing_index = next(
        (
            index
            for index, item in enumerate(guests)
            if item.get("name", "").strip().lower() == profile["name"].lower()
            and item.get("email", "").strip().lower() == profile["email"].lower()
        ),
        None,
    )
    if existing_index is not None:
        guests[existing_index] = profile
    else:
        guests.append(profile)

    _write_json_file(GUESTS_FILE, {"guests": guests})
    return profile


def is_guest_profile(profile=None):
    if profile is None:
        profile = CURRENT_SESSION_PROFILE

    normalized = _normalize_session_profile(profile)
    user_name = str(normalized.get("name") or "").strip().lower()
    user_email = str(normalized.get("email") or "").strip().lower()
    return user_name == "guest" and user_email == "guest"


def is_guest_login_credentials(user_name, email_account):
    name = str(user_name or "").strip().lower()
    email = str(email_account or "").strip().lower()
    return name == "guest" and email == "guest"


def sync_session_profile(profile=None, user_name=None, user_email=None, *, clear=False):
    if clear:
        CURRENT_SESSION_PROFILE["name"] = ""
        CURRENT_SESSION_PROFILE["email"] = ""
        return CURRENT_SESSION_PROFILE

    if isinstance(profile, dict):
        normalized = _normalize_session_profile(profile)
        CURRENT_SESSION_PROFILE["name"] = normalized["name"]
        CURRENT_SESSION_PROFILE["email"] = normalized["email"]
        return CURRENT_SESSION_PROFILE

    if isinstance(profile, str):
        if user_name is not None and user_email is None:
            user_email = user_name
        user_name = profile
        user_email = user_email or ""

    normalized = _normalize_session_profile({"name": user_name, "email": user_email})
    CURRENT_SESSION_PROFILE["name"] = normalized["name"]
    CURRENT_SESSION_PROFILE["email"] = normalized["email"]
    return CURRENT_SESSION_PROFILE


def ensure_default_guest_session():
    normalized = _normalize_session_profile(CURRENT_SESSION_PROFILE)
    if not normalized["name"] and not normalized["email"]:
        sync_session_profile(user_name="Guest", user_email="Guest")
    elif normalized["name"].lower() == "guest" or normalized["email"].lower() == "guest":
        sync_session_profile(user_name="Guest", user_email="Guest")
    return CURRENT_SESSION_PROFILE


def set_current_session_profile(profile=None, user_name=None, user_email=None):
    return sync_session_profile(profile=profile, user_name=user_name, user_email=user_email)


def is_registered_user_profile(profile=None):
    if profile is None:
        profile = CURRENT_SESSION_PROFILE

    normalized = _normalize_session_profile(profile)
    user_name = str(normalized.get("name") or "").strip()
    user_email = str(normalized.get("email") or "").strip()
    if not user_name or not user_email:
        return False
    if user_name.lower() == "guest" or user_email.lower() == "guest":
        return False
    return verify_registered_user(user_name, user_email)


def build_report_issuer_footer():
    profile = CURRENT_SESSION_PROFILE.copy()
    if not profile.get("name") and not profile.get("email"):
        profile = load_user_profile()
    if not is_registered_user_profile(profile):
        user_name = "Guest"
    else:
        user_name = profile.get("name") or "System"
    return T("Report issued by: {user_name}", user_name=user_name)


def append_report_footer(lines):
    footer = build_report_issuer_footer()
    content = [str(item) for item in lines]
    if not content:
        return [footer]
    if content[-1].strip() == footer:
        return content
    return content + ["", footer]


__all__ = [
    "APP_ROOT",
    "CURRENT_SESSION_PROFILE",
    "GUESTS_FILE",
    "LEGACY_USER_PROFILE_FILE",
    "USERS_FILE",
    "_normalize_guest_record",
    "_normalize_user_record",
    "_read_json_file",
    "_write_json_file",
    "ensure_default_guest_session",
    "get_registered_user_name",
    "is_admin_registration_allowed",
    "is_guest_login_credentials",
    "is_guest_profile",
    "is_registered_user_profile",
    "is_registration_submission_allowed",
    "load_guest_profiles",
    "load_registered_users",
    "load_user_profile",
    "save_guest_profile",
    "save_user_profile",
    "set_current_session_profile",
    "sync_session_profile",
    "user_registeration",
    "user_registration",
    "verify_registered_user",
]
