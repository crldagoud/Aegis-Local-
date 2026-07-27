"""
Import des mots de passe enregistrés dans les navigateurs basés sur Chromium
(Google Chrome, Microsoft Edge, Brave...).

Fonctionnement (Windows uniquement pour la méthode directe) :
- Chrome/Edge stockent les identifiants dans un fichier SQLite "Login Data".
- La clé de chiffrement de ces mots de passe est elle-même stockée (chiffrée
  via DPAPI, l'API de chiffrement de Windows liée à la session utilisateur)
  dans un fichier JSON "Local State".
- On récupère cette clé via DPAPI (CryptUnprotectData), puis on l'utilise
  pour déchiffrer chaque mot de passe (AES-256-GCM depuis Chrome 80+).

IMPORTANT : depuis 2024, les versions récentes de Chrome/Edge sur Windows
ont ajouté un chiffrement supplémentaire dit "app-bound encryption", qui lie
la clé au processus du navigateur lui-même. Dans ce cas, cette méthode
directe peut échouer. C'est pourquoi une méthode de repli par import CSV
est proposée : Chrome/Edge permettent d'exporter les mots de passe
enregistrés depuis leurs paramètres (Paramètres > Mots de passe > Exporter
les mots de passe), ce qui génère un fichier .csv qu'on peut importer ici
sans aucune limitation.
"""

import os
import csv
import json
import base64
import shutil
import sqlite3
import platform
import tempfile
from dataclasses import dataclass


@dataclass
class ImportedCredential:
    site: str
    username: str
    password: str


class BrowserImportError(Exception):
    pass


def _get_chromium_master_key(local_state_path: str) -> bytes:
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)

    encrypted_key_b64 = local_state["os_crypt"]["encrypted_key"]
    encrypted_key = base64.b64decode(encrypted_key_b64)
    encrypted_key = encrypted_key[5:]  # on retire le préfixe "DPAPI"

    import win32crypt  # disponible uniquement sur Windows (pywin32)

    key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return key


def _decrypt_chromium_password(buff: bytes, key: bytes) -> str:
    if not buff:
        return ""
    try:
        if buff[:3] in (b"v10", b"v11"):
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            iv = buff[3:15]
            payload = buff[15:-16]
            tag = buff[-16:]
            aesgcm = AESGCM(key)
            decrypted = aesgcm.decrypt(iv, payload + tag, None)
            return decrypted.decode("utf-8", errors="ignore")
        else:
            import win32crypt

            decrypted = win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1]
            return decrypted.decode("utf-8", errors="ignore")
    except Exception:
        # Mot de passe illisible (probablement "app-bound encryption" récent) :
        # on ignore plutôt que de planter tout l'import.
        return ""


def _extract_from_profile(login_data_path: str, local_state_path: str) -> list[ImportedCredential]:
    if not os.path.exists(login_data_path):
        return []
    if not os.path.exists(local_state_path):
        return []

    key = _get_chromium_master_key(local_state_path)

    # On copie la base avant lecture : si le navigateur est ouvert, le
    # fichier original est verrouillé.
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        shutil.copy2(login_data_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        try:
            cur = conn.execute("SELECT origin_url, username_value, password_value FROM logins")
            results = []
            for url, username, password_blob in cur.fetchall():
                password = _decrypt_chromium_password(password_blob, key)
                if url or username:
                    results.append(ImportedCredential(site=url or "", username=username or "", password=password))
            return results
        finally:
            conn.close()
    finally:
        os.remove(tmp_path)


def _chrome_paths() -> tuple[str, str]:
    local = os.environ["LOCALAPPDATA"]
    login_data = os.path.join(local, "Google", "Chrome", "User Data", "Default", "Login Data")
    local_state = os.path.join(local, "Google", "Chrome", "User Data", "Local State")
    return login_data, local_state


def _edge_paths() -> tuple[str, str]:
    local = os.environ["LOCALAPPDATA"]
    login_data = os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Login Data")
    local_state = os.path.join(local, "Microsoft", "Edge", "User Data", "Local State")
    return login_data, local_state


def import_from_chrome() -> list[ImportedCredential]:
    if platform.system() != "Windows":
        raise BrowserImportError("L'import direct depuis Chrome n'est disponible que sur Windows.")
    login_data, local_state = _chrome_paths()
    return _extract_from_profile(login_data, local_state)


def import_from_edge() -> list[ImportedCredential]:
    if platform.system() != "Windows":
        raise BrowserImportError("L'import direct depuis Edge n'est disponible que sur Windows.")
    login_data, local_state = _edge_paths()
    return _extract_from_profile(login_data, local_state)


def import_from_csv(csv_path: str) -> list[ImportedCredential]:
    """
    Import depuis un fichier CSV exporté par un navigateur
    (Chrome/Edge/Firefox utilisent tous des colonnes similaires :
    name/url, username, password).
    """
    results = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise BrowserImportError("Fichier CSV vide ou illisible.")

        # On normalise les noms de colonnes (les navigateurs varient un peu).
        fieldmap = {name.strip().lower(): name for name in reader.fieldnames}
        url_col = fieldmap.get("url") or fieldmap.get("origin_url") or fieldmap.get("login_uri")
        user_col = fieldmap.get("username") or fieldmap.get("login_username")
        pass_col = fieldmap.get("password") or fieldmap.get("login_password")

        if not (url_col and pass_col):
            raise BrowserImportError(
                "Colonnes attendues introuvables dans le CSV (url, username, password)."
            )

        for row in reader:
            results.append(
                ImportedCredential(
                    site=(row.get(url_col) or "").strip(),
                    username=(row.get(user_col) or "").strip() if user_col else "",
                    password=(row.get(pass_col) or "").strip(),
                )
            )
    return results
