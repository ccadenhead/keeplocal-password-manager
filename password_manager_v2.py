# Copyright (c) 2026 Charles Cadenhead
# All rights reserved.

import getpass
import sys

import vault_core


def show_startup_warning():
    print("\n====================")
    print("  Password Manager")
    print("====================")
    print("\nIMPORTANT SECURITY WARNING")
    print("This vault is local and has no recovery backdoor.")
    print("If the master password is forgotten, saved passwords cannot be recovered.")
    print("Keep secure backups of the vault files and remember the master password.")


def show_message(message):
    print(f"\n{message}\n")


def read_secret(prompt):
    if sys.stdin is not None and sys.stdin.isatty():
        return getpass.getpass(prompt)

    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        value = simpledialog.askstring("Password Manager", prompt, show="*")
        root.destroy()
        return value or ""
    except Exception:
        return input(prompt)


def create_vault_flow():
    print("\nCreate a master password for this local vault.")
    while True:
        master_password = read_secret("New master password: ")
        confirm_password = read_secret("Confirm master password: ")

        if not master_password:
            show_message("Master password cannot be blank.")
        elif master_password != confirm_password:
            show_message("Passwords do not match. Try again.")
        else:
            break

    fernet = vault_core.create_vault(master_password)
    show_message("Local vault created.")
    return fernet


def unlock_vault_flow():
    if not vault_core.vault_exists():
        return create_vault_flow()

    for _ in range(3):
        master_password = read_secret("Master password: ")
        fernet = vault_core.unlock_vault(master_password)

        if fernet is not None:
            return fernet

        show_message("Incorrect master password.")

    show_message("Too many failed attempts.")
    return None


def ask_yes_no(prompt):
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        show_message("Please enter y or n.")


def ask_password_length():
    while True:
        try:
            length = int(input("Enter the desired password length: "))
            if length > 0:
                return length
            show_message("Password length must be greater than zero.")
        except ValueError:
            show_message("Please enter a whole number.")


def generate_password_flow():
    length = ask_password_length()
    password, error = vault_core.generate_password(
        length=length,
        use_upper=ask_yes_no("Include uppercase letters? (y/n): "),
        use_lower=ask_yes_no("Include lowercase letters? (y/n): "),
        use_digits=ask_yes_no("Include numbers? (y/n): "),
        use_symbols=ask_yes_no("Include symbols? (y/n): "),
    )

    if error:
        show_message(error)
        return None

    return password


def load_records_with_messages(fernet):
    records, errors = vault_core.load_records(fernet)
    for line_number in errors:
        show_message(f"Could not decrypt record on line {line_number}.")
    return records


def add_password(fernet):
    label = input("Website/app label: ").strip()
    username = input("Username/email: ").strip()

    if not label or not username:
        show_message("Label and username are required.")
        return

    records = load_records_with_messages(fernet)
    duplicate_labels = [
        record for record in records
        if record["label"].lower() == label.lower()
    ]
    if duplicate_labels:
        show_message(f"Warning: {len(duplicate_labels)} saved record(s) already use this label.")
        if not ask_yes_no("Save another record with this label? (y/n): "):
            return

    if ask_yes_no("Generate a password? (y/n): "):
        password = generate_password_flow()
        if password is None:
            return

        if ask_yes_no("Reveal generated password now? (y/n): "):
            show_message(f"Generated password: {password}")
    else:
        password = read_secret("Password to save: ")
        if not password:
            show_message("Password cannot be blank.")
            return

    note = input("Note (optional): ").strip()

    vault_core.save_record(fernet, label, username, password, note)
    show_message("Encrypted record saved.")


def choose_record(matches):
    if not matches:
        show_message("No matching records found.")
        return None

    print("\nMatches:")
    for display_number, (_, record) in enumerate(matches, start=1):
        print(f"{display_number}. {record['label']} | {record['username']}")

    try:
        selected = int(input("Enter match number: "))
        return matches[selected - 1]
    except (ValueError, IndexError):
        show_message("Invalid selection.")
        return None


def edit_record(record):
    print("\nPress Enter to keep the current value.")

    new_label = input(f"Website/app label [{record['label']}]: ").strip()
    new_username = input(f"Username/email [{record['username']}]: ").strip()
    current_note = record.get("note", "")
    new_note = input(f"Note [{current_note}]: ").strip()

    if ask_yes_no("Change password? (y/n): "):
        if ask_yes_no("Generate a new password? (y/n): "):
            new_password = generate_password_flow()
            if new_password is None:
                return False

            show_message(f"Generated password: {new_password}")
        else:
            new_password = read_secret("New password: ")
            if not new_password:
                show_message("Password was not changed.")
                new_password = record["password"]
    else:
        new_password = record["password"]

    vault_core.update_record(
        record,
        label=new_label,
        username=new_username,
        password=new_password,
        note=new_note,
    )
    return True


