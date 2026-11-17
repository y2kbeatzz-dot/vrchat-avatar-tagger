#!/usr/bin/env python3
"""VRChat Avatar Tagger — polished, cross-platform Qt desktop application.

The UI stays on the main thread. VRChat HTTP requests happen in background QThreads.
"""
import sys
import threading
import time

from PySide6.QtCore import Qt, QThread, Signal, QUrl, QItemSelectionModel
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QCheckBox, QComboBox,
    QSpinBox, QProgressBar, QPlainTextEdit, QListWidget, QDialog,
    QDialogButtonBox, QInputDialog, QMessageBox, QScrollArea, QSizePolicy
)

from app_paths import resource_file
from tagger_core import (
    CONTENT_TAGS, DATA_DIR, REQUEST_DELAY, ProgressStore, authenticate,
    create_session, fetch_owned_avatars, normalize_tag, operation_key,
    update_avatar_tags
)
from vrchatapi.api import avatars_api

REPO_URL = "https://github.com/y2kbeatzz-dot/vrchat-avatar-tagger"
WEBSITE_URL = "https://y2kbeatzz-dot.github.io/vrchat-avatar-tagger/"
VERSION = "1.5.0"


def named_label(text, style="muted"):
    result = QLabel(text)
    result.setObjectName(style)
    result.setWordWrap(True)
    return result


def button(text, style="secondary", callback=None):
    result = QPushButton(text)
    result.setObjectName(style)
    result.setCursor(Qt.PointingHandCursor)
    result.setMinimumHeight(40)
    if callback:
        result.clicked.connect(callback)
    return result


def layout_panel(layout, style="panel"):
    result = QFrame()
    result.setObjectName(style)
    result.setLayout(layout)
    return result


def skin(light=False):
    c = dict(
        bg="#f5f6fc" if light else "#090d19",
        sidebar="#edf0f8" if light else "#101528",
        panel="#ffffff" if light else "#161b30",
        surface="#f7f8fc" if light else "#1d233c",
        border="#dce1ee" if light else "#323958",
        text="#20243b" if light else "#f7f5ff",
        muted="#747b96" if light else "#a6aecb",
        selected="#eee7ff" if light else "#30254f",
        accent="#7645da" if light else "#b893ff",
        hover="#e9e3fa" if light else "#2d3351",
        warning="#b42e67" if light else "#ff84b5",
    )
    return """
        QWidget { background: %(bg)s; color: %(text)s; font-family: "SF Pro Text", "Segoe UI", Arial, sans-serif; font-size: 13px; }
        QMainWindow, QStackedWidget, QScrollArea { background: %(bg)s; }
        QFrame#sidebar { background: %(sidebar)s; border-right: 1px solid %(border)s; }
        QFrame#panel, QFrame#stat, QFrame#loginPanel { background: %(panel)s; border: 1px solid %(border)s; border-radius: 17px; }
        QFrame#heroPanel { background: %(selected)s; border: 1px solid %(border)s; border-radius: 17px; }
        QLabel { background: transparent; }
        QLabel#title { font-size: 30px; font-weight: 800; }
        QLabel#pageTitle { font-size: 24px; font-weight: 800; }
        QLabel#sectionTitle { font-size: 17px; font-weight: 750; }
        QLabel#statValue { font-size: 28px; font-weight: 800; color: %(accent)s; }
        QLabel#brand { font-size: 17px; font-weight: 850; }
        QLabel#eyebrow { color: %(accent)s; font-size: 11px; font-weight: 800; }
        QLabel#muted, QLabel#hint { color: %(muted)s; }
        QLabel#success { color: #52d9a3; font-weight: 700; }
        QLabel#warning { color: %(warning)s; }
        QPushButton { background: %(surface)s; color: %(text)s; padding: 9px 14px; border: 1px solid %(border)s; border-radius: 10px; font-weight: 650; }
        QPushButton:hover { background: %(hover)s; border-color: %(accent)s; }
        QPushButton:disabled { color: %(muted)s; }
        QPushButton#primary { background: #9664e9; color: white; border: 1px solid #b08af8; font-weight: 750; }
        QPushButton#primary:hover { background: #ac80fa; }
        QPushButton#danger { color: %(warning)s; }
        QPushButton#nav { background: transparent; border: 0; text-align: left; padding: 13px 16px; font-size: 14px; }
        QPushButton#nav[active="true"] { background: %(selected)s; border-left: 3px solid %(accent)s; font-weight: 800; }
        QPushButton#nav:hover { background: %(hover)s; }
        QLineEdit, QComboBox, QSpinBox { background: %(surface)s; border: 1px solid %(border)s; border-radius: 10px; padding: 9px 12px; selection-background-color: #8655dc; }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: %(accent)s; }
        QComboBox::drop-down { border: 0; width: 24px; }
        QComboBox QAbstractItemView { background: %(panel)s; selection-background-color: %(selected)s; border: 1px solid %(border)s; }
        QCheckBox { background: transparent; spacing: 8px; padding: 4px 0; }
        QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid %(muted)s; border-radius: 5px; background: %(surface)s; }
        QCheckBox::indicator:checked { background: #9970ef; border-color: #9970ef; }
        QTableWidget { background: %(panel)s; alternate-background-color: %(surface)s; border: 0; gridline-color: transparent; selection-background-color: %(selected)s; selection-color: %(text)s; outline: none; }
        QTableWidget::item { padding: 7px; border-bottom: 1px solid %(border)s; }
        QHeaderView::section { background: %(surface)s; color: %(muted)s; border: 0; border-bottom: 1px solid %(border)s; padding: 12px 9px; font-weight: 750; }
        QListWidget, QPlainTextEdit { background: %(surface)s; border: 1px solid %(border)s; border-radius: 11px; padding: 10px; selection-background-color: %(selected)s; }
        QListWidget::item { padding: 7px 4px; }
        QProgressBar { border: 1px solid %(border)s; background: %(surface)s; height: 15px; text-align: center; border-radius: 7px; }
        QProgressBar::chunk { background: #a680f8; border-radius: 6px; }
        QScrollArea { border: 0; }
    """ % c


