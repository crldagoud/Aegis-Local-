"""
Interface graphique du gestionnaire de mots de passe (Tkinter).
"""

import os
import secrets
import string
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import crypto_utils
import db
import browser_import

APP_TITLE = "PyVault - Gestionnaire de mots de passe"
DATA_DIR = os.path.join(os.path.expanduser("~"), ".pyvault")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
DB_PATH = os.path.join(DATA_DIR, "vault.db")

BG = "#1e1f26"
BG_CARD = "#262832"
FG = "#e6e6e6"
FG_MUTED = "#9a9ca8"
ACCENT = "#5b8cff"
ACCENT_HOVER = "#4472e0"
DANGER = "#e05d5d"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 18, "bold")


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x600")
        self.minsize(700, 450)
        self.configure(bg=BG)

        self.fernet = None  # défini une fois le coffre déverrouillé
        self.conn = None

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self._show_entry_screen()

    # ------------------------------------------------------------------ #
    # Navigation entre écrans
    # ------------------------------------------------------------------ #
    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def _show_entry_screen(self):
        self._clear_container()
        if crypto_utils.is_first_run(CONFIG_PATH):
            SetupScreen(self.container, self)
        else:
            LoginScreen(self.container, self)

    def on_unlocked(self, fernet):
        self.fernet = fernet
        self.conn = db.get_connection(DB_PATH)
        self._clear_container()
        MainScreen(self.container, self)

    def on_first_setup_done(self, fernet):
        self.fernet = fernet
        self.conn = db.get_connection(DB_PATH)
        self._clear_container()
        ImportPromptScreen(self.container, self)

    def lock(self):
        self.fernet = None
        if self.conn:
            self.conn.close()
            self.conn = None
        self._show_entry_screen()


# ---------------------------------------------------------------------- #
# Écran 1 : création du mot de passe maître (première utilisation)
# ---------------------------------------------------------------------- #
class SetupScreen(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=BG)
        self.app = app
        self.pack(fill="both", expand=True)

        card = tk.Frame(self, bg=BG_CARD, padx=40, pady=40)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="Bienvenue dans PyVault", font=FONT_TITLE, bg=BG_CARD, fg=FG).pack(pady=(0, 6))
        tk.Label(
            card,
            text="Crée ton mot de passe maître.\nIl protège l'accès à tous tes mots de passe.",
            font=FONT, bg=BG_CARD, fg=FG_MUTED, justify="center",
        ).pack(pady=(0, 20))

        tk.Label(card, text="Mot de passe maître", font=FONT, bg=BG_CARD, fg=FG, anchor="w").pack(fill="x")
        self.pwd1 = tk.Entry(card, show="•", font=FONT, width=32, bg="#33353f", fg=FG, insertbackground=FG, relief="flat")
        self.pwd1.pack(ipady=6, pady=(4, 14))

        tk.Label(card, text="Confirme le mot de passe", font=FONT, bg=BG_CARD, fg=FG, anchor="w").pack(fill="x")
        self.pwd2 = tk.Entry(card, show="•", font=FONT, width=32, bg="#33353f", fg=FG, insertbackground=FG, relief="flat")
        self.pwd2.pack(ipady=6, pady=(4, 20))

        self.error_label = tk.Label(card, text="", font=FONT, bg=BG_CARD, fg=DANGER)
        self.error_label.pack()

        btn = tk.Button(
            card, text="Créer mon coffre", font=FONT_BOLD, bg=ACCENT, fg="white",
            activebackground=ACCENT_HOVER, relief="flat", padx=20, pady=8, cursor="hand2",
            command=self._create,
        )
        btn.pack(pady=(10, 0))

        self.pwd1.focus_set()
        self.pwd2.bind("<Return>", lambda e: self._create())

    def _create(self):
        p1, p2 = self.pwd1.get(), self.pwd2.get()
        if len(p1) < 6:
            self.error_label.config(text="Le mot de passe doit faire au moins 6 caractères.")
            return
        if p1 != p2:
            self.error_label.config(text="Les deux mots de passe ne correspondent pas.")
            return
        fernet = crypto_utils.create_master_password(p1, CONFIG_PATH)
        self.app.on_first_setup_done(fernet)


