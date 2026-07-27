# Aegis Local 🛡️🔒

A secure, lightweight desktop application designed to centralize and protect your credentials strictly **locally** on your machine. Nothing is ever sent to the internet; your data remains fully encrypted on your disk.

## ✨ Features

* **Master Password Vault:** Secure your entire vault behind a single master password created on first startup (never stored in plain text, only as a cryptographic hash via PBKDF2).
* **Browser Credentials Import (Windows):** Automatically scan and import existing login credentials from Google Chrome and Microsoft Edge (with user permission).
* **Offline CSV Import:** Import passwords via a `.csv` file exported from any other browser (Firefox, Brave, etc.).
* **Local Storage & Encryption:** All database entries (Website, Email, Password) are protected by robust local encryption (Fernet / AES).
* **Intuitive Interface:**
  * **Password Toggle:** Hide or reveal plain-text passwords using the eye icon (👁).
  * **Quick Copy:** Copy any password directly to your clipboard with the copy icon (📋).
  * **Inline Editing:** Double-click on any field to modify it directly.
* **Full Management:** Manually create new entries or delete outdated records easily.
* **Integrated Generator:** Includes a random password generator for creating new, strong credentials.

## ⚠️ Security & Safety Warning

> **DISCLAIMER:** This project is intended for educational and personal utility purposes.
>
> * **Local Responsibility:** Your passwords are stored solely on your local disk. **If you forget your Master Password, there is no recovery mechanism.**
> * **Source Code Integrity:** Only compile or run this application from trusted sources. Compromised dependencies or exposed encryption keys can put your credentials at risk.

## 🛠️ Requirements & Installation

Aegis Local requires Python 3.10 or newer (with Tkinter, which is included by default in the official Python installer on Windows).

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt

   Run the Application:

On the very first launch, the app will prompt you to create your master password, then offer to import existing passwords from Chrome/Edge.

📂 Where is Data Stored?
Everything is stored in a hidden directory inside your user home folder:

~/.aegis_local/config.json → Cryptographic salt + verification token (never the master password itself).

~/.aegis_local/vault.db → A local SQLite database containing your entries, with passwords fully encrypted.

On Windows, ~ corresponds to C:\Users\YourName\.

💡 Technical Note: Browser Auto-Import
This feature reads the local file where Chrome/Edge store credentials and decrypts them using the Windows Data Protection API (DPAPI)—the exact same mechanism used by the browsers themselves. Everything happens strictly on your machine.

Known Limitation: Recent updates to Chrome/Edge may enforce strict process isolation, locking these database files while the browser is running. Make sure to close your browser before attempting a direct import. If automatic import fails, use the CSV Import option.

🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
