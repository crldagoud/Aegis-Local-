"""
Gestion du mot de passe maître et du chiffrement du coffre.

Le mot de passe maître n'est JAMAIS stocké tel quel. On dérive une clé
de chiffrement à partir de lui (PBKDF2), et on garde uniquement un
"jeton de vérification" chiffré pour pouvoir contrôler qu'un mot de
passe saisi est le bon, sans jamais avoir à le stocker en clair.
"""

import os
import json
import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

KDF_ITERATIONS = 390_000
CHECK_PLAINTEXT = b"pyvault-master-check"


def _derive_key(master_password: str, salt: bytes, iterations: int = KDF_ITERATIONS) -> bytes:
    """Transforme le mot de passe maître + un sel en clé Fernet (32 octets encodés base64)."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    raw_key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


def is_first_run(config_path: str) -> bool:
    """Vrai si aucun mot de passe maître n'a encore été créé."""
    return not os.path.exists(config_path)


def create_master_password(master_password: str, config_path: str) -> Fernet:
    """
    Crée le mot de passe maître pour la toute première utilisation.
    Retourne un objet Fernet à garder en mémoire pendant la session
    (jamais écrit sur le disque).
    """
    salt = os.urandom(16)
    key = _derive_key(master_password, salt)
    fernet = Fernet(key)

    check_token = fernet.encrypt(CHECK_PLAINTEXT)

    data = {
        "salt": base64.b64encode(salt).decode("utf-8"),
        "check": base64.b64encode(check_token).decode("utf-8"),
        "iterations": KDF_ITERATIONS,
    }
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return fernet


def unlock(master_password: str, config_path: str) -> Fernet | None:
    """
    Tente de déverrouiller le coffre avec le mot de passe saisi.
    Retourne l'objet Fernet si le mot de passe est correct, sinon None.
    """
    if not os.path.exists(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    salt = base64.b64decode(data["salt"])
    iterations = data.get("iterations", KDF_ITERATIONS)
    key = _derive_key(master_password, salt, iterations)
    fernet = Fernet(key)

    try:
        token = base64.b64decode(data["check"])
        result = fernet.decrypt(token)
    except (InvalidToken, ValueError):
        return None

    if result == CHECK_PLAINTEXT:
        return fernet
    return None


def change_master_password(old_password: str, new_password: str, config_path: str, db_reencrypt_callback) -> bool:
    """
    Change le mot de passe maître : dérive une nouvelle clé, puis
    déchiffre/rechiffre toutes les entrées existantes avec la nouvelle clé
    via db_reencrypt_callback(old_fernet, new_fernet).
    """
    old_fernet = unlock(old_password, config_path)
    if old_fernet is None:
        return False

    salt = os.urandom(16)
    new_key = _derive_key(new_password, salt)
    new_fernet = Fernet(new_key)

    db_reencrypt_callback(old_fernet, new_fernet)

    check_token = new_fernet.encrypt(CHECK_PLAINTEXT)
    data = {
        "salt": base64.b64encode(salt).decode("utf-8"),
        "check": base64.b64encode(check_token).decode("utf-8"),
        "iterations": KDF_ITERATIONS,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return True