# ---------------------------------------------------------------------- #
# Écran 2 : déverrouillage (lancements suivants)
# ---------------------------------------------------------------------- #
class LoginScreen(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=BG)
        self.app = app
        self.pack(fill="both", expand=True)

        card = tk.Frame(self, bg=BG_CARD, padx=40, pady=40)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="PyVault", font=FONT_TITLE, bg=BG_CARD, fg=FG).pack(pady=(0, 6))
        tk.Label(card, text="Entre ton mot de passe maître pour déverrouiller le coffre.",
                 font=FONT, bg=BG_CARD, fg=FG_MUTED).pack(pady=(0, 20))

        self.pwd = tk.Entry(card, show="•", font=FONT, width=32, bg="#33353f", fg=FG, insertbackground=FG, relief="flat")
        self.pwd.pack(ipady=6, pady=(4, 14))

        self.error_label = tk.Label(card, text="", font=FONT, bg=BG_CARD, fg=DANGER)
        self.error_label.pack()

        btn = tk.Button(
            card, text="Déverrouiller", font=FONT_BOLD, bg=ACCENT, fg="white",
            activebackground=ACCENT_HOVER, relief="flat", padx=20, pady=8, cursor="hand2",
            command=self._try_unlock,
        )
        btn.pack(pady=(10, 0))

        self.pwd.focus_set()
        self.pwd.bind("<Return>", lambda e: self._try_unlock())

    def _try_unlock(self):
        fernet = crypto_utils.unlock(self.pwd.get(), CONFIG_PATH)
        if fernet is None:
            self.error_label.config(text="Mot de passe incorrect.")
            self.pwd.delete(0, "end")
            return
        self.app.on_unlocked(fernet)


# ---------------------------------------------------------------------- #
# Écran 3 (juste après la création) : proposer l'import navigateur
# ---------------------------------------------------------------------- #
class ImportPromptScreen(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=BG)
        self.app = app
        self.pack(fill="both", expand=True)

        card = tk.Frame(self, bg=BG_CARD, padx=40, pady=40)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="Importer tes mots de passe existants ?", font=FONT_TITLE,
                 bg=BG_CARD, fg=FG, wraplength=440, justify="center").pack(pady=(0, 10))
        tk.Label(
            card,
            text=(
                "PyVault peut récupérer les mots de passe déjà enregistrés\n"
                "dans Google Chrome ou Microsoft Edge sur cet ordinateur.\n"
                "Rien n'est envoyé sur internet : tout reste en local."
            ),
            font=FONT, bg=BG_CARD, fg=FG_MUTED, justify="center",
        ).pack(pady=(0, 24))

        row = tk.Frame(card, bg=BG_CARD)
        row.pack()
        tk.Button(row, text="Oui, importer", font=FONT_BOLD, bg=ACCENT, fg="white",
                  activebackground=ACCENT_HOVER, relief="flat", padx=18, pady=8, cursor="hand2",
                  command=self._do_import).pack(side="left", padx=6)
        tk.Button(row, text="Non merci", font=FONT, bg="#3a3c46", fg=FG,
                  relief="flat", padx=18, pady=8, cursor="hand2",
                  command=self._skip).pack(side="left", padx=6)

    def _skip(self):
        self.app._clear_container()
        MainScreen(self.app.container, self.app)

    def _do_import(self):
        imported = 0
        errors = []

        for label, func in (("Chrome", browser_import.import_from_chrome),
                             ("Edge", browser_import.import_from_edge)):
            try:
                creds = func()
                rows = [
                    (c.site, c.username, self.app.fernet.encrypt(c.password.encode("utf-8")))
                    for c in creds if c.password
                ]
                if rows:
                    db.add_entries_bulk(self.app.conn, rows)
                    imported += len(rows)
            except browser_import.BrowserImportError as e:
                errors.append(f"{label} : {e}")
            except Exception as e:
                errors.append(f"{label} : échec de l'import ({e})")

        msg = f"{imported} mot(s) de passe importé(s)."
        if errors:
            msg += "\n\nCertains navigateurs n'ont pas pu être lus :\n" + "\n".join(errors)
            msg += (
                "\n\nAstuce : depuis les paramètres de ton navigateur "
                "(Mots de passe > Exporter les mots de passe), tu peux "
                "générer un fichier .csv et l'importer via le bouton "
                "'Importer un CSV' dans l'écran principal."
            )
        messagebox.showinfo("Import terminé", msg)

        self.app._clear_container()
        MainScreen(self.app.container, self.app)


