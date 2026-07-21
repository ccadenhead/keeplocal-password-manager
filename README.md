# KeepLocal Password Manager

KeepLocal is a local-first password manager prototype for Windows, built with help from Codex and GPT-5.6. It keeps saved credentials encrypted on the user's own computer, without cloud sync, online accounts, or recovery backdoors.

This project was inspired by my son, who wanted a password manager he could trust without relying on an online service.

## Use of Codex and GPT-5.6

Codex and GPT-5.6 were used as development partners throughout this project. I am a professor, not a full-time software engineer, and Codex helped me move from an old beginner Python password generator into a structured, working password manager prototype.

Codex and GPT-5.6 helped with:

- Reasoning through the security model
- Replacing a stored encryption key with master-password-derived encryption
- Debugging Windows-specific behavior, including clipboard support
- Refactoring the app into a command-line interface and reusable vault core
- Improving terminal messages and demo flow
- Writing README and submission materials

KeepLocal itself does not use AI at runtime. Passwords, vault files, and user data are not sent to OpenAI or any cloud service.

## What It Does

- Creates a local encrypted password vault
- Unlocks the vault with a master password
- Saves encrypted login records
- Stores website/app labels, usernames, passwords, notes, and timestamps
- Searches saved records by label
- Edits and deletes saved records
- Copies usernames or passwords to the Windows clipboard
- Creates encrypted local backups
- Restores from encrypted backups
- Stores vault data in the user's local AppData folder

## Security Model

KeepLocal is designed around a simple rule: there is no backdoor.

The master password is used to derive the encryption key. The app does not store the raw encryption key on disk. If the master password is forgotten, the saved vault data cannot be recovered.

Vault files are stored locally under:

```text
C:\Users\<user>\AppData\Local\LocalPasswordManager
```

The encrypted vault files include:

```text
password_vault.jsonl
vault_salt.bin
vault_verify.token
vault_backups\
```

These files should not be uploaded publicly or shared.

## Project Structure

```text
password_manager_v2.py   # Command-line interface and user prompts
vault_core.py            # Vault paths, encryption, records, clipboard, backup/restore
.gitignore               # Prevents local vault data from being committed
```

## How It Was Built

KeepLocal is built with Python and the `cryptography` package.

The project started as a simple password generator, then grew into a local password manager with Codex and GPT-5.6 helping guide the architecture, debugging, and refactoring process. As the app became more serious, the code was split into a command-line interface and a reusable vault core. This makes it easier to build a future graphical Windows version without rewriting the encryption and storage logic.

## Requirements

- Windows
- Python 3
- `cryptography`

Install the required package:

```bash
python -m pip install cryptography
```

## Run It

From the project folder:

```bash
python password_manager_v2.py
```

On first run, the app will ask the user to create a master password. After that, the vault unlocks with that master password.

## Current Status

This is a working console prototype. It demonstrates the core password manager workflow:

1. Create a local vault
2. Add encrypted records
3. Search records
4. Copy usernames or passwords
5. Edit or delete records
6. Back up and restore the vault

## Challenges

One challenge was replacing the original stored-key approach with a master-password-based encryption model. This made the app safer, but also introduced the important tradeoff that forgotten master passwords cannot be recovered.

Another challenge was handling backup and restore safely. Since restoring a backup replaces the active vault files, the app now creates a pre-restore safety backup before replacing anything.

Windows clipboard support also needed special handling. The app now uses Windows' built-in clipboard command for more reliable copy behavior.

## What I Learned

This project taught me more about local encryption, key derivation, backup safety, and the user experience details that matter even in a command-line app. Clear warnings, predictable file locations, and readable terminal output all make the project feel safer and easier to use.

It also showed me how Codex can support a builder with limited coding background: not just by generating snippets, but by helping reason through design decisions, spot bugs, simplify structure, and turn a rough idea into a working prototype.

## What's Next

Planned future improvements:

- Rename the app throughout the interface
- Add a full Windows graphical interface
- Package the app as a Windows executable
- Add password strength guidance
- Add optional auto-lock after inactivity
- Improve backup and restore screens
- Add import/export tools

## Important Note

This project is a prototype and should be reviewed carefully before storing real credentials in it.

## License

Copyright (c) 2026 Charles Cadenhead. All rights reserved.

This source code is provided for hackathon review purposes only. No permission is granted to copy, modify, distribute, or use this code without written permission.
