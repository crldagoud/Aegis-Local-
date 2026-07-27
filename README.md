# Aegis Local 🛡️🔒 — Gestionnaire de mots de passe local

Un gestionnaire de mots de passe qui tourne entièrement **en local** sur ta
machine. Rien n'est envoyé sur internet, tout reste chiffré sur ton disque.

## Fonctionnalités

- Création d'un **mot de passe maître** au premier lancement (jamais stocké
  en clair, seulement une dérivation cryptographique via PBKDF2).
- **Import automatique** des mots de passe déjà enregistrés dans Google
  Chrome / Microsoft Edge (Windows), ou via un fichier `.csv` exporté
  depuis n'importe quel navigateur.
- Liste des mots de passe : site, identifiant, mot de passe masqué.
- Bouton **œil (👁)** pour révéler/masquer un mot de passe.
- **Double-clic** sur le site, l'identifiant ou le mot de passe pour le
  modifier.
- Bouton **📋** pour copier un mot de passe dans le presse-papiers.
- Bouton **+ Ajouter** pour créer une nouvelle entrée (avec générateur de
  mot de passe aléatoire intégré).
- Bouton **🗑** pour supprimer une entrée.
- Barre de recherche pour filtrer par site.

## Installation

Il faut Python 3.10 ou plus récent (avec Tkinter, inclus par défaut dans
l'installeur officiel Python sur Windows).

```bash
pip install -r requirements.txt
```

## Lancement

```bash
python main.py
```

Au tout premier lancement, l'application te demande de créer ton mot de
passe maître, puis te propose d'importer tes mots de passe existants
depuis Chrome/Edge.

## Où sont stockées les données ?

Tout est stocké dans un dossier caché de ton profil utilisateur :

- `~/.pyvault/config.json` → le sel cryptographique + un jeton de
  vérification (jamais ton mot de passe maître lui-même).
- `~/.pyvault/vault.db` → une base SQLite contenant tes entrées, avec les
  mots de passe **chiffrés** (Fernet / AES).

Sur Windows, `~` correspond à `C:\Users\TonNom\`.

⚠️ Si tu perds ton mot de passe maître, il n'y a **aucun moyen** de
récupérer les mots de passe stockés (c'est volontaire, c'est ce qui rend
le chiffrement solide). Choisis-en un dont tu te souviendras, ou note-le
quelque part en sécurité.

## À propos de l'import automatique Chrome/Edge

Cette fonctionnalité lit le fichier local où Chrome/Edge stockent tes
identifiants, et déchiffre les mots de passe via l'API de chiffrement de
Windows (DPAPI) — exactement le même mécanisme que celui qu'utilisent les
navigateurs eux-mêmes. Tout se passe en local, aucune donnée ne quitte ta
machine.

**Limitation connue** : depuis 2024, les versions récentes de Chrome/Edge
sur Windows ont ajouté une couche de protection supplémentaire ("app-bound
encryption") qui peut empêcher cette méthode directe de fonctionner. Si
l'import automatique échoue ou ramène 0 mot de passe, utilise le bouton
**"Importer un CSV"** : va dans les paramètres de ton navigateur
(`Mots de passe` → `Exporter les mots de passe`), ce qui génère un fichier
`.csv`, puis importe-le directement dans PyVault.

Pense aussi à **fermer le navigateur** avant de lancer l'import direct,
certains fichiers pouvant être verrouillés pendant que Chrome/Edge tourne.

## Structure du projet

```
password_manager/
├── main.py             # point d'entrée
├── gui.py               # interface graphique (Tkinter)
├── crypto_utils.py       # mot de passe maître + chiffrement
├── db.py                 # stockage SQLite local
├── browser_import.py      # import Chrome / Edge / CSV
└── requirements.txt
```

## Idées d'améliorations futures

- Verrouillage automatique après un temps d'inactivité.
- Export chiffré / sauvegarde du coffre.
- Indicateur de force du mot de passe et détection de doublons.
- Recherche floue (tolérance aux fautes de frappe).
