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

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vrchat_session.cookies")
REQUEST_DELAY = 1.2  # seconds between API calls, be polite to VRChat's API

CONTENT_TAGS = [
    ("Sexually Suggestive", "content_sex"),
    ("Adult Language and Themes", "content_adult"),
    ("Graphic Violence", "content_violence"),
    ("Excessive Gore", "content_gore"),
    ("Extreme Horror", "content_horror"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VRChat Avatar Tagger")
        self.geometry("760x640")
        self.minsize(640, 480)

        self.api_client = None
        self.avatar_api = None
        self.all_avatars = []
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None

        self._build_login_frame()
        self._build_main_frame()
        self.main_frame.pack_forget()  # hidden until logged in

        self.after(100, self._poll_log_queue)

    # ---------- UI construction ----------

    def _build_login_frame(self):
        self.login_frame = ttk.Frame(self, padding=24)
        self.login_frame.pack(fill="both", expand=True)

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

        # --- Tag checkboxes ---
        tags_box = ttk.LabelFrame(self.main_frame, text="Content warning tags to apply", padding=8)
        tags_box.pack(fill="x", pady=4)
        self.tag_vars = {}
        for i, (label, api_value) in enumerate(CONTENT_TAGS):
            var = tk.BooleanVar(value=(api_value == "content_sex"))
            self.tag_vars[api_value] = var
            ttk.Checkbutton(tags_box, text=label, variable=var).grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=2)

        # --- Search + list ---
        list_box_frame = ttk.LabelFrame(self.main_frame, text="Select avatars", padding=8)
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

        # --- Options row ---
        options_row = ttk.Frame(self.main_frame)
        options_row.pack(fill="x", pady=4)
        self.dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row, text="Dry run (preview only, don't actually change anything)", variable=self.dry_run_var).pack(side="left")

        ttk.Label(options_row, text="   Limit:").pack(side="left")
        self.limit_var = tk.StringVar(value="")
        ttk.Entry(options_row, textvariable=self.limit_var, width=6).pack(side="left")
        ttk.Label(options_row, text="(blank = no limit)").pack(side="left", padx=(4, 0))

        # --- Run button ---
        run_row = ttk.Frame(self.main_frame)
        run_row.pack(fill="x", pady=4)
        self.run_button = ttk.Button(run_row, text="Apply Tags to Selected Avatars", command=self._on_run_click)
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

    # ---------- Run / tagging ----------

    def _on_run_click(self):
        selected_indices = self.avatar_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Nothing selected", "Select at least one avatar from the list first.")
            return
        chosen_tags = [v for v, var in self.tag_vars.items() if var.get()]
        if not chosen_tags:
            messagebox.showwarning("No tags chosen", "Check at least one content warning tag to apply.")
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

        self.run_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.stop_event.clear()
        self.progress.config(maximum=len(avatars_to_process), value=0)

        self.worker_thread = threading.Thread(
            target=self._tagging_worker, args=(avatars_to_process, chosen_tags, dry_run, limit), daemon=True
        )
        self.worker_thread.start()

    def _on_stop_click(self):
        self.stop_event.set()
        self._log("Stopping after the current avatar...")

    def _tagging_worker(self, avatars_to_process, chosen_tags, dry_run, limit):
        updated, skipped, failed = 0, 0, 0
        total = len(avatars_to_process)

        for i, avatar in enumerate(avatars_to_process, 1):
            if self.stop_event.is_set():
                self._log("Stopped by user.")
                break
            if limit is not None and updated >= limit:
                self._log(f"Reached limit of {limit}, stopping.")
                break

            existing_tags = set(avatar.tags or [])
            new_tags = existing_tags | set(chosen_tags)

            if new_tags == existing_tags:
                self._log(f"[{i}/{total}] {avatar.name} -- already tagged, skipping")
                skipped += 1
            else:
                self._log(f"[{i}/{total}] {avatar.name} -- adding {chosen_tags}")
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
                        updated += 1
                    except Exception as e:
                        self._log(f"    FAILED: {e}")
                        failed += 1
                else:
                    updated += 1
                time.sleep(REQUEST_DELAY)

            self.log_queue.put(("progress", i))

        summary = f"Done. Updated: {updated}, already tagged: {skipped}, failed: {failed}"
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
                elif kind == "finished":
                    self.run_button.config(state="normal")
                    self.stop_button.config(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)


if __name__ == "__main__":
    App().mainloop()
