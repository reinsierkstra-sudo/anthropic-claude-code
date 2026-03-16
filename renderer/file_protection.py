"""
renderer/file_protection.py
----------------------------
Standalone file-integrity helpers extracted from the
IsotopeDashboardGenerator class in gallium_extractor.py.

All functions are pure (no class state), operating only on the
filesystem paths passed as arguments.
"""

import hashlib
import os
import stat


def calculate_file_hash(filepath):
    """Calculate the SHA-256 hex digest of *filepath*.

    Returns the hex string on success, or ``None`` if the file cannot
    be read (e.g. it does not exist or is locked).
    """
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (IOError, OSError) as e:
        print(f"[WARNING] Hash calculation failed for {filepath!r}: {e}")
        return None


def set_readonly(filepath):
    """Remove write permissions for owner, group, and others on *filepath*.

    Returns ``True`` on success, ``False`` if the operation fails (e.g.
    the file does not exist or the process lacks privileges).
    """
    try:
        current_permissions = os.stat(filepath).st_mode
        os.chmod(
            filepath,
            current_permissions & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH,
        )
        return True
    except Exception as e:
        print(f"[WARNING] Could not set read-only on {filepath!r}: {e}")
        return False


def remove_readonly(filepath):
    """Re-add owner-write permission on *filepath* so it can be overwritten.

    Returns ``True`` on success, ``False`` on failure.
    """
    try:
        current_permissions = os.stat(filepath).st_mode
        os.chmod(filepath, current_permissions | stat.S_IWUSR)
        return True
    except Exception:
        return False


def check_file_integrity(html_path, hash_path):
    """Verify that *html_path* has not been modified since the last hash save.

    Returns a ``(ok: bool, message: str | None)`` tuple:
    - ``(True, None)``  — file is clean (or does not exist yet / no hash saved).
    - ``(False, msg)``  — file contents differ from the stored hash.
    """
    if not os.path.exists(html_path):
        return True, None  # File doesn't exist — no tampering possible.
    if not os.path.exists(hash_path):
        return True, None  # No hash file — first run.

    try:
        with open(hash_path, 'r') as f:
            stored_hash = f.read().strip()

        current_hash = calculate_file_hash(html_path)
        if current_hash != stored_hash:
            return False, "[WARNING] FILE TAMPERED: HTML file has been manually modified!"

        return True, None
    except Exception as e:
        return True, f"Warning: Could not verify file integrity: {e}"


def save_file_hash(html_path, hash_path):
    """Compute and persist the SHA-256 hash of *html_path* to *hash_path*.

    Returns ``True`` on success, ``False`` on failure (warning is printed).
    """
    try:
        file_hash = calculate_file_hash(html_path)
        with open(hash_path, 'w') as f:
            f.write(file_hash)
        return True
    except Exception as e:
        print(f"[WARNING] Could not save file hash for {html_path!r}: {e}")
        return False
