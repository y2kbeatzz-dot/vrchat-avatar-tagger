#!/usr/bin/env python3
"""
vrchat-avatar-tagger -- desktop GUI

Requires: pip install vrchatapi --break-system-packages
(tkinter ships with the standard python.org installer on Windows/Mac already)

Run with:
  python3 tag_avatars_gui.py

or double-click run_gui.bat on Windows.
"""

import atexit
import http.cookiejar
import json
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time

import vrchatapi
from vrchatapi.api import authentication_api, avatars_api
from vrchatapi.exceptions import UnauthorizedException
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.models.update_avatar_request import UpdateAvatarRequest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(SCRIPT_DIR, "vrchat_session.cookies")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "tagger_progress.json")
BANNER_FILE = os.path.join(SCRIPT_DIR, "banner.png")
REQUEST_DELAY = 1.2  # seconds between API calls, be polite to VRChat's API

CONTENT_TAGS = [
    ("Sexually Suggestive", "content_sex"),
    ("Adult Language and Themes", "content_adult"),
    ("Graphic Violence", "content_violence"),
    ("Excessive Gore", "content_gore"),
    ("Extreme Horror", "content_horror"),
]


def _normalize_tag(raw):
    """Turn free-typed text into a plausible VRChat tag token."""
    return raw.strip().lower().replace(" ", "_")


def _run_key(tags, remove_mode):
    """Stable key identifying 'this exact bulk operation' for progress tracking."""
    action = "remove" if remove_mode else "add"
    return action + ":" + ",".join(sorted(tags))


LIGHT_THEME = {
    "bg": "#f0f0f0",
    "fg": "#000000",
    "field_bg": "#ffffff",
    "field_fg": "#000000",
    "select_bg": "#0078d7",
    "select_fg": "#ffffff",
    "accent": "#0a5",
}

DARK_THEME = {
    "bg": "#1e1e22",
    "fg": "#e6e6e6",
    "field_bg": "#2b2b30",
    "field_fg": "#e6e6e6",
    "select_bg": "#3a6fd8",
    "select_fg": "#ffffff",
    "accent": "#4fd48a",
}


class ProgressStore:
    """Tracks which avatars have already been successfully updated for a given
    bulk add/remove operation, persisted to disk so a run can be stopped
    (or the app closed/crashed) and resumed later without redoing work."""

    def __init__(self, path):
        self.path = path
        self.data = {}  # run_key -> list of avatar ids done
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def is_done(self, run_key, avatar_id):
        return avatar_id in self.data.get(run_key, [])

    def mark_done(self, run_key, avatar_id):
        ids = self.data.setdefault(run_key, [])
        if avatar_id not in ids:
            ids.append(avatar_id)
        self._save()

    def count_done(self, run_key):
        return len(self.data.get(run_key, []))

    def clear_all(self):
        self.data = {}
        self._save()