def manage_passwords(fernet):
    search_text = input("Search website/app label to manage: ").strip().lower()
    if not search_text:
        show_message("Search text is required.")
        return

    records = load_records_with_messages(fernet)
    selected_match = choose_record(vault_core.find_matching_records(records, search_text))
    if selected_match is None:
        return

    record_index, record = selected_match

    print("\nOptions:")
    print("1. Edit record")
    print("2. Delete record")
    print("3. Cancel")

    choice = input("Choose an option (1/2/3): ").strip()

    if choice == "1":
        if edit_record(record):
            records[record_index] = record
            vault_core.save_all_records(fernet, records)
            show_message("Record updated.")
    elif choice == "2":
        if ask_yes_no(f"Delete '{record['label']}'? (y/n): "):
            del records[record_index]
            vault_core.save_all_records(fernet, records)
            show_message("Record deleted.")
    elif choice == "3":
        return
    else:
        show_message("Invalid choice.")


def search_passwords(fernet):
    search_text = input("Search website/app label: ").strip().lower()
    if not search_text:
        show_message("Search text is required.")
        return

    records = load_records_with_messages(fernet)
    matches = [
        record for record in records
        if search_text in record["label"].lower()
    ]

    if not matches:
        show_message("No matching records found.")
        return

    print("\nMatches:")
    for index, record in enumerate(matches, start=1):
        print(f"\n{index}. {record['label']}")
        print(f"Username: {record['username']}")
        print(f"Password: {record['password']}")
        if record.get("note"):
            print(f"Note: {record['note']}")
        print(f"Created: {record['created_at']}")
        print(f"Updated: {record['updated_at']}")

    if len(matches) == 1:
        record_to_copy = matches[0]
    else:
        try:
            selected = int(input("\nEnter match number to copy from: "))
            record_to_copy = matches[selected - 1]
        except (ValueError, IndexError):
            show_message("Invalid selection. Nothing copied.")
            return

    print("\nCopy to clipboard:")
    print("1. Username")
    print("2. Password")
    print("3. Nothing")
    copy_choice = input("Choose an option (1/2/3): ").strip()

    if copy_choice == "1":
        copied_text = record_to_copy["username"]
        copied_label = "Username"
    elif copy_choice == "2":
        copied_text = record_to_copy["password"]
        copied_label = "Password"
    elif copy_choice == "3":
        return
    else:
        show_message("Invalid choice. Nothing copied.")
        return

    if vault_core.copy_to_clipboard(copied_text):
        show_message(f"{copied_label} copied to clipboard.")
    else:
        show_message("Could not copy to clipboard.")


def create_backup_flow():
    backup_path = vault_core.create_backup()
    if backup_path is None:
        show_message("No vault files found to back up.")
    else:
        show_message(f"Encrypted backup created: {backup_path}")


def restore_backup_flow():
    backup_folders = vault_core.get_backup_folders()
    if not backup_folders:
        show_message("No complete backups found.")
        return

    print("\nAvailable backups:")
    for index, backup_path in enumerate(backup_folders, start=1):
        print(f"{index}. {backup_path}")

    try:
        selected = int(input("Enter backup number to restore: "))
        backup_path = backup_folders[selected - 1]
    except (ValueError, IndexError):
        show_message("Invalid selection.")
        return

    print("\nWARNING: Restoring a backup will replace the current vault files.")
    print("After restore, restart the program and unlock with that backup's master password.")
    if not ask_yes_no("Restore this backup? (y/n): "):
        show_message("Restore cancelled.")
        return

    show_message("Creating a safety backup of the current vault before restore.")
    vault_core.restore_backup(backup_path)
    show_message("Backup restored. Please exit and restart the program.")


def backup_or_restore():
    while True:
        print("\nBackup or Restore:")
        print("1. Create backup")
        print("2. Restore from backup")
        print("3. Cancel")

        choice = input("Choose an option (1/2/3): ").strip()

        if choice == "1":
            create_backup_flow()
            return
        if choice == "2":
            restore_backup_flow()
            return
        if choice == "3":
            return

        show_message("Invalid choice, try again.")


def main():
    show_startup_warning()
    vault_core.setup_app_data_folder()
    print(f"Vault location: {vault_core.APP_DATA_FOLDER}")

    fernet = unlock_vault_flow()
    if fernet is None:
        return

    while True:
        print("\nOptions:")
        print("1. Add saved password")
        print("2. Edit or delete saved password")
        print("3. Search saved passwords")
        print("4. Backup or restore vault")
        print("5. Exit")

        choice = input("Choose an option (1/2/3/4/5): ").strip()

        if choice == "1":
            add_password(fernet)
        elif choice == "2":
            manage_passwords(fernet)
        elif choice == "3":
            search_passwords(fernet)
        elif choice == "4":
            backup_or_restore()
        elif choice == "5":
            break
        else:
            show_message("Invalid choice, try again.")


if __name__ == "__main__":
    main()