class LoginWorker(QThread):
    success = Signal(object, object, str)
    need_code = Signal(str)
    error = Signal(str)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password
        self._code_event = threading.Event()
        self._code = ""

    def submit_code(self, code):
        self._code = code
        self._code_event.set()

    def run(self):
        try:
            client, save = create_session(self.username, self.password)
            self.password = ""
            def request_code(method):
                self.need_code.emit(method)
                if not self._code_event.wait(180):
                    raise RuntimeError("2FA timed out; please sign in again.")
                return self._code
            user = authenticate(client, request_code)
            save()
            self.success.emit(client, avatars_api.AvatarsApi(client), str(user.display_name))
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")


class FetchWorker(QThread):
    success = Signal(object)
    error = Signal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api
        self.cancelled = threading.Event()

    def run(self):
        try:
            result = fetch_owned_avatars(self.api, self.cancelled.is_set)
            if not self.cancelled.is_set():
                self.success.emit(result)
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")


class TagWorker(QThread):
    event = Signal(str)
    progress = Signal(int, int)
    changed = Signal(str, object)
    complete = Signal(object)

    def __init__(self, api, avatars, tags, remove, preview, resume, limit, store):
        super().__init__()
        self.api, self.avatars, self.tags = api, list(avatars), set(tags)
        self.remove, self.preview, self.resume = remove, preview, resume
        self.limit, self.store = limit, store
        self.cancelled = threading.Event()

    def run(self):
        counts = {"updated": 0, "unchanged": 0, "failed": 0, "resumed": 0}
        key = operation_key(self.tags, self.remove)
        total = len(self.avatars)
        for index, avatar in enumerate(self.avatars, 1):
            if self.cancelled.is_set():
                self.event.emit("Stopped after the current request.")
                break
            if self.limit and counts["updated"] >= self.limit:
                self.event.emit(f"Reached limit of {self.limit} updates.")
                break
            avatar_id = str(avatar.id)
            old = set(avatar.tags or [])
            new = old - self.tags if self.remove else old | self.tags
            if self.resume and not self.preview and self.store.done(key, avatar_id):
                counts["resumed"] += 1
            elif new == old:
                counts["unchanged"] += 1
                if not self.preview:
                    self.store.mark(key, avatar_id)
            elif self.preview:
                counts["updated"] += 1
                self.event.emit(f"PREVIEW  {avatar.name}: {'remove' if self.remove else 'add'} {', '.join(sorted(self.tags))}")
            else:
                try:
                    update_avatar_tags(self.api, avatar.id, new)
                    avatar.tags = sorted(new)
                    self.changed.emit(avatar_id, sorted(new))
                    self.store.mark(key, avatar_id)
                    counts["updated"] += 1
                    self.event.emit(f"UPDATED  {avatar.name}")
                except Exception as exc:
                    counts["failed"] += 1
                    self.event.emit(f"FAILED  {avatar.name}: {type(exc).__name__}: {exc}")
                time.sleep(REQUEST_DELAY)
            self.progress.emit(index, total)
        self.complete.emit(counts)


