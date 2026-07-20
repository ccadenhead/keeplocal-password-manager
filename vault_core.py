# Copyright (c) 2026 Charles Cadenhead
# All rights reserved.

import base64
import json
import os
import secrets
import shutil
import string
import subprocess
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


APP_NAME = "LocalPasswordManager"
SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
APP_DATA_FOLDER = os.path.join(
    os.environ.get("LOCALAPPDATA", SCRIPT_FOLDER),
    APP_NAME,
)
SALT_FILE = os.path.join(APP_DATA_FOLDER, "vault_salt.bin")
VERIFY_FILE = os.path.join(APP_DATA_FOLDER, "vault_verify.token")
VAULT_FILE = os.path.join(APP_DATA_FOLDER, "password_vault.jsonl")
BACKUP_FOLDER = os.path.join(APP_DATA_FOLDER, "vault_backups")
VAULT_FILES = (
    ("vault_salt.bin", SALT_FILE),
    ("vault_verify.token", VERIFY_FILE),
    ("password_vault.jsonl", VAULT_FILE),
)
KDF_ITERATIONS = 600_000


def old_local_path(file_name):
    return os.path.join(SCRIPT_FOLDER, file_name)


def setup_app_data_folder():
    os.makedirs(APP_DATA_FOLDER, exist_ok=True)


def migrate_legacy_vault_files():
    for old_file_name, new_path in VAULT_FILES:
        old_path = old_local_path(old_file_name)
        if os.path.exists(old_path) and not os.path.exists(new_path):
            shutil.copy2(old_path, new_path)

    old_backup_folder = old_local_path("vault_backups")
    if os.path.exists(old_backup_folder) and not os.path.exists(BACKUP_FOLDER):
        shutil.copytree(old_backup_folder, BACKUP_FOLDER)


def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def vault_exists():
    return os.path.exists(SALT_FILE) and os.path.exists(VERIFY_FILE)


def derive_key(master_password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))


def create_vault(master_password):
    salt = os.urandom(16)
    key = derive_key(master_password, salt)
    fernet = Fernet(key)

    with open(SALT_FILE, "wb") as salt_file:
        salt_file.write(salt)

    with open(VERIFY_FILE, "wb") as verify_file:
        verify_file.write(fernet.encrypt(b"vault-ok"))

    return fernet


def unlock_vault(master_password):
    with open(SALT_FILE, "rb") as salt_file:
        salt = salt_file.read()

    with open(VERIFY_FILE, "rb") as verify_file:
        verify_token = verify_file.read()

    key = derive_key(master_password, salt)
    fernet = Fernet(key)

    try:
        if fernet.decrypt(verify_token) == b"vault-ok":
            return fernet
    except InvalidToken:
        return None

    return None


def generate_password(length, use_upper, use_lower, use_digits, use_symbols):
    choices = []
    required_chars = []

    if use_upper:
        choices.append(string.ascii_uppercase)
        required_chars.append(secrets.choice(string.ascii_uppercase))
    if use_lower:
        choices.append(string.ascii_lowercase)
        required_chars.append(secrets.choice(string.ascii_lowercase))
    if use_digits:
        choices.append(string.digits)
        required_chars.append(secrets.choice(string.digits))
    if use_symbols:
        choices.append(string.punctuation)
        required_chars.append(secrets.choice(string.punctuation))

    if not choices:
        return None, "You must select at least one character type."

    if length < len(required_chars):
        return None, f"Password length must be at least {len(required_chars)}."

    char_pool = "".join(choices)
    password_chars = required_chars[:]

    while len(password_chars) < length:
        password_chars.append(secrets.choice(char_pool))

    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars), None


def build_record(label, username, password, note):
    timestamp = current_timestamp()
    return {
        "label": label,
        "username": username,
        "password": password,
        "note": note,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def save_record(fernet, label, username, password, note):
    encrypted_record = fernet.encrypt(
        json.dumps(build_record(label, username, password, note)).encode("utf-8")
    )

    with open(VAULT_FILE, "ab") as vault_file:
        vault_file.write(encrypted_record + b"\n")


def load_records(fernet):
    if not os.path.exists(VAULT_FILE):
        return [], []

    records = []
    errors = []
    with open(VAULT_FILE, "rb") as vault_file:
        for line_number, line in enumerate(vault_file, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                decrypted = fernet.decrypt(line)
                record = json.loads(decrypted.decode("utf-8"))
                record.setdefault("note", "")
                record.setdefault("created_at", "Not recorded")
                record.setdefault("updated_at", "Not recorded")
                records.append(record)
            except (InvalidToken, json.JSONDecodeError):
                errors.append(line_number)

    return records, errors


def save_all_records(fernet, records):
    with open(VAULT_FILE, "wb") as vault_file:
        for record in records:
            encrypted_record = fernet.encrypt(json.dumps(record).encode("utf-8"))
            vault_file.write(encrypted_record + b"\n")


def find_matching_records(records, search_text):
    return [
        (index, record)
        for index, record in enumerate(records)
        if search_text in record["label"].lower()
    ]


def update_record(record, label=None, username=None, password=None, note=None):
    if label:
        record["label"] = label
    if username:
        record["username"] = username
    if note:
        record["note"] = note
    if password is not None:
        record["password"] = password

    record["updated_at"] = current_timestamp()


def copy_to_clipboard(text):
    if os.name == "nt":
        try:
            subprocess.run(
                ["clip"],
                input=text,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return True
        except Exception:
            pass

    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False


def create_backup(prefix="backup"):
    existing_files = [
        (file_name, file_path)
        for file_name, file_path in VAULT_FILES
        if os.path.exists(file_path)
    ]

    if not existing_files:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_FOLDER, f"{prefix}_{timestamp}")
    os.makedirs(backup_path, exist_ok=True)

    for file_name, file_path in existing_files:
        shutil.copy2(file_path, os.path.join(backup_path, file_name))

    return backup_path


def get_backup_folders():
    if not os.path.exists(BACKUP_FOLDER):
        return []

    backup_folders = []
    required_file_names = [file_name for file_name, _ in VAULT_FILES]

    for entry_name in os.listdir(BACKUP_FOLDER):
        backup_path = os.path.join(BACKUP_FOLDER, entry_name)
        if not os.path.isdir(backup_path):
            continue

        has_required_files = all(
            os.path.exists(os.path.join(backup_path, file_name))
            for file_name in required_file_names
        )
        if has_required_files:
            backup_folders.append(backup_path)

    backup_folders.sort(reverse=True)
    return backup_folders


def restore_backup(backup_path):
    safety_backup_path = create_backup("pre_restore_backup")

    for file_name, file_path in VAULT_FILES:
        shutil.copy2(os.path.join(backup_path, file_name), file_path)

    return safety_backup_path
