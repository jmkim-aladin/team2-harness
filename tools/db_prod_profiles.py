"""Strict production profile snapshots; secrets only cross private pipes.

The user chose the current macOS account and its existing login keychain.
Loading a profile performs no SQL Server network operation.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

TARGETS = frozenset(("lego-prod", "cool-prod"))


class ProfileError(Exception):
    pass


def unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ProfileError("duplicate_profile_field")
        result[key] = value
    return result


def parse_profile(raw):
    try:
        profile = json.loads(raw, object_pairs_hook=unique_pairs)
    except Exception:
        raise ProfileError("invalid_profile_json") from None
    if not isinstance(profile, dict) or set(profile) != {"host", "port", "account"}:
        raise ProfileError("invalid_profile_fields")
    host, port, account = (profile[k] for k in ("host", "port", "account"))
    if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9_.:\-]+", host):
        raise ProfileError("invalid_profile_host")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ProfileError("invalid_profile_port")
    if not isinstance(account, str) or not account.strip() or any(ord(c) < 32 for c in account):
        raise ProfileError("invalid_profile_account")
    return profile


def profile_digest(profile):
    return hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class LocalKeychain:
    def __init__(self, state_dir, helper):
        self.state_dir = Path(state_dir)
        self.helper = str(helper)

    def _get(self, service, account):
        try:
            request = dict(mode="read-login", path=str(Path.home() / "Library/Keychains/login.keychain-db"),
                           service=service, account=account)
            result = subprocess.run([self.helper], input=json.dumps(request).encode(),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
                                    env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home())})
            if result.returncode:
                try:
                    code = json.loads(result.stdout).get("error")
                except Exception:
                    code = None
                if code in {"keychain_interaction_required", "keychain_access_cancelled",
                            "keychain_item_not_found", "keychain_path_invalid", "keychain_value_invalid",
                            "keychain_status_-25293"}:
                    raise ProfileError(code)
                raise ProfileError("service_keychain_unavailable")
            response = json.loads(result.stdout)
            value = response["value"]
            if not isinstance(value, str) or not value:
                raise ProfileError("empty_service_credential")
            return value
        except ProfileError:
            raise
        except Exception:
            raise ProfileError("service_keychain_unavailable") from None

    def profile(self, target, *, observer=False):
        if target not in TARGETS:
            raise ProfileError("unknown_target")
        service = target + ("-observer" if observer else "")
        return parse_profile(self._get(service + "-profile", "profile"))

    def credentials(self, target, expected, *, observer=False):
        profile = self.profile(target, observer=observer)
        if profile_digest(profile) != profile_digest(expected):
            raise ProfileError("profile_changed_new_approval_required")
        service = target + ("-observer" if observer else "")
        # Only the admitted backend calls this password path.
        return dict(profile, password=self._get(service, profile["account"]))