class SingleEditWorker(QThread):
    success = Signal(str, object)
    error = Signal(str)

    def __init__(self, api, avatar_id, tags):
        super().__init__()
        self.api, self.avatar_id, self.tags = api, avatar_id, list(tags)

    def run(self):
        try:
            update_avatar_tags(self.api, self.avatar_id, self.tags)
            self.success.emit(str(self.avatar_id), self.tags)
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")


class TagDialog(QDialog):
    def __init__(self, avatar, parent=None):
        super().__init__(parent)
        self.avatar = avatar
        self.setWindowTitle("Edit avatar tags")
        self.setMinimumSize(470, 480)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)
        root.addWidget(named_label("SINGLE AVATAR  /  EDIT TAGS", "eyebrow"))
        name = named_label(str(avatar.name), "pageTitle")
        root.addWidget(name)
        root.addWidget(named_label("Select a tag to remove it or add one below. Only this avatar will change."))
        self.items = QListWidget()
        self.items.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.items.addItems(sorted(set(avatar.tags or [])))
        root.addWidget(self.items, 1)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a new tag")
        self.input.returnPressed.connect(self.add)
        row.addWidget(self.input, 1)
        row.addWidget(button("Add", callback=self.add))
        root.addLayout(row)
        root.addWidget(button("Remove selected", "danger", self.remove))
        controls = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        root.addWidget(controls)

    def add(self):
        tag = normalize_tag(self.input.text())
        if tag and not self.items.findItems(tag, Qt.MatchExactly):
            self.items.addItem(tag)
        self.input.clear()

    def remove(self):
        for item in self.items.selectedItems():
            self.items.takeItem(self.items.row(item))

    def tags(self):
        return [self.items.item(i).text() for i in range(self.items.count())]


class TaggerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VRChat Avatar Tagger")
        self.resize(1260, 820)
        self.setMinimumSize(980, 640)
        self.setWindowIcon(QIcon(resource_file("app-icon.png")))
        self.setStyleSheet(skin())
        self.api = None
        self.client = None
        self.avatars = []
        self.filtered = []
        self.selected_avatar_ids = set()
        self.store = ProgressStore()
        self.workers = []
        self.running = False
        self.light = False
        self.logged_in_name = ""
        self._build_ui()

    def _worker(self, worker):
        self.workers.append(worker)
        worker.finished.connect(lambda: self.workers.remove(worker) if worker in self.workers else None)
        worker.start()

    def _build_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self._make_login()
        self._make_workspace()
        self.stack.setCurrentIndex(0)

    def _make_login(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(30, 24, 30, 24)
        outer.addStretch()
        center = QHBoxLayout()
        center.addStretch()
        body = QVBoxLayout()
        body.setContentsMargins(38, 34, 38, 34)
        body.setSpacing(16)
        logo = QLabel()
        logo.setPixmap(QIcon(resource_file("app-icon.png")).pixmap(72, 72))
        body.addWidget(logo, 0, Qt.AlignHCenter)
        title = named_label("AVATAR TAGGER", "title")
        title.setAlignment(Qt.AlignCenter)
        body.addWidget(title)
        subtitle = named_label("Your VRChat avatar workspace. Organized, fast, and built for creators.")
        subtitle.setAlignment(Qt.AlignCenter)
        body.addWidget(subtitle)
        body.addSpacing(13)
        body.addWidget(named_label("VRCHAT USERNAME OR EMAIL", "eyebrow"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("Your VRChat username")
        body.addWidget(self.username)
        body.addWidget(named_label("PASSWORD", "eyebrow"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("VRChat password")
        self.password.returnPressed.connect(self.login)
        body.addWidget(self.password)
        self.login_btn = button("Sign in to VRChat  →", "primary", self.login)
        body.addWidget(self.login_btn)
        self.login_status = named_label("Connect securely using your VRChat credentials.", "hint")
        self.login_status.setAlignment(Qt.AlignCenter)
        body.addWidget(self.login_status)
        body.addSpacing(8)
        link = button("Visit the project website", callback=lambda: QDesktopServices.openUrl(QUrl(WEBSITE_URL)))
        body.addWidget(link)
        login_panel = layout_panel(body, "loginPanel")
        login_panel.setFixedWidth(460)
        center.addWidget(login_panel)
        center.addStretch()
        outer.addLayout(center)
        outer.addStretch()
        self.stack.addWidget(page)

    def _make_workspace(self):
        page = QWidget()
        root = QHBoxLayout(page)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 25, 18, 22)
        side.setSpacing(13)
        brand = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QIcon(resource_file("app-icon.png")).pixmap(45, 45))
        brand.addWidget(icon)
        brand.addWidget(named_label("AVATAR\nTAGGER", "brand"))
        side.addLayout(brand)
        side.addSpacing(21)
        side.addWidget(named_label("WORKSPACE", "eyebrow"))
        self.nav_buttons = []
        for index, title in enumerate(("◈  Avatars", "▤  Activity", "◌  About")):
            nav = button(title, "nav", lambda checked=False, i=index: self.change_page(i))
            nav.setProperty("active", index == 0)
            self.nav_buttons.append(nav)
            side.addWidget(nav)
        side.addStretch()
        self.side_status = named_label("●  Not connected", "muted")
        side.addWidget(self.side_status)
        side.addWidget(named_label("FREE · OPEN SOURCE · v" + VERSION, "hint"))
        side.addWidget(button("☼  Toggle theme", callback=self.toggle_theme))
        side.addWidget(button("Open website ↗", callback=lambda: QDesktopServices.openUrl(QUrl(WEBSITE_URL))))
        root.addWidget(sidebar)
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        self._make_avatars_page()
        self._make_activity_page()
        self._make_about_page()
        self.stack.addWidget(page)

    def change_page(self, index):
        self.pages.setCurrentIndex(index)
        for i, nav in enumerate(self.nav_buttons):
            nav.setProperty("active", i == index)
            nav.style().unpolish(nav)
            nav.style().polish(nav)

    def _make_avatars_page(self):
        page = QWidget()
        all_layout = QVBoxLayout(page)
        all_layout.setContentsMargins(25, 25, 25, 25)
        all_layout.setSpacing(17)
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(named_label("YOUR COLLECTION", "eyebrow"))
        title_col.addWidget(named_label("Avatar workspace", "pageTitle"))
        title_col.addWidget(named_label("Search, select, and tag your own avatars."))
        header.addLayout(title_col, 1)
        self.refresh_btn = button("↻  Refresh avatars", callback=self.refresh)
        header.addWidget(self.refresh_btn)
        all_layout.addLayout(header)
        stats = QHBoxLayout()
        self.total_stat, self.selected_stat, self.tagged_stat = (
            named_label("0", "statValue"), named_label("0", "statValue"), named_label("0", "statValue")
        )
        for label, value in (("AVATARS", self.total_stat), ("SELECTED", self.selected_stat), ("WITH WARNINGS", self.tagged_stat)):
            cell = QVBoxLayout()
            cell.setContentsMargins(17, 13, 17, 13)
            cell.setSpacing(4)
            cell.addWidget(named_label(label, "eyebrow"))
            cell.addWidget(value)
            stats.addWidget(layout_panel(cell, "stat"), 1)
        all_layout.addLayout(stats)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)
        left = QVBoxLayout()
        left.setContentsMargins(19, 18, 19, 18)
        left.setSpacing(11)
        left.addWidget(named_label("AVATAR LIBRARY", "eyebrow"))
        search = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("⌕  Search avatars by name or tag...")
        self.search.textChanged.connect(self.render_avatars)
        search.addWidget(self.search, 1)
        search.addWidget(button("Select visible", callback=self.select_visible))
        search.addWidget(button("Clear", callback=self.clear_selection))
        left.addLayout(search)
        self.library = QTableWidget(0, 3)
        self.library.setHorizontalHeaderLabels(["AVATAR NAME", "CURRENT TAGS", "ID"])
        self.library.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.library.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.library.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.library.setAlternatingRowColors(True)
        self.library.verticalHeader().hide()
        self.library.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.library.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.library.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.library.itemSelectionChanged.connect(self.selection_changed)
        self.library.itemDoubleClicked.connect(lambda _: self.edit_selected())
        left.addWidget(self.library, 1)
        self.library_hint = named_label("Sign in to load your avatars.")
        left.addWidget(self.library_hint)
        actions_layout.addWidget(layout_panel(left), 5)
        right = QVBoxLayout()
        right.setContentsMargins(18, 17, 18, 17)
        right.setSpacing(9)
        right.addWidget(named_label("BULK ACTIONS", "eyebrow"))
        right.addWidget(named_label("Tag studio", "sectionTitle"))
        right.addWidget(named_label("Choose exactly what to change. Existing unrelated tags stay untouched."))
        self.mode = QComboBox()
        self.mode.addItems(["＋  Add selected tags", "－  Remove selected tags"])
        right.addWidget(self.mode)
        right.addWidget(named_label("CONTENT WARNINGS", "eyebrow"))
        self.tag_checks = {}
        for label, value in CONTENT_TAGS:
            check = QCheckBox(label)
            check.setChecked(value == "content_sex")
            self.tag_checks[value] = check
            right.addWidget(check)
        right.addSpacing(4)
        right.addWidget(named_label("CUSTOM TAG", "eyebrow"))
        custom_row = QHBoxLayout()
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("e.g. fantasy")
        self.custom_input.returnPressed.connect(self.add_custom)
        custom_row.addWidget(self.custom_input, 1)
        custom_row.addWidget(button("Add", callback=self.add_custom))
        right.addLayout(custom_row)
        self.custom_tags = []
        self.custom_view = named_label("No custom tags", "hint")
        right.addWidget(self.custom_view)
        right.addWidget(button("Clear custom tags", callback=self.clear_custom))
        right.addSpacing(6)
        self.dry = QCheckBox("Dry run · preview changes only")
        self.dry.setChecked(True)
        right.addWidget(self.dry)
        self.resume = QCheckBox("Resume previous operation")
        self.resume.setChecked(True)
        right.addWidget(self.resume)
        limit_row = QHBoxLayout()
        limit_row.addWidget(named_label("Update limit (0 = all)"))
        self.limit = QSpinBox()
        self.limit.setRange(0, 999999)
        self.limit.setValue(0)
        limit_row.addWidget(self.limit)
        right.addLayout(limit_row)
        self.run_btn = button("Preview selected avatars →", "primary", self.start_bulk)
        right.addWidget(self.run_btn)
        self.dry.toggled.connect(lambda value: self.run_btn.setText("Preview selected avatars →" if value else "Apply tags to selected →"))
        right.addWidget(button("Edit one avatar's tags", callback=self.edit_selected))
        right.addStretch()
        actions_layout.addWidget(layout_panel(right), 2)
        all_layout.addLayout(actions_layout, 1)
        footer = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        footer.addWidget(self.progress, 1)
        self.progress_label = named_label("Ready")
        footer.addWidget(self.progress_label)
        self.stop_btn = button("Stop", "danger", self.stop_run)
        self.stop_btn.setEnabled(False)
        footer.addWidget(self.stop_btn)
        all_layout.addLayout(footer)
        self.pages.addWidget(page)

    def _make_activity_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(12)
        lay.addWidget(named_label("ACTION HISTORY", "eyebrow"))
        lay.addWidget(named_label("Activity & progress", "pageTitle"))
        lay.addWidget(named_label("Review progress, preview changes, successful updates, and request errors."))
        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setPlainText("Your activity will show here after signing in.\n")
        lay.addWidget(self.activity, 1)
        row = QHBoxLayout()
        row.addWidget(button("Clear activity view", callback=self.activity.clear))
        row.addWidget(button("Clear saved resume records", "danger", self.clear_progress))
        row.addStretch()
        lay.addLayout(row)
        self.pages.addWidget(page)

    def _make_about_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(18)
        outer.addWidget(named_label("ABOUT THE PROJECT", "eyebrow"))
        outer.addWidget(named_label("Designed for creators.", "pageTitle"))
        msg = QVBoxLayout()
        msg.setContentsMargins(25, 25, 25, 25)
        msg.setSpacing(14)
        msg.addWidget(named_label("VRChat Avatar Tagger · " + VERSION, "sectionTitle"))
        msg.addWidget(named_label("Bulk manage the content-warning and custom tags on your own VRChat avatars. Fast selection, searchable lists, per-avatar editing, cautious previews and resumable operations."))
        msg.addWidget(named_label("Local data: " + str(DATA_DIR)))
        msg.addWidget(named_label("Unofficial community project. Not affiliated with VRChat. Always preview changes before applying them."))
        msg.addWidget(button("Official website ↗", callback=lambda: QDesktopServices.openUrl(QUrl(WEBSITE_URL))))
        msg.addWidget(button("GitHub repository ↗", callback=lambda: QDesktopServices.openUrl(QUrl(REPO_URL))))
        outer.addWidget(layout_panel(msg))
        outer.addStretch()
        self.pages.addWidget(page)

    def toggle_theme(self):
        self.light = not self.light
        self.setStyleSheet(skin(self.light))

    def login(self):
        user, password = self.username.text().strip(), self.password.text()
        if not user or not password:
            self.login_status.setText("Please enter your username and password.")
            return
        self.login_btn.setEnabled(False)
        self.login_status.setText("Connecting to VRChat…")
        worker = LoginWorker(user, password)
        worker.need_code.connect(lambda method, w=worker: self.prompt_2fa(method, w))
        worker.success.connect(self.signed_in)
        worker.error.connect(self.login_failed)
        self._worker(worker)

    def prompt_2fa(self, method, worker):
        label = ("Enter the verification code from your email:" if method == "email"
                 else "Enter your authenticator app's one-time code:")
        code, accepted = QInputDialog.getText(self, "VRChat two-factor verification", label)
        worker.submit_code(code.strip() if accepted else "")

    def signed_in(self, client, avatar_api, display_name):
        self.client, self.api, self.logged_in_name = client, avatar_api, display_name
        self.password.clear()
        self.login_status.setText("Connected successfully.")
        self.stack.setCurrentIndex(1)
        self.side_status.setText("●  " + display_name)
        self._event("Signed in as " + display_name)
        self.refresh()

    def login_failed(self, message):
        self.login_btn.setEnabled(True)
        self.login_status.setText("Sign-in failed. See the error dialog.")
        QMessageBox.warning(self, "Could not sign in", message)

    def refresh(self):
        if self.api is None or self.running:
            return
        self.refresh_btn.setEnabled(False)
        self.library_hint.setText("Loading your avatars from VRChat…")
        worker = FetchWorker(self.api)
        worker.success.connect(self.avatars_loaded)
        worker.error.connect(self.fetch_failed)
        self._worker(worker)

    def avatars_loaded(self, avatars):
        self.avatars = list(avatars)
        self.selected_avatar_ids.clear()
        self.refresh_btn.setEnabled(True)
        self.total_stat.setText(str(len(self.avatars)))
        self.tagged_stat.setText(str(sum(bool(set(a.tags or []) & {v for _, v in CONTENT_TAGS}) for a in self.avatars)))
        self._event(f"Loaded {len(self.avatars)} avatar(s).")
        self.render_avatars()

    def fetch_failed(self, message):
        self.refresh_btn.setEnabled(True)
        self.library_hint.setText("Avatar loading failed.")
        self._event("ERROR  Could not load avatars: " + message)
        QMessageBox.warning(self, "Could not load avatars", message)

    def render_avatars(self):
        if not hasattr(self, "library"):
            return
        needle = self.search.text().strip().lower()
        self.filtered = [a for a in self.avatars
                         if needle in str(a.name or "").lower() or
                         needle in " ".join(a.tags or []).lower()]
        self.library.blockSignals(True)
        self.library.setRowCount(len(self.filtered))
        for row, avatar in enumerate(self.filtered):
            tags = list(avatar.tags or [])
            for col, value in enumerate((str(avatar.name or "Unnamed avatar"),
                                         ", ".join(tags[:4]) + ("  +" + str(len(tags)-4) if len(tags)>4 else "") if tags else "No tags",
                                         str(avatar.id))):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.library.setItem(row, col, item)
            self.library.setRowHeight(row, 54)
            if str(avatar.id) in self.selected_avatar_ids:
                index = self.library.model().index(row, 0)
                self.library.selectionModel().select(
                    index, QItemSelectionModel.Select | QItemSelectionModel.Rows
                )
        self.library.blockSignals(False)
        self.library_hint.setText(f"Showing {len(self.filtered)} of {len(self.avatars)} avatars · Double-click to edit tags")
        self.selected_stat.setText(str(len(self.selected_avatar_ids)))

    def selection_changed(self):
        current_visible = {str(self.filtered[i.row()].id) for i in self.library.selectionModel().selectedRows()
                           if i.row() < len(self.filtered)}
        # Preserve selections hidden by the search filter.
        visible_ids = {str(a.id) for a in self.filtered}
        self.selected_avatar_ids.difference_update(visible_ids)
        self.selected_avatar_ids.update(current_visible)
        self.selected_stat.setText(str(len(self.selected_avatar_ids)))

    def select_visible(self):
        self.selected_avatar_ids.update(str(a.id) for a in self.filtered)
        self.library.selectAll()
        self.selected_stat.setText(str(len(self.selected_avatar_ids)))

    def clear_selection(self):
        self.selected_avatar_ids.clear()
        self.library.clearSelection()
        self.selected_stat.setText("0")

    def add_custom(self):
        tag = normalize_tag(self.custom_input.text())
        if tag and tag not in self.custom_tags:
            self.custom_tags.append(tag)
        self.custom_input.clear()
        self.custom_view.setText(", ".join(self.custom_tags) if self.custom_tags else "No custom tags")

    def clear_custom(self):
        self.custom_tags.clear()
        self.custom_view.setText("No custom tags")

    def tags_to_use(self):
        return set(self.custom_tags) | {value for value, box in self.tag_checks.items() if box.isChecked()}

    def start_bulk(self):
        if self.running:
            return
        selected = [a for a in self.avatars if str(a.id) in self.selected_avatar_ids]
        if not selected:
            QMessageBox.information(self, "No avatars selected", "Select one or more avatars first.")
            return
        tags = self.tags_to_use()
        if not tags:
            QMessageBox.information(self, "No tags selected", "Choose a warning tag or add a custom tag.")
            return
        preview = self.dry.isChecked()
        remove = self.mode.currentIndex() == 1
        if not preview:
            description = "REMOVE" if remove else "ADD"
            approved = QMessageBox.question(
                self, "Confirm avatar updates",
                f"{description} {len(tags)} tag(s) across {len(selected)} selected avatar(s)?\n\n"
                "This changes your VRChat account. Unrelated tags will be preserved.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if approved != QMessageBox.Yes:
                return
        self.running = True
        self.run_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setRange(0, len(selected))
        self.progress.setValue(0)
        self.change_page(1)
        self._event(f"{'PREVIEW' if preview else 'APPLY'} started for {len(selected)} avatars.")
        worker = TagWorker(self.api, selected, tags, remove, preview,
                           self.resume.isChecked(), self.limit.value(), self.store)
        self.tag_worker = worker
        worker.event.connect(self._event)
        worker.progress.connect(self.update_progress)
        worker.changed.connect(self.avatar_changed)
        worker.complete.connect(lambda counts, is_preview=preview: self.bulk_complete(counts, is_preview))
        self._worker(worker)

    def stop_run(self):
        if self.running and hasattr(self, "tag_worker"):
            self.tag_worker.cancel()
            self._event("Stop requested. The current request will finish.")

    def update_progress(self, index, total):
        self.progress.setMaximum(total)
        self.progress.setValue(index)
        self.progress_label.setText(f"{index}/{total}")

    def avatar_changed(self, avatar_id, tags):
        for avatar in self.avatars:
            if str(avatar.id) == avatar_id:
                avatar.tags = list(tags)
                break

    def bulk_complete(self, counts, preview):
        self.running = False
        self.run_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.tagged_stat.setText(str(sum(bool(set(a.tags or []) & {v for _, v in CONTENT_TAGS}) for a in self.avatars)))
        self.render_avatars()
        self._event(("Preview finished" if preview else "Update finished") +
                    f" · changed: {counts['updated']}, unchanged: {counts['unchanged']}, " +
                    f"resumed: {counts['resumed']}, failed: {counts['failed']}")
        self.progress_label.setText("Preview done" if preview else "Done")

    def edit_selected(self):
        if self.running:
            return
        selected = [a for a in self.avatars if str(a.id) in self.selected_avatar_ids]
        if len(selected) != 1:
            QMessageBox.information(self, "Select one avatar", "Select exactly one avatar to edit its tags.")
            return
        avatar = selected[0]
        dialog = TagDialog(avatar, self)
        if dialog.exec() != QDialog.Accepted:
            return
        tags = dialog.tags()
        if set(tags) == set(avatar.tags or []):
            return
        if QMessageBox.question(self, "Confirm single-avatar edit",
                                f"Save {len(tags)} tag(s) for {avatar.name} on VRChat?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.running = True
        self.run_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        worker = SingleEditWorker(self.api, avatar.id, tags)
        def saved(avatar_id, saved_tags):
            self.avatar_changed(avatar_id, saved_tags)
            self._event(f"Saved tags for {avatar.name}.")
            self.running = False
            self.run_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.render_avatars()
        def failed(message):
            self.running = False
            self.run_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self._event("ERROR  Single-avatar update failed: " + message)
            QMessageBox.warning(self, "Save failed", message)
        worker.success.connect(saved)
        worker.error.connect(failed)
        self._worker(worker)

    def clear_progress(self):
        if QMessageBox.question(self, "Clear resume history",
                                "Clear locally saved progress records? This does not change avatar tags.",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.store.clear()
            self._event("Saved resume history cleared.")

    def _event(self, message):
        stamp = time.strftime("%H:%M:%S")
        self.activity.appendPlainText(f"[{stamp}]  {message}")

    def closeEvent(self, event):
        if self.running:
            QMessageBox.information(self, "Operation in progress",
                "Stop the current operation before closing so progress is preserved.")
            event.ignore()
            return
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VRChat Avatar Tagger")
    app.setOrganizationName("VRChat Avatar Tagger")
    app.setWindowIcon(QIcon(resource_file("app-icon.png")))
    win = TaggerApp()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