# ---------------------------------------------------------------------- #
# Écran principal : liste des mots de passe
# ---------------------------------------------------------------------- #
class MainScreen(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=BG)
        self.app = app
        self.pack(fill="both", expand=True)
        self.revealed = set()  # ids dont le mot de passe est actuellement affiché en clair

        self._build_topbar()
        self._build_list_area()
        self.refresh()

    # -- barre du haut : recherche + actions --------------------------- #
    def _build_topbar(self):
        bar = tk.Frame(self, bg=BG, pady=14, padx=20)
        bar.pack(fill="x")

        tk.Label(bar, text="PyVault", font=FONT_TITLE, bg=BG, fg=FG).pack(side="left")

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(bar, textvariable=self.search_var, font=FONT, width=24,
                                 bg="#33353f", fg=FG, insertbackground=FG, relief="flat")
        search_entry.pack(side="left", ipady=5, padx=(30, 0))
        # Le placeholder est inséré AVANT d'attacher le trace_add, pour ne pas
        # déclencher un refresh() avant que la liste (rows_frame) n'existe.
        self._add_placeholder(search_entry, "Rechercher un site...")
        self.search_var.trace_add("write", lambda *a: self.refresh())

        right = tk.Frame(bar, bg=BG)
        right.pack(side="right")

        tk.Button(right, text="+ Ajouter", font=FONT_BOLD, bg=ACCENT, fg="white",
                  activebackground=ACCENT_HOVER, relief="flat", padx=14, pady=6, cursor="hand2",
                  command=self._open_add_dialog).pack(side="left", padx=4)
        tk.Button(right, text="⭳ Importer", font=FONT, bg="#3a3c46", fg=FG,
                  relief="flat", padx=14, pady=6, cursor="hand2",
                  command=self._open_import_menu).pack(side="left", padx=4)
        tk.Button(right, text="🔑 Mot de passe maître", font=FONT, bg="#3a3c46", fg=FG,
                  relief="flat", padx=14, pady=6, cursor="hand2",
                  command=self._open_change_master_dialog).pack(side="left", padx=4)
        tk.Button(right, text="🔒 Verrouiller", font=FONT, bg="#3a3c46", fg=FG,
                  relief="flat", padx=14, pady=6, cursor="hand2",
                  command=self.app.lock).pack(side="left", padx=4)

    def _add_placeholder(self, entry: tk.Entry, text: str):
        entry.insert(0, text)
        entry.config(fg=FG_MUTED)

        def on_focus_in(e):
            if entry.get() == text:
                entry.delete(0, "end")
                entry.config(fg=FG)

        def on_focus_out(e):
            if not entry.get():
                entry.insert(0, text)
                entry.config(fg=FG_MUTED)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    # -- zone défilante contenant une ligne par entrée ------------------ #
    def _build_list_area(self):
        header = tk.Frame(self, bg=BG, padx=24)
        header.pack(fill="x")
        tk.Label(header, text="SITE", font=FONT_BOLD, bg=BG, fg=FG_MUTED, width=24, anchor="w").pack(side="left")
        tk.Label(header, text="IDENTIFIANT", font=FONT_BOLD, bg=BG, fg=FG_MUTED, width=24, anchor="w").pack(side="left")
        tk.Label(header, text="MOT DE PASSE", font=FONT_BOLD, bg=BG, fg=FG_MUTED, anchor="w").pack(side="left", fill="x", expand=True)

        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=(4, 20))

        self.canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.rows_frame = tk.Frame(self.canvas, bg=BG)

        self.rows_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw", width=1)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._canvas_window_id = self.canvas.find_all()[0]

        def _on_resize(event):
            self.canvas.itemconfig(self._canvas_window_id, width=event.width)
        self.canvas.bind("<Configure>", _on_resize)

        # Molette de souris : bindée localement (pas bind_all) pour éviter
        # une accumulation de bindings si l'écran est reconstruit plusieurs
        # fois (verrouillage / déverrouillage successifs).
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel_recursive(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    # -- (re)construction de la liste ----------------------------------- #
    def refresh(self):
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        query = self.search_var.get().strip().lower()
        if query == "rechercher un site...":
            query = ""

        entries = db.get_all_entries(self.app.conn)
        if query:
            entries = [e for e in entries if query in (e[1] or "").lower()]

        if not entries:
            tk.Label(self.rows_frame, text="Aucun mot de passe pour l'instant. Clique sur '+ Ajouter'.",
                     font=FONT, bg=BG, fg=FG_MUTED, pady=30).pack()
            return

        for entry_id, site, username, password_enc in entries:
            self._build_row(entry_id, site, username, password_enc)

        self._bind_mousewheel_recursive(self.rows_frame)

    def _build_row(self, entry_id, site, username, password_enc):
        row = tk.Frame(self.rows_frame, bg=BG_CARD, pady=8, padx=10)
        row.pack(fill="x", pady=3)

        site_lbl = tk.Label(row, text=site or "(sans nom)", font=FONT, bg=BG_CARD, fg=FG,
                             width=24, anchor="w")
        site_lbl.pack(side="left")
        site_lbl.bind("<Double-Button-1>", lambda e: self._edit_field(entry_id, "site", site))

        user_lbl = tk.Label(row, text=username or "(aucun)", font=FONT, bg=BG_CARD, fg=FG,
                             width=24, anchor="w")
        user_lbl.pack(side="left")
        user_lbl.bind("<Double-Button-1>", lambda e: self._edit_field(entry_id, "username", username))

        pwd_zone = tk.Frame(row, bg=BG_CARD)
        pwd_zone.pack(side="left", fill="x", expand=True)

        is_revealed = entry_id in self.revealed
        display_text = self._decrypt(password_enc) if is_revealed else "•" * 10

        pwd_lbl = tk.Label(pwd_zone, text=display_text, font=("Consolas", 10), bg=BG_CARD, fg=FG, anchor="w")
        pwd_lbl.pack(side="left")
        pwd_lbl.bind("<Double-Button-1>", lambda e: self._edit_field(entry_id, "password", self._decrypt(password_enc)))

        eye_btn = tk.Button(
            pwd_zone, text=("🙈" if is_revealed else "👁"), font=FONT, bg=BG_CARD, fg=FG_MUTED,
            relief="flat", cursor="hand2", bd=0,
            command=lambda: self._toggle_reveal(entry_id),
        )
        eye_btn.pack(side="left", padx=(10, 0))

        copy_btn = tk.Button(
            pwd_zone, text="📋", font=FONT, bg=BG_CARD, fg=FG_MUTED,
            relief="flat", cursor="hand2", bd=0,
            command=lambda: self._copy_password(password_enc),
        )
        copy_btn.pack(side="left", padx=(6, 0))

        del_btn = tk.Button(
            row, text="🗑", font=FONT, bg=BG_CARD, fg=DANGER,
            relief="flat", cursor="hand2", bd=0,
            command=lambda: self._delete(entry_id, site),
        )
        del_btn.pack(side="right")

    def _decrypt(self, password_enc: bytes) -> str:
        try:
            return self.app.fernet.decrypt(password_enc).decode("utf-8")
        except Exception:
            return "(erreur de déchiffrement)"

    def _toggle_reveal(self, entry_id):
        if entry_id in self.revealed:
            self.revealed.discard(entry_id)
        else:
            self.revealed.add(entry_id)
        self.refresh()

    def _copy_password(self, password_enc):
        plain = self._decrypt(password_enc)
        self.clipboard_clear()
        self.clipboard_append(plain)
        messagebox.showinfo("Copié", "Mot de passe copié dans le presse-papiers.")

    def _delete(self, entry_id, site):
        if messagebox.askyesno("Supprimer", f"Supprimer l'entrée « {site} » ?"):
            db.delete_entry(self.app.conn, entry_id)
            self.refresh()

    # -- dialogues ------------------------------------------------------ #
    def _edit_field(self, entry_id, field, current_value):
        labels = {"site": "le site", "username": "l'identifiant", "password": "le mot de passe"}
        dialog = tk.Toplevel(self, bg=BG_CARD)
        dialog.title(f"Modifier {labels[field]}")
        dialog.geometry("380x160")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text=f"Nouvelle valeur pour {labels[field]} :", font=FONT, bg=BG_CARD, fg=FG).pack(pady=(20, 8))

        show_char = "•" if field == "password" else ""
        var = tk.StringVar(value=current_value)
        entry = tk.Entry(dialog, textvariable=var, font=FONT, width=32, show=show_char,
                          bg="#33353f", fg=FG, insertbackground=FG, relief="flat")
        entry.pack(ipady=6, pady=4)
        entry.focus_set()
        entry.select_range(0, "end")

        def save():
            new_value = var.get()
            if field == "site":
                db.update_entry(self.app.conn, entry_id, site=new_value)
            elif field == "username":
                db.update_entry(self.app.conn, entry_id, username=new_value)
            elif field == "password":
                db.update_entry(self.app.conn, entry_id, password_enc=self.app.fernet.encrypt(new_value.encode("utf-8")))
            dialog.destroy()
            self.refresh()

        entry.bind("<Return>", lambda e: save())
        tk.Button(dialog, text="Enregistrer", font=FONT_BOLD, bg=ACCENT, fg="white",
                  relief="flat", padx=16, pady=6, cursor="hand2", command=save).pack(pady=14)

    def _open_add_dialog(self):
        dialog = tk.Toplevel(self, bg=BG_CARD)
        dialog.title("Ajouter un mot de passe")
        dialog.geometry("400x340")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Nouvelle entrée", font=FONT_TITLE, bg=BG_CARD, fg=FG).pack(pady=(20, 14))

        def labeled_entry(label_text, show=""):
            tk.Label(dialog, text=label_text, font=FONT, bg=BG_CARD, fg=FG, anchor="w").pack(fill="x", padx=40)
            e = tk.Entry(dialog, font=FONT, show=show, bg="#33353f", fg=FG, insertbackground=FG, relief="flat")
            e.pack(fill="x", padx=40, ipady=6, pady=(2, 12))
            return e

        site_entry = labeled_entry("Site (ex : github.com)")
        user_entry = labeled_entry("Identifiant / email")

        tk.Label(dialog, text="Mot de passe", font=FONT, bg=BG_CARD, fg=FG, anchor="w").pack(fill="x", padx=40)
        pwd_row = tk.Frame(dialog, bg=BG_CARD)
        pwd_row.pack(fill="x", padx=40, pady=(2, 4))
        pwd_entry = tk.Entry(pwd_row, font=FONT, bg="#33353f", fg=FG, insertbackground=FG, relief="flat")
        pwd_entry.pack(side="left", fill="x", expand=True, ipady=6)

        def fill_random():
            pwd_entry.delete(0, "end")
            pwd_entry.insert(0, generate_password())

        tk.Button(pwd_row, text="🎲 Générer", font=FONT, bg="#3a3c46", fg=FG, relief="flat",
                  cursor="hand2", command=fill_random).pack(side="left", padx=(8, 0))

        def save():
            site = site_entry.get().strip()
            username = user_entry.get().strip()
            password = pwd_entry.get()
            if not site or not password:
                messagebox.showwarning("Champs manquants", "Le site et le mot de passe sont obligatoires.")
                return
            enc = self.app.fernet.encrypt(password.encode("utf-8"))
            db.add_entry(self.app.conn, site, username, enc)
            dialog.destroy()
            self.refresh()

        tk.Button(dialog, text="Ajouter", font=FONT_BOLD, bg=ACCENT, fg="white",
                  relief="flat", padx=16, pady=8, cursor="hand2", command=save).pack(pady=18)

        site_entry.focus_set()

    def _open_import_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Depuis Google Chrome", command=self._import_chrome)
        menu.add_command(label="Depuis Microsoft Edge", command=self._import_edge)
        menu.add_separator()
        menu.add_command(label="Depuis un fichier CSV exporté...", command=self._import_csv)
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        menu.tk_popup(x, y)

    def _import_chrome(self):
        self._run_import("Chrome", browser_import.import_from_chrome)

    def _import_edge(self):
        self._run_import("Edge", browser_import.import_from_edge)

    def _run_import(self, label, func):
        try:
            creds = func()
        except browser_import.BrowserImportError as e:
            messagebox.showerror("Import impossible", str(e))
            return
        except Exception as e:
            messagebox.showerror("Import impossible", f"Erreur inattendue : {e}")
            return

        rows = [
            (c.site, c.username, self.app.fernet.encrypt(c.password.encode("utf-8")))
            for c in creds if c.password
        ]
        if not rows:
            messagebox.showinfo("Import", f"Aucun mot de passe récupérable trouvé dans {label}.")
            return
        db.add_entries_bulk(self.app.conn, rows)
        self.refresh()
        messagebox.showinfo("Import terminé", f"{len(rows)} mot(s) de passe importé(s) depuis {label}.")

    def _open_change_master_dialog(self):
        dialog = tk.Toplevel(self, bg=BG_CARD)
        dialog.title("Changer le mot de passe maître")
        dialog.geometry("400x340")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Changer le mot de passe maître", font=FONT_BOLD, bg=BG_CARD, fg=FG).pack(pady=(20, 14))

        def labeled_pwd(label_text):
            tk.Label(dialog, text=label_text, font=FONT, bg=BG_CARD, fg=FG, anchor="w").pack(fill="x", padx=40)
            e = tk.Entry(dialog, show="•", font=FONT, bg="#33353f", fg=FG, insertbackground=FG, relief="flat")
            e.pack(fill="x", padx=40, ipady=6, pady=(2, 10))
            return e

        old_entry = labeled_pwd("Mot de passe actuel")
        new_entry = labeled_pwd("Nouveau mot de passe")
        confirm_entry = labeled_pwd("Confirme le nouveau mot de passe")

        error_label = tk.Label(dialog, text="", font=FONT, bg=BG_CARD, fg=DANGER, wraplength=320)
        error_label.pack(pady=(4, 0))

        def save():
            old_pwd = old_entry.get()
            new_pwd = new_entry.get()
            confirm_pwd = confirm_entry.get()

            if len(new_pwd) < 6:
                error_label.config(text="Le nouveau mot de passe doit faire au moins 6 caractères.")
                return
            if new_pwd != confirm_pwd:
                error_label.config(text="Les deux nouveaux mots de passe ne correspondent pas.")
                return

            def reencrypt_cb(old_fernet, new_fernet):
                db.reencrypt_all(self.app.conn, old_fernet, new_fernet)

            ok = crypto_utils.change_master_password(old_pwd, new_pwd, CONFIG_PATH, reencrypt_cb)
            if not ok:
                error_label.config(text="Mot de passe actuel incorrect.")
                return

            # On recharge la nouvelle clé pour la session en cours.
            self.app.fernet = crypto_utils.unlock(new_pwd, CONFIG_PATH)
            dialog.destroy()
            messagebox.showinfo("Succès", "Mot de passe maître changé avec succès.")

        old_entry.bind("<Return>", lambda e: save())
        tk.Button(dialog, text="Valider", font=FONT_BOLD, bg=ACCENT, fg="white",
                  relief="flat", padx=16, pady=8, cursor="hand2", command=save).pack(pady=14)

        old_entry.focus_set()

    def _import_csv(self):
        path = filedialog.askopenfilename(title="Choisir le fichier CSV exporté", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            creds = browser_import.import_from_csv(path)
        except browser_import.BrowserImportError as e:
            messagebox.showerror("Import impossible", str(e))
            return

        rows = [
            (c.site, c.username, self.app.fernet.encrypt(c.password.encode("utf-8")))
            for c in creds if c.password
        ]
        if not rows:
            messagebox.showinfo("Import", "Aucune entrée valide trouvée dans ce fichier.")
            return
        db.add_entries_bulk(self.app.conn, rows)
        self.refresh()
        messagebox.showinfo("Import terminé", f"{len(rows)} mot(s) de passe importé(s) depuis le CSV.")