class TagEditorDialog(tk.Toplevel):
    """Popup to view/add/remove/fix the full tag list on a single avatar."""

    def __init__(self, parent, avatar, on_save, theme=None):
        super().__init__(parent)
        self.avatar = avatar
        self.on_save = on_save
        self.title(f"Edit tags -- {avatar.name}")
        self.geometry("420x420")
        self.transient(parent)
        self.grab_set()

        theme = theme or LIGHT_THEME
        self.configure(bg=theme["bg"])

        self.tags = list(avatar.tags or [])

        ttk.Label(self, text=avatar.name, font=("Segoe UI", 12, "bold")).pack(pady=(12, 4))
        ttk.Label(self, text="All tags currently on this avatar (content-warning\nand any other tags). Select one and remove it, or\ntype a new tag below to add it.", justify="center").pack(pady=(0, 8))

        list_frame = ttk.Frame(self, padding=(12, 0))
        list_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set, selectmode="extended",
            bg=theme["field_bg"], fg=theme["field_fg"],
            selectbackground=theme["select_bg"], selectforeground=theme["select_fg"],
            highlightthickness=0, relief="flat",
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)
        self._refresh_list()

        remove_row = ttk.Frame(self, padding=(12, 6))
        remove_row.pack(fill="x")
        ttk.Button(remove_row, text="Remove selected", command=self._remove_selected).pack(side="left")

        add_row = ttk.Frame(self, padding=(12, 0))
        add_row.pack(fill="x")
        ttk.Label(add_row, text="Add tag:").pack(side="left")
        self.new_tag_var = tk.StringVar()
        entry = ttk.Entry(add_row, textvariable=self.new_tag_var)
        entry.pack(side="left", fill="x", expand=True, padx=6)
        entry.bind("<Return>", lambda e: self._add_tag())
        ttk.Button(add_row, text="Add", command=self._add_tag).pack(side="left")

        btn_row = ttk.Frame(self, padding=12)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text="Save changes", command=self._save).pack(side="right")

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for t in self.tags:
            self.listbox.insert("end", t)

    def _remove_selected(self):
        selected = list(self.listbox.curselection())
        for i in reversed(selected):
            del self.tags[i]
        self._refresh_list()

    def _add_tag(self):
        raw = self.new_tag_var.get()
        tag = _normalize_tag(raw)
        if not tag:
            return
        if tag not in self.tags:
            self.tags.append(tag)
        self.new_tag_var.set("")
        self._refresh_list()

    def _save(self):
        self.destroy()
        self.on_save(self.avatar, self.tags)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VRChat Avatar Tagger")
        self.geometry("780x680")
        self.minsize(660, 500)

        self.api_client = None
        self.avatar_api = None
        self.all_avatars = []
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.progress_store = ProgressStore(PROGRESS_FILE)
        self.extra_tags = []  # custom tags added via the "add tag" box

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.dark_mode_var = tk.BooleanVar(value=False)

        self._build_login_frame()
        self._build_main_frame()
        self.main_frame.pack_forget()  # hidden until logged in

        self._apply_theme()
        self.after(100, self._poll_log_queue)

    # ---------- Theme ----------

    def _current_theme(self):
        return DARK_THEME if self.dark_mode_var.get() else LIGHT_THEME

    def _on_toggle_dark_mode(self):
        self._apply_theme()

    def _apply_theme(self):
        t = self._current_theme()
        self.configure(bg=t["bg"])

        for widget_style in ("TFrame", "TLabelframe", "TLabelframe.Label", "TLabel",
                              "TButton", "TCheckbutton", "TRadiobutton"):
            self.style.configure(widget_style, background=t["bg"], foreground=t["fg"])
        self.style.map("TButton", background=[("active", t["field_bg"])])
        self.style.map("TCheckbutton", background=[("active", t["bg"])], foreground=[("active", t["fg"])])
        self.style.map("TRadiobutton", background=[("active", t["bg"])], foreground=[("active", t["fg"])])

        self.style.configure("TEntry", fieldbackground=t["field_bg"], foreground=t["field_fg"],
                              insertcolor=t["field_fg"])
        self.style.configure("TProgressbar", background=t["accent"], troughcolor=t["field_bg"])

        # tk.Listbox and tk.Text don't follow ttk themes, so color them directly.
        # (Listbox has no insertbackground option -- only Text/Entry do -- so
        # these need separate configure() calls.)
        if hasattr(self, "avatar_listbox"):
            self.avatar_listbox.configure(
                bg=t["field_bg"], fg=t["field_fg"],
                selectbackground=t["select_bg"], selectforeground=t["select_fg"],
                highlightthickness=0,
            )
        if hasattr(self, "log_text"):
            self.log_text.configure(
                bg=t["field_bg"], fg=t["field_fg"],
                selectbackground=t["select_bg"], selectforeground=t["select_fg"],
                insertbackground=t["field_fg"], highlightthickness=0,
            )
        if hasattr(self, "custom_tags_label"):
            self.custom_tags_label.configure(foreground=t["accent"])
        if hasattr(self, "login_status"):
            self.login_status.configure(background=t["bg"])

    # ---------- UI construction ----------

    def _build_login_frame(self):
        self.login_frame = ttk.Frame(self, padding=24)
        self.login_frame.pack(fill="both", expand=True)

        top_row = ttk.Frame(self.login_frame)
        top_row.pack(fill="x")
        ttk.Checkbutton(
            top_row, text="Dark mode", variable=self.dark_mode_var, command=self._on_toggle_dark_mode
        ).pack(side="right")

        self._add_banner_if_available(self.login_frame)

        ttk.Label(self.login_frame, text="VRChat Avatar Tagger", font=("Segoe UI", 16, "bold")).pack(pady=(0, 16))

        form = ttk.Frame(self.login_frame)
        form.pack()

        ttk.Label(form, text="Username / Email:").grid(row=0, column=0, sticky="e", pady=4, padx=4)
        self.username_entry = ttk.Entry(form, width=32)
        self.username_entry.grid(row=0, column=1, pady=4, padx=4)

        ttk.Label(form, text="Password:").grid(row=1, column=0, sticky="e", pady=4, padx=4)
        self.password_entry = ttk.Entry(form, width=32, show="*")
        self.password_entry.grid(row=1, column=1, pady=4, padx=4)
        self.password_entry.bind("<Return>", lambda e: self._on_login_click())

        self.login_button = ttk.Button(self.login_frame, text="Log In", command=self._on_login_click)
        self.login_button.pack(pady=16)

        self.login_status = ttk.Label(self.login_frame, text="", foreground="#888")
        self.login_status.pack()

    def _build_main_frame(self):
        self.main_frame = ttk.Frame(self, padding=12)

        top = ttk.Frame(self.main_frame)
        top.pack(fill="x", pady=(0, 8))
        self.logged_in_label = ttk.Label(top, text="", font=("Segoe UI", 10, "bold"))
        self.logged_in_label.pack(side="left")
        ttk.Checkbutton(
            top, text="Dark mode", variable=self.dark_mode_var, command=self._on_toggle_dark_mode
        ).pack(side="right")

        # --- Tag checkboxes ---
        tags_box = ttk.LabelFrame(self.main_frame, text="Content warning tags", padding=8)
        tags_box.pack(fill="x", pady=4)

        mode_row = ttk.Frame(tags_box)
        mode_row.pack(fill="x", pady=(0, 6))
        self.action_var = tk.StringVar(value="add")
        ttk.Label(mode_row, text="Action:").pack(side="left")
        ttk.Radiobutton(mode_row, text="Add tags", variable=self.action_var, value="add").pack(side="left", padx=(6, 12))
        ttk.Radiobutton(mode_row, text="Remove tags", variable=self.action_var, value="remove").pack(side="left")

        self.tag_vars = {}
        checks_frame = ttk.Frame(tags_box)
        checks_frame.pack(fill="x")
        for i, (label, api_value) in enumerate(CONTENT_TAGS):
            var = tk.BooleanVar(value=(api_value == "content_sex"))
            self.tag_vars[api_value] = var
            ttk.Checkbutton(checks_frame, text=label, variable=var).grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=2)

        # --- Custom tags ---
        custom_row = ttk.Frame(tags_box)
        custom_row.pack(fill="x", pady=(8, 0))
        ttk.Label(custom_row, text="Custom tag:").pack(side="left")
        self.custom_tag_var = tk.StringVar()
        custom_entry = ttk.Entry(custom_row, textvariable=self.custom_tag_var, width=20)
        custom_entry.pack(side="left", padx=6)
        custom_entry.bind("<Return>", lambda e: self._add_custom_tag())
        ttk.Button(custom_row, text="+ Add", command=self._add_custom_tag).pack(side="left")
        self.custom_tags_label = ttk.Label(custom_row, text="", foreground="#0a5")
        self.custom_tags_label.pack(side="left", padx=(10, 0))
        ttk.Button(custom_row, text="Clear custom", command=self._clear_custom_tags).pack(side="left", padx=(10, 0))

        # --- Search + list ---
        list_box_frame = ttk.LabelFrame(self.main_frame, text="Select avatars (double-click one to edit its tags directly)", padding=8)
        list_box_frame.pack(fill="both", expand=True, pady=4)

        search_row = ttk.Frame(list_box_frame)
        search_row.pack(fill="x", pady=(0, 4))
        ttk.Label(search_row, text="Filter:").pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *a: self._refresh_avatar_list())
        ttk.Entry(search_row, textvariable=self.filter_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(search_row, text="Select All", command=lambda: self._select_all(True)).pack(side="left", padx=2)
        ttk.Button(search_row, text="Select None", command=lambda: self._select_all(False)).pack(side="left", padx=2)

        list_container = ttk.Frame(list_box_frame)
        list_container.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        self.avatar_listbox = tk.Listbox(
            list_container, selectmode="extended", yscrollcommand=scrollbar.set, activestyle="none"
        )
        self.avatar_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.avatar_listbox.yview)
        self.avatar_listbox.bind("<Double-Button-1>", self._on_avatar_double_click)

        # --- Options row ---
        options_row = ttk.Frame(self.main_frame)
        options_row.pack(fill="x", pady=4)
        self.dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row, text="Dry run (preview only, don't actually change anything)", variable=self.dry_run_var).pack(side="left")

        ttk.Label(options_row, text="   Limit:").pack(side="left")
        self.limit_var = tk.StringVar(value="")
        ttk.Entry(options_row, textvariable=self.limit_var, width=6).pack(side="left")
        ttk.Label(options_row, text="(blank = no limit)").pack(side="left", padx=(4, 0))

        # --- Resume / progress row ---
        resume_row = ttk.Frame(self.main_frame)
        resume_row.pack(fill="x", pady=(0, 4))
        self.resume_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            resume_row,
            text="Resume: skip avatars already updated in a previous run with the same tags/action",
            variable=self.resume_var,
        ).pack(side="left")
        ttk.Button(resume_row, text="Clear saved progress", command=self._on_clear_progress).pack(side="right")

        # --- Run button ---
        run_row = ttk.Frame(self.main_frame)
        run_row.pack(fill="x", pady=4)
        self.run_button = ttk.Button(run_row, text="Apply to Selected Avatars", command=self._on_run_click)
        self.run_button.pack(side="left")
        self.stop_button = ttk.Button(run_row, text="Stop", command=self._on_stop_click, state="disabled")
        self.stop_button.pack(side="left", padx=6)
        self.progress = ttk.Progressbar(run_row, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=8)

        # --- Log output ---
        log_frame = ttk.LabelFrame(self.main_frame, text="Log", padding=4)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side="right", fill="y")
        self.log_text = tk.Text(log_frame, height=10, yscrollcommand=log_scroll.set, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)
        log_scroll.config(command=self.log_text.yview)

    # ---------- Custom tags ----------

    def _add_custom_tag(self):
        tag = _normalize_tag(self.custom_tag_var.get())
        if not tag:
            return
        if tag not in self.extra_tags:
            self.extra_tags.append(tag)
        self.custom_tag_var.set("")
        self._refresh_custom_tags_label()

    def _clear_custom_tags(self):
        self.extra_tags = []
        self._refresh_custom_tags_label()

    def _refresh_custom_tags_label(self):
        if self.extra_tags:
            self.custom_tags_label.config(text="+ " + ", ".join(self.extra_tags))
        else:
            self.custom_tags_label.config(text="")

    def _chosen_tags(self):
        preset = [v for v, var in self.tag_vars.items() if var.get()]
        return preset + [t for t in self.extra_tags if t not in preset]

    def _add_banner_if_available(self, parent, target_width=560):
        """Show banner.png at the top of the given frame, scaled to target_width.
        Uses plain tkinter (no Pillow dependency) -- silently skipped if the
        file is missing or the image fails to load, so this never crashes the app."""
        if not os.path.exists(BANNER_FILE):
            return
        try:
            img = tk.PhotoImage(file=BANNER_FILE)
            factor = max(1, round(img.width() / target_width))
            if factor > 1:
                img = img.subsample(factor, factor)
            self.banner_image = img  # keep a reference so it isn't garbage-collected
            ttk.Label(parent, image=img).pack(pady=(0, 12))
        except Exception:
            pass

    # ---------- Login ----------

    def _on_login_click(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning("Missing info", "Please enter both username and password.")
            return
        self.login_button.config(state="disabled")
        self.login_status.config(text="Logging in...")
        self.update_idletasks()
        try:
            self.api_client = self._do_login(username, password)
        except Exception as e:
            self.login_status.config(text=f"Login failed: {e}")
            self.login_button.config(state="normal")
            return

        self.avatar_api = avatars_api.AvatarsApi(self.api_client)
        self.login_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self._fetch_avatars_async()

    def _do_login(self, username, password):
        configuration = vrchatapi.Configuration(username=username, password=password)
        # The vrchatapi library aggressively validates that fields aren't None,
        # but VRChat's real API frequently omits fields (e.g. an avatar with no
        # image), which otherwise crashes the library entirely. Must be set as
        # the *global default* config since deserialized models pull from there.
        configuration.client_side_validation = False
        vrchatapi.Configuration.set_default(configuration)

        api_client = vrchatapi.ApiClient(configuration)
        api_client.user_agent = "vrchat-avatar-tagger-gui/1.0 (github.com/USERNAME/vrchat-avatar-tagger)"

        cookie_jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)
        if os.path.exists(COOKIE_FILE):
            try:
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
            except Exception:
                pass
        api_client.rest_client.cookie_jar = cookie_jar

        def save_session():
            try:
                cookie_jar.save(ignore_discard=True, ignore_expires=True)
            except Exception:
                pass

        atexit.register(save_session)

        auth_api = authentication_api.AuthenticationApi(api_client)
        try:
            current_user = auth_api.get_current_user()
        except UnauthorizedException as e:
            if e.status == 200:
                if "Email" in str(e.reason):
                    code = simpledialog.askstring("Email 2FA", "Enter the code emailed to you:", parent=self)
                    if not code:
                        raise RuntimeError("2FA code entry cancelled")
                    auth_api.verify2_fa_email_code(TwoFactorEmailCode(code=code.strip()))
                else:
                    code = simpledialog.askstring("Authenticator 2FA", "Enter your authenticator code:", parent=self)
                    if not code:
                        raise RuntimeError("2FA code entry cancelled")
                    auth_api.verify2_fa(TwoFactorAuthCode(code=code.strip()))
                current_user = auth_api.get_current_user()
            else:
                raise RuntimeError(f"{e.reason} (status {e.status})")

        save_session()
        self.logged_in_label.config(text=f"Logged in as {current_user.display_name}")
        return api_client

    # ---------- Avatar list ----------

    def _fetch_avatars_async(self):
        self.login_status.config(text="")
        self._log(f"Fetching your avatars...")

        def worker():
            avatars = []
            offset = 0
            page_size = 100
            while True:
                page = self.avatar_api.search_avatars(user="me", n=page_size, offset=offset, release_status="all")
                if not page:
                    break
                avatars.extend(page)
                offset += page_size
                time.sleep(REQUEST_DELAY)
            self.all_avatars = avatars
            self.log_queue.put(("avatars_loaded", None))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_avatar_list(self):
        query = self.filter_var.get().strip().lower()
        self.avatar_listbox.delete(0, "end")
        self._visible_avatars = [
            a for a in self.all_avatars if query in (a.name or "").lower()
        ]
        for a in self._visible_avatars:
            tag_note = ", ".join(a.tags or []) or "no tags"
            self.avatar_listbox.insert("end", f"{a.name}   [{tag_note}]")

    def _select_all(self, select):
        if select:
            self.avatar_listbox.select_set(0, "end")
        else:
            self.avatar_listbox.select_clear(0, "end")

    # ---------- Per-avatar tag editor ----------

    def _on_avatar_double_click(self, event):
        selected_indices = self.avatar_listbox.curselection()
        if not selected_indices:
            return
        avatar = self._visible_avatars[selected_indices[0]]
        TagEditorDialog(self, avatar, self._apply_single_avatar_edit, theme=self._current_theme())

    def _apply_single_avatar_edit(self, avatar, new_tags):
        old_tags = set(avatar.tags or [])
        new_tags_set = set(new_tags)
        if new_tags_set == old_tags:
            self._log(f"{avatar.name} -- no changes made.")
            return

        added = new_tags_set - old_tags
        removed = old_tags - new_tags_set
        change_desc = []
        if added:
            change_desc.append(f"+{', '.join(sorted(added))}")
        if removed:
            change_desc.append(f"-{', '.join(sorted(removed))}")
        change_text = " ".join(change_desc)

        # This dialog's Save button is an explicit, already-reviewed single edit,
        # so it always applies for real -- it deliberately ignores the bulk-run
        # "Dry run" checkbox (previously it obeyed that checkbox, which meant
        # nothing happened here whenever Dry run was left checked, the default).
        if not messagebox.askyesno(
            "Confirm tag change",
            f"Apply this change to {avatar.name}?\n\n{change_text}",
        ):
            self._log(f"{avatar.name} -- edit cancelled.")
            return

        self._log(f"{avatar.name} -- {change_text}")

        def worker():
            try:
                self.avatar_api.update_avatar(
                    avatar.id,
                    update_avatar_request=UpdateAvatarRequest(
                        tags=list(new_tags_set),
                        unity_version=None,
                        version=None,
                    ),
                )
                avatar.tags = list(new_tags_set)
                self.log_queue.put(("log", f"  Saved changes to {avatar.name}."))
                self.log_queue.put(("avatars_loaded", None))
            except Exception as e:
                self.log_queue.put(("log", f"  FAILED to save {avatar.name}: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Run / bulk tagging ----------

    def _on_clear_progress(self):
        if messagebox.askyesno(
            "Clear saved progress",
            "This clears the record of which avatars were already updated in past runs. "
            "The next run with 'Resume' checked will no longer skip anything. Continue?",
        ):
            self.progress_store.clear_all()
            self._log("Saved progress cleared.")

    def _on_run_click(self):
        selected_indices = self.avatar_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Nothing selected", "Select at least one avatar from the list first.")
            return
        chosen_tags = self._chosen_tags()
        if not chosen_tags:
            messagebox.showwarning("No tags chosen", "Check at least one content warning tag or add a custom tag to apply.")
            return

        limit_text = self.limit_var.get().strip()
        limit = None
        if limit_text:
            try:
                limit = int(limit_text)
            except ValueError:
                messagebox.showwarning("Invalid limit", "Limit must be a whole number, or left blank.")
                return

        avatars_to_process = [self._visible_avatars[i] for i in selected_indices]
        dry_run = self.dry_run_var.get()
        remove_mode = self.action_var.get() == "remove"
        resume = self.resume_var.get()

        self.run_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.stop_event.clear()
        self.progress.config(maximum=len(avatars_to_process), value=0)

        self.worker_thread = threading.Thread(
            target=self._tagging_worker,
            args=(avatars_to_process, chosen_tags, dry_run, limit, remove_mode, resume),
            daemon=True,
        )
        self.worker_thread.start()

    def _on_stop_click(self):
        self.stop_event.set()
        self._log("Stopping after the current avatar... progress so far is saved.")

    def _tagging_worker(self, avatars_to_process, chosen_tags, dry_run, limit, remove_mode, resume):
        updated, skipped, failed, resumed_skip = 0, 0, 0, 0
        total = len(avatars_to_process)
        action_word = "removing" if remove_mode else "adding"
        run_key = _run_key(chosen_tags, remove_mode)

        if resume and not dry_run:
            already = self.progress_store.count_done(run_key)
            if already:
                self._log(f"Resume is on: {already} avatar(s) already done for this exact tag/action combo will be skipped.")

        for i, avatar in enumerate(avatars_to_process, 1):
            if self.stop_event.is_set():
                self._log("Stopped by user.")
                break
            if limit is not None and updated >= limit:
                self._log(f"Reached limit of {limit}, stopping.")
                break

            if resume and not dry_run and self.progress_store.is_done(run_key, avatar.id):
                resumed_skip += 1
                self.log_queue.put(("progress", i))
                continue

            existing_tags = set(avatar.tags or [])
            if remove_mode:
                new_tags = existing_tags - set(chosen_tags)
            else:
                new_tags = existing_tags | set(chosen_tags)

            if new_tags == existing_tags:
                reason = "doesn't have this tag" if remove_mode else "already tagged"
                self._log(f"[{i}/{total}] {avatar.name} -- {reason}, skipping")
                skipped += 1
                if not dry_run:
                    self.progress_store.mark_done(run_key, avatar.id)
            else:
                self._log(f"[{i}/{total}] {avatar.name} -- {action_word} {chosen_tags}")
                if not dry_run:
                    try:
                        self.avatar_api.update_avatar(
                            avatar.id,
                            update_avatar_request=UpdateAvatarRequest(
                                tags=list(new_tags),
                                unity_version=None,  # library defaults this to '5.3.4p1' unless
                                version=None,        # overridden, which makes VRChat's API think
                                                      # we're updating asset files and reject the request.
                            ),
                        )
                        avatar.tags = list(new_tags)
                        updated += 1
                        self.progress_store.mark_done(run_key, avatar.id)
                    except Exception as e:
                        self._log(f"    FAILED: {e}")
                        failed += 1
                else:
                    updated += 1
                time.sleep(REQUEST_DELAY)

            self.log_queue.put(("progress", i))

        summary = f"Done. Updated: {updated}, already tagged: {skipped}, failed: {failed}"
        if resumed_skip:
            summary += f", skipped (resumed from earlier run): {resumed_skip}"
        if dry_run:
            summary += " (dry run, nothing was actually changed)"
        self._log(summary)
        self.log_queue.put(("finished", None))

    # ---------- Logging / thread-safe UI updates ----------

    def _log(self, message):
        self.log_queue.put(("log", message))

    def _poll_log_queue(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "log":
                    self.log_text.config(state="normal")
                    self.log_text.insert("end", payload + "\n")
                    self.log_text.see("end")
                    self.log_text.config(state="disabled")
                elif kind == "avatars_loaded":
                    self._refresh_avatar_list()
                    self._log(f"Found {len(self.all_avatars)} avatars.")
                elif kind == "progress":
                    self.progress.config(value=payload)
                    self._refresh_avatar_list()
                elif kind == "finished":
                    self.run_button.config(state="normal")
                    self.stop_button.config(state="disabled")
                    self._refresh_avatar_list()
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)


if __name__ == "__main__":
    App().mainloop()
