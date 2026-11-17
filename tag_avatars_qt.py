#!/usr/bin/env python3
"""VRChat Avatar Tagger — polished, cross-platform Qt desktop application.

The UI stays on the main thread. VRChat HTTP requests happen in background QThreads.
"""
import sys
import threading
import time
import traceback

from PySide6.QtCore import Qt, QThread, Signal, QUrl, QItemSelectionModel, QSize, QTimer
from PySide6.QtGui import QIcon, QDesktopServices, QPainter, QColor, QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QCheckBox, QComboBox,
    QSpinBox, QProgressBar, QPlainTextEdit, QListWidget, QDialog,
    QDialogButtonBox, QInputDialog, QMessageBox, QScrollArea, QSizePolicy,
    QStyledItemDelegate, QStyle, QSplitter
)

from app_paths import resource_file
from tagger_core import (
    CONTENT_TAGS, DATA_DIR, REQUEST_DELAY, ProgressStore, authenticate,
    create_session, fetch_owned_avatars, normalize_tag, operation_key,
    update_avatar_tags, friendly_login_error
)
from vrchatapi.api import avatars_api

REPO_URL = "https://github.com/y2kbeatzz-dot/vrchat-avatar-tagger"
WEBSITE_URL = "https://y2kbeatzz-dot.github.io/vrchat-avatar-tagger/"
CREATOR_NAME = "Ksyusha (Ксюша)"
CREATOR_PROFILE_URL = "https://guns.lol/life999"
VERSION = "1.5.5"


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
        QFrame#heroPanel { background: %(selected)s; border: 1px solid %(border)s; border-radius: 20px; }
        QFrame#glassCard { background: %(surface)s; border: 1px solid %(border)s; border-radius: 16px; }
        QLabel#heroTitle { font-size: 38px; font-weight: 900; color: %(text)s; }
        QLabel#heroHint { color: %(muted)s; font-size: 14px; }
        QLabel#pill { color: %(accent)s; background: %(selected)s; border: 1px solid %(border)s; border-radius: 11px; padding: 7px 12px; font-weight: 750; }
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
        QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #9866ed,stop:1 #db74bc); color: white; border: 1px solid #ba93f7; font-weight: 800; }
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
        QTableWidget { background: %(panel)s; alternate-background-color: %(surface)s; border: 0; gridline-color: transparent; selection-background-color: %(selected)s; selection-color: %(text)s; outline: none; }
        QTableWidget::item { padding: 7px; border-bottom: 1px solid %(border)s; }
        QHeaderView::section { background: %(surface)s; color: %(muted)s; border: 0; border-bottom: 1px solid %(border)s; padding: 12px 9px; font-weight: 750; }
        QListWidget, QPlainTextEdit { background: %(surface)s; border: 1px solid %(border)s; border-radius: 11px; padding: 10px; selection-background-color: %(selected)s; }
        QListWidget::item { padding: 7px 4px; }
        QProgressBar { border: 1px solid %(border)s; background: %(surface)s; height: 15px; text-align: center; border-radius: 7px; }
        QProgressBar::chunk { background: #a680f8; border-radius: 6px; }
        QScrollArea { border: 0; }
    """ % c



class AvatarRowDelegate(QStyledItemDelegate):
    """Avatar monograms and readable tag chips using native Qt painting.

    Keeps the table's selection, scrolling and keyboard navigation intact.
    """

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        selected = bool(option.state & QStyle.State_Selected)
        light = bool(self.parent().property("lightMode"))
        row_bg = "#e9e4fb" if light else "#2b2546"
        base_bg = "#ffffff" if light else "#151b30"
        alternate_bg = "#f5f6fc" if light else "#191e33"
        painter.fillRect(option.rect, QColor(row_bg if selected else
                                             (alternate_bg if index.row() % 2 else base_bg)))
        r = option.rect.adjusted(12, 7, -9, -7)
        text = str(index.data() or "")
        main = QColor("#22213c" if light else "#f7f4ff")
        secondary = QColor("#6c7390" if light else "#a5aecb")
        if index.column() == 0:
            icon = r.adjusted(0, 7, 0, -7)
            icon.setWidth(36)
            icon.setHeight(36)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#8950d9" if selected else "#573b91"))
            painter.drawRoundedRect(icon, 11, 11)
            initial = text[:1].upper() or "A"
            painter.setPen(QColor("#ffffff"))
            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(icon, Qt.AlignCenter, initial)
            painter.setPen(main)
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            name_rect = r.adjusted(49, 0, 0, 0)
            painter.drawText(name_rect, Qt.AlignVCenter | Qt.AlignLeft,
                             painter.fontMetrics().elidedText(text, Qt.ElideRight, name_rect.width()))
        elif index.column() == 1:
            tags = index.data(Qt.UserRole) or []
            if not tags:
                painter.setPen(secondary)
                painter.drawText(r, Qt.AlignVCenter | Qt.AlignLeft, "— No tags yet")
            else:
                x, center_y = r.left(), r.center().y()
                font = QFont()
                font.setPointSize(9)
                font.setBold(True)
                painter.setFont(font)
                available = r.right()
                for idx, tag in enumerate(tags):
                    width = min(185, painter.fontMetrics().horizontalAdvance(tag) + 24)
                    if x + width > available - 24:
                        rest = len(tags) - idx
                        if x + 35 < available:
                            painter.setPen(secondary)
                            painter.drawText(x + 6, center_y + 5, f"+{rest}")
                        break
                    color = "#f87dbb" if tag.startswith("content_") else "#76dbe9"
                    fill = "#572846" if tag.startswith("content_") else "#214556"
                    if light:
                        color = "#913265" if tag.startswith("content_") else "#16677a"
                        fill = "#ffe1f0" if tag.startswith("content_") else "#def9fc"
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(fill))
                    painter.drawRoundedRect(x, center_y - 13, width, 26, 11, 11)
                    painter.setPen(QColor(color))
                    painter.drawText(x + 12, center_y + 5, tag)
                    x += width + 8
        else:
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            painter.setPen(secondary)
            painter.drawText(r, Qt.AlignVCenter | Qt.AlignLeft,
                             painter.fontMetrics().elidedText(text, Qt.ElideMiddle, r.width()))
        painter.setPen(QColor("#333a55" if not light else "#e4e7f0"))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(100, 62)


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
            self.error.emit(friendly_login_error(exc))


class FetchWorker(QThread):
    page_received = Signal(object, int)
    success = Signal(object)
    error = Signal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api
        self.cancelled = threading.Event()

    def run(self):
        try:
            result = fetch_owned_avatars(
                self.api,
                stopped=self.cancelled.is_set,
                on_page=lambda page, total: self.page_received.emit(page, total),
                cancel_event=self.cancelled,
            )
            if not self.cancelled.is_set():
                self.success.emit(result)
        except Exception as exc:
            if not self.cancelled.is_set():
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
            if new == old:
                counts["unchanged"] += 1
                # Resume history must never skip an avatar whose tags now differ.
                if self.resume and self.store.done(key, avatar_id):
                    counts["resumed"] += 1
            elif self.preview:
                counts["updated"] += 1
                self.event.emit(f"PREVIEW  {avatar.name}: {'remove' if self.remove else 'add'} {', '.join(sorted(self.tags))}")
            else:
                try:
                    confirmed = update_avatar_tags(self.api, avatar.id, new)
                    avatar.tags = confirmed
                    self.changed.emit(avatar_id, confirmed)
                    self.store.mark(key, avatar_id)
                    counts["updated"] += 1
                    self.event.emit(f"CONFIRMED BY VRCHAT  {avatar.name}")
                except Exception as exc:
                    counts["failed"] += 1
                    self.event.emit(f"FAILED  {avatar.name}: {type(exc).__name__}: {exc}")
                if index < total and not self.cancelled.is_set():
                    self.event.emit("Pausing between writes to respect VRChat's request limits…")
                    self.cancelled.wait(REQUEST_DELAY)
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
            confirmed = update_avatar_tags(self.api, self.avatar_id, self.tags)
            self.success.emit(str(self.avatar_id), confirmed)
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
        try:
            tag = normalize_tag(self.input.text())
        except ValueError as exc:
            QMessageBox.information(self, "Choose a content warning checkbox", str(exc))
            return
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
        self.setMinimumSize(890, 620)
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
        self.fetch_worker = None
        self._closing_requested = False
        self._avatar_render_timer = QTimer(self)
        self._avatar_render_timer.setSingleShot(True)
        self._avatar_render_timer.setInterval(180)
        self._avatar_render_timer.timeout.connect(self.render_avatars)
        self.light = False
        self.logged_in_name = ""
        self._build_ui()
        self._install_shortcuts()
        self.statusBar().showMessage(
            "Ready · Ctrl/⌘+F to search · Ctrl/⌘+1/2/3 to switch pages"
        )

    def _install_shortcuts(self):
        """Accessible native keyboard commands for macOS and Windows."""
        self.shortcuts = []
        for sequence, callback in (
            ("Ctrl+F", self.focus_search),
            ("Ctrl+R", self.refresh),
            ("Ctrl+1", lambda: self.workspace_page(0)),
            ("Ctrl+2", lambda: self.workspace_page(1)),
            ("Ctrl+3", lambda: self.workspace_page(2)),
            ("Ctrl+Shift+L", self.toggle_theme),
            ("F1", lambda: self.workspace_page(2)),
            ("Escape", self.clear_search),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

    def workspace_page(self, index):
        if self.stack.currentIndex() == 1:
            self.change_page(index)

    def focus_search(self):
        if self.stack.currentIndex() == 1:
            self.change_page(0)
            self.search.setFocus()
            self.search.selectAll()

    def clear_search(self):
        if self.stack.currentIndex() == 1 and self.pages.currentIndex() == 0 and self.search.hasFocus():
            self.search.clear()

    def _worker(self, worker):
        """Keep QThread objects alive until finished, even during window close."""
        if self._closing_requested:
            return
        self.workers.append(worker)
        worker.finished.connect(lambda w=worker: self._worker_finished(w))
        worker.start()

    def _worker_finished(self, worker):
        if worker is self.fetch_worker:
            self.fetch_worker = None
            if not self._closing_requested:
                self.refresh_btn.setEnabled(True)
        if worker in self.workers:
            self.workers.remove(worker)
        if self._closing_requested and not any(w.isRunning() for w in self.workers):
            # Close on the next UI event, after the last worker has finished.
            QTimer.singleShot(0, self.close)

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
        center.setSpacing(26)
        welcome = QVBoxLayout()
        welcome.setContentsMargins(35, 38, 35, 38)
        welcome.setSpacing(19)
        welcome.addWidget(named_label("DESIGNED BY KSYUSHA (КСЮША)", "eyebrow"))
        welcome.addSpacing(15)
        welcome.addWidget(named_label("YOUR AVATARS.\nYOUR RULES.", "heroTitle"))
        welcome.addWidget(named_label(
            "A better way to organize your VRChat collection. "
            "Search every avatar, build tag sets, preview edits, and apply changes with confidence.",
            "heroHint"
        ))
        welcome.addSpacing(16)
        for item in (
            "✦  Manage content warnings in bulk",
            "◈  Find avatars without the endless scrolling",
            "◎  Preview before anything changes",
            "↺  Resume long sessions right where you left off",
        ):
            welcome.addWidget(named_label(item, "sectionTitle"))
        welcome.addStretch()
        welcome.addWidget(named_label("VRCHAT AVATAR TAGGER  •  V" + VERSION, "eyebrow"))
        welcome_panel = layout_panel(welcome, "heroPanel")
        center.addWidget(welcome_panel, 1)
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
        self.login_btn = button("Continue to your avatars  →", "primary", self.login)
        body.addWidget(self.login_btn)
        self.login_status = named_label("No account password is saved by the app.", "hint")
        self.login_status.setAlignment(Qt.AlignCenter)
        body.addWidget(self.login_status)
        body.addSpacing(8)
        link = button("Visit the project website", callback=lambda: QDesktopServices.openUrl(QUrl(WEBSITE_URL)))
        body.addWidget(link)
        login_panel = layout_panel(body, "loginPanel")
        login_panel.setFixedWidth(460)
        center.addWidget(login_panel)
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
        sidebar.setFixedWidth(200)
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
        all_layout.setContentsMargins(18, 16, 18, 14)
        all_layout.setSpacing(11)
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(named_label("YOUR COLLECTION", "eyebrow"))
        title_col.addWidget(named_label("Avatar workspace", "pageTitle"))
        title_col.addWidget(named_label("Search, select, and tag your own avatars."))
        header.addLayout(title_col, 1)
        self.refresh_btn = button("↻  Refresh avatars", callback=self.refresh)
        self.refresh_btn.setToolTip("Reload your own avatars from VRChat (Ctrl/⌘+R)")
        header.addWidget(self.refresh_btn)
        all_layout.addLayout(header)
        hero = QHBoxLayout()
        hero.setContentsMargins(14, 9, 14, 9)
        hero_col = QVBoxLayout()
        hero_col.setSpacing(5)
        hero_col.addWidget(named_label("CREATOR CONTROL CENTER", "eyebrow"))
        hero_col.addWidget(named_label("Every avatar. One organized workspace.", "sectionTitle"))
        hero_col.addWidget(named_label("Pick your collection, choose tags, preview your changes."))
        hero.addLayout(hero_col, 1)
        self.mode_pill = named_label("●  PREVIEW-FIRST WORKFLOW", "pill")
        hero.addWidget(self.mode_pill, 0, Qt.AlignVCenter)
        all_layout.addWidget(layout_panel(hero, "heroPanel"))

        stats = QHBoxLayout()
        self.total_stat, self.selected_stat, self.tagged_stat = (
            named_label("0", "statValue"), named_label("0", "statValue"), named_label("0", "statValue")
        )
        for label, value in (("AVATARS", self.total_stat), ("SELECTED", self.selected_stat), ("WITH WARNINGS", self.tagged_stat)):
            cell = QVBoxLayout()
            cell.setContentsMargins(12, 9, 12, 9)
            cell.setSpacing(4)
            cell.addWidget(named_label(label, "eyebrow"))
            cell.addWidget(value)
            stats.addWidget(layout_panel(cell, "stat"), 1)
        all_layout.addLayout(stats)
        actions_layout = QSplitter(Qt.Horizontal)
        actions_layout.setChildrenCollapsible(False)
        actions_layout.setHandleWidth(8)
        actions_layout.setOpaqueResize(False)
        left = QVBoxLayout()
        left.setContentsMargins(19, 18, 19, 18)
        left.setSpacing(11)
        left.addWidget(named_label("AVATAR LIBRARY", "eyebrow"))
        search = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("⌕  Search avatars by name or tag...  (Ctrl/⌘+F)")
        self.search.textChanged.connect(self.render_avatars)
        search.addWidget(self.search, 1)
        search.addWidget(button("Select visible", callback=self.select_visible))
        search.addWidget(button("Clear", callback=self.clear_selection))
        left.addLayout(search)
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.filter_mode = QComboBox()
        self.filter_mode.addItems(["All avatars", "With content warnings", "Without content warnings", "Has any tags", "Untagged"])
        self.filter_mode.currentIndexChanged.connect(self.render_avatars)
        filters.addWidget(named_label("SHOW", "eyebrow"))
        filters.addWidget(self.filter_mode, 1)
        filters.addStretch(1)
        left.addLayout(filters)
        self.library = QTableWidget(0, 3)
        self.library.setHorizontalHeaderLabels(["AVATAR NAME", "TAGS", "AVATAR ID"])
        self.library.setItemDelegate(AvatarRowDelegate(self.library))
        self.library.setShowGrid(False)
        self.library.setWordWrap(False)
        self.library.setProperty("lightMode", False)
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
        self.library.setToolTip("Select multiple avatars, or double-click one to edit its tags.")
        left.addWidget(self.library, 1)
        self.library_hint = named_label("Sign in to load your avatars.")
        left.addWidget(self.library_hint)
        library_panel = layout_panel(left)
        library_panel.setMinimumWidth(320)
        actions_layout.addWidget(library_panel)
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
            check.setChecked(False)
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
        right.addWidget(named_label("Preview never uploads. Apply asks for confirmation and sends to VRChat.", "hint"))
        self.resume = QCheckBox("Use saved resume history")
        self.resume.setChecked(True)
        right.addWidget(self.resume)
        limit_row = QHBoxLayout()
        limit_row.addWidget(named_label("Update limit (0 = all)"))
        self.limit = QSpinBox()
        self.limit.setRange(0, 999999)
        self.limit.setValue(0)
        limit_row.addWidget(self.limit)
        right.addLayout(limit_row)
        self.preview_btn = button("Preview changes (no upload)", callback=lambda: self.start_bulk(preview=True))
        self.preview_btn.setToolTip("Shows pending changes locally. Does not contact VRChat to update tags.")
        right.addWidget(self.preview_btn)
        self.run_btn = button("Apply tags to VRChat  →", "primary", callback=lambda: self.start_bulk(preview=False))
        self.run_btn.setToolTip("Apply selected tags to VRChat after explicit confirmation.")
        right.addWidget(self.run_btn)
        right.addWidget(button("Edit one avatar's tags", callback=self.edit_selected))
        right.addStretch()
        # Keep the tag studio accessible on smaller notebook displays.
        studio_scroll = QScrollArea()
        studio_scroll.setWidgetResizable(True)
        studio_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        studio_scroll.setMinimumWidth(285)
        studio_scroll.setWidget(layout_panel(right))
        actions_layout.addWidget(studio_scroll)
        actions_layout.setStretchFactor(0, 5)
        actions_layout.setStretchFactor(1, 3)
        actions_layout.setSizes([640, 330])
        self.workspace_splitter = actions_layout
        all_layout.addWidget(actions_layout, 1)
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
        activity_header = QHBoxLayout()
        self.activity_progress = QProgressBar()
        self.activity_progress.setRange(0, 100)
        self.activity_progress.setValue(0)
        activity_header.addWidget(self.activity_progress, 1)
        self.activity_status = named_label("Waiting for an operation")
        activity_header.addWidget(self.activity_status)
        lay.addLayout(activity_header)
        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setPlainText("Your activity will show here after signing in.\n")
        lay.addWidget(self.activity, 1)
        row = QHBoxLayout()
        row.addWidget(button("← Back to avatars", callback=lambda: self.change_page(0)))
        row.addWidget(button("Clear activity view", callback=self.activity.clear))
        row.addWidget(button("Clear saved resume records", "danger", self.clear_progress))
        row.addStretch()
        lay.addLayout(row)
        self.pages.addWidget(page)

    def _make_about_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(10)

        root.addWidget(named_label("MEET THE CREATOR", "eyebrow"))
        root.addWidget(named_label("Made by " + CREATOR_NAME, "pageTitle"))
        root.addWidget(named_label(
            "A small project built to make managing VRChat avatars easier, "
            "without opening and editing each avatar one by one."
        ))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 16, 12, 14)
        body.setSpacing(15)

        story = QVBoxLayout()
        story.setContentsMargins(22, 21, 22, 21)
        story.setSpacing(12)
        story.addWidget(named_label("THE STORY", "eyebrow"))
        story.addWidget(named_label("Why I made Avatar Tagger", "sectionTitle"))
        story.addWidget(named_label(
            "Keeping a lot of VRChat avatars organized can get repetitive, especially "
            "when the same content-warning tags need updating across multiple avatars. "
            "Avatar Tagger was made to turn those repeated steps into one clear workflow: "
            "find your avatars, choose tags, preview what will change, and apply the edits you want."
        ))
        story.addWidget(named_label(
            "The goal is to save creators time while keeping control of each change. "
            "That is why the app includes dry-run previews, individual avatar editing, "
            "stop controls, and the ability to resume a longer session."
        ))
        body.addWidget(layout_panel(story, "heroPanel"))

        build = QVBoxLayout()
        build.setContentsMargins(22, 21, 22, 21)
        build.setSpacing(11)
        build.addWidget(named_label("BEHIND THE APP", "eyebrow"))
        build.addWidget(named_label("How it was made", "sectionTitle"))
        build.addWidget(named_label(
            "Built in Python with the community VRChat API wrapper for account and "
            "avatar management. The desktop interface uses Qt (PySide6), while "
            "PyInstaller packages the Windows and macOS apps. GitHub Actions creates "
            "the downloadable releases; macOS uses custom drag-to-Applications DMGs "
            "and Windows uses a branded setup installer."
        ))
        build.addWidget(named_label(
            "The project is free and open source, with features and design evolving "
            "to make the app simpler to use."
        ))
        body.addWidget(layout_panel(build))

        creator = QVBoxLayout()
        creator.setContentsMargins(22, 21, 22, 21)
        creator.setSpacing(10)
        creator.addWidget(named_label("CONNECT", "eyebrow"))
        creator.addWidget(named_label(CREATOR_NAME, "sectionTitle"))
        creator.addWidget(named_label("Creator of VRChat Avatar Tagger"))
        creator.addWidget(button(
            "Visit my profiles ↗",
            "primary",
            lambda: QDesktopServices.openUrl(QUrl(CREATOR_PROFILE_URL))
        ))
        creator.addWidget(button(
            "Project website ↗",
            callback=lambda: QDesktopServices.openUrl(QUrl(WEBSITE_URL))
        ))
        creator.addWidget(button(
            "Source code on GitHub ↗",
            callback=lambda: QDesktopServices.openUrl(QUrl(REPO_URL))
        ))
        body.addWidget(layout_panel(creator))

        note = named_label(
            "VRChat Avatar Tagger v" + VERSION + " · Unofficial community project, "
            "not affiliated with VRChat. Your VRChat session and resume data "
            "are stored locally at " + str(DATA_DIR),
            "hint"
        )
        body.addWidget(note)
        body.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        self.pages.addWidget(page)

    def toggle_theme(self):
        self.light = not self.light
        self.library.setProperty("lightMode", self.light)
        self.setStyleSheet(skin(self.light))
        self.library.viewport().update()

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
        self.statusBar().showMessage("Signed in as " + display_name + " · Select avatars to begin")
        self._event("Welcome back to your avatar workspace.")
        self._event("Signed in as " + display_name)
        self.refresh()

    def login_failed(self, message):
        self.login_btn.setEnabled(True)
        tls_problem = message.startswith("Secure connection to VRChat could not be verified.")
        self.login_status.setText(
            "Secure connection blocked — check your network's certificates."
            if tls_problem else "Sign-in failed. See the error dialog."
        )
        self.statusBar().showMessage(
            "VRChat certificate not trusted · Connection cancelled safely."
            if tls_problem else "VRChat sign-in failed."
        )
        QMessageBox.warning(
            self,
            "Secure connection blocked" if tls_problem else "Could not sign in",
            message,
        )

    def refresh(self):
        if self.api is None or self.running or self._closing_requested:
            return
        if self.fetch_worker is not None and self.fetch_worker.isRunning():
            self.statusBar().showMessage("Avatar loading is already in progress…")
            return
        self.refresh_btn.setEnabled(False)
        self.library_hint.setText("Loading first 100 avatars…")
        self.statusBar().showMessage("Contacting VRChat · First avatars will appear shortly…")
        self.avatars.clear()
        self.filtered.clear()
        self.selected_avatar_ids.clear()
        self.selected_stat.setText("0")
        self.total_stat.setText("0")
        self.tagged_stat.setText("0")
        self.library.setRowCount(0)
        self._warning_loaded = 0
        worker = FetchWorker(self.api)
        self.fetch_worker = worker
        worker.page_received.connect(self.avatar_page_received)
        worker.success.connect(self.avatars_loaded)
        worker.error.connect(self.fetch_failed)
        self._worker(worker)

    def avatar_page_received(self, page, total):
        if self._closing_requested:
            return
        self.avatars.extend(page)
        warning_values = {value for _, value in CONTENT_TAGS}
        self._warning_loaded += sum(
            bool(set(a.tags or []) & warning_values) for a in page
        )
        self.total_stat.setText(str(total))
        self.tagged_stat.setText(str(self._warning_loaded))
        self.library_hint.setText(
            f"Loaded {total} avatars so far · More pages are loading…"
        )
        self.statusBar().showMessage(
            f"Loaded {total} avatars · You can browse while more load"
        )
        # Render the first page immediately; consolidate later page redraws.
        # Repainting thousands of table cells for every 100 avatars felt janky.
        if total <= 100 or total % 500 == 0:
            if not self._avatar_render_timer.isActive():
                self._avatar_render_timer.start()

    def avatars_loaded(self, avatars):
        if self._closing_requested:
            return
        self._avatar_render_timer.stop()
        self.avatars = list(avatars)
        self.total_stat.setText(str(len(self.avatars)))
        self.tagged_stat.setText(
            str(sum(
                bool(set(a.tags or []) & {v for _, v in CONTENT_TAGS})
                for a in self.avatars
            ))
        )
        self._event(f"Loaded {len(self.avatars)} avatar(s) successfully.")
        self.statusBar().showMessage(
            f"Loaded {len(self.avatars)} avatars · Ctrl/⌘+F to search"
        )
        self.render_avatars()

    def fetch_failed(self, message):
        if self._closing_requested:
            return
        self._avatar_render_timer.stop()
        self.render_avatars()
        self._event("ERROR  Avatar listing failed: " + message)
        self.library_hint.setText(
            f"Loading stopped after {len(self.avatars)} avatars. Refresh to retry."
        )
        QMessageBox.warning(
            self, "Avatar loading interrupted",
            f"{len(self.avatars)} avatars were loaded before this error:\n\n{message}"
        )

    def render_avatars(self):
        if not hasattr(self, "library"):
            return
        needle = self.search.text().strip().lower()
        warning_values = {value for _, value in CONTENT_TAGS}
        filter_index = self.filter_mode.currentIndex()
        def matches(avatar):
            tags = set(avatar.tags or [])
            if needle and needle not in str(avatar.name or "").lower() and needle not in " ".join(tags).lower():
                return False
            has_warning = bool(tags & warning_values)
            if filter_index == 1: return has_warning
            if filter_index == 2: return not has_warning
            if filter_index == 3: return bool(tags)
            if filter_index == 4: return not tags
            return True
        self.filtered = [avatar for avatar in self.avatars if matches(avatar)]
        self.library.blockSignals(True)
        self.library.setUpdatesEnabled(False)
        try:
            self.library.setRowCount(len(self.filtered))
            for row, avatar in enumerate(self.filtered):
                tags = list(avatar.tags or [])
                for col, value in enumerate((str(avatar.name or "Unnamed avatar"),
                                             ", ".join(tags[:4]) + ("  +" + str(len(tags)-4) if len(tags)>4 else "") if tags else "No tags",
                                             str(avatar.id))):
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    if col == 1:
                        item.setData(Qt.UserRole, tags)
                    self.library.setItem(row, col, item)
                self.library.setRowHeight(row, 62)
                if str(avatar.id) in self.selected_avatar_ids:
                    index = self.library.model().index(row, 0)
                    self.library.selectionModel().select(
                        index, QItemSelectionModel.Select | QItemSelectionModel.Rows
                    )
        finally:
            self.library.setUpdatesEnabled(True)
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
        try:
            tag = normalize_tag(self.custom_input.text())
        except ValueError as exc:
            QMessageBox.information(self, "Custom tags", str(exc))
            return
        if tag and tag not in self.custom_tags:
            self.custom_tags.append(tag)
        self.custom_input.clear()
        self.custom_view.setText(", ".join(self.custom_tags) if self.custom_tags else "No custom tags")

    def clear_custom(self):
        self.custom_tags.clear()
        self.custom_view.setText("No custom tags")

    def tags_to_use(self):
        return set(self.custom_tags) | {value for value, box in self.tag_checks.items() if box.isChecked()}

    def start_bulk(self, preview=False):
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
        preview = bool(preview)
        remove = self.mode.currentIndex() == 1
        if not preview:
            description = "REMOVE" if remove else "ADD"
            approved = QMessageBox.question(
                self, "Confirm avatar updates",
                f"{description} {len(tags)} tag(s) across {len(selected)} selected avatar(s)?\n\n"
                f"Tags: {', '.join(sorted(tags))}\n\n"
                "Click Yes to send these changes to VRChat. "
                "Existing unrelated tags will be preserved.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if approved != QMessageBox.Yes:
                return
        self.running = True
        self.run_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setRange(0, len(selected))
        self.progress.setValue(0)
        self.activity_progress.setRange(0, len(selected))
        self.activity_progress.setValue(0)
        self.activity_status.setText("Preview running…" if preview else "Applying changes…")
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
        self.activity_progress.setMaximum(total)
        self.activity_progress.setValue(index)
        self.progress_label.setText(f"{index}/{total}")
        self.activity_status.setText(f"Processed {index} of {total} avatars")

    def avatar_changed(self, avatar_id, tags):
        for avatar in self.avatars:
            if str(avatar.id) == avatar_id:
                avatar.tags = list(tags)
                break

    def bulk_complete(self, counts, preview):
        self.running = False
        self.run_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.tagged_stat.setText(str(sum(bool(set(a.tags or []) & {v for _, v in CONTENT_TAGS}) for a in self.avatars)))
        self.render_avatars()
        action = "PREVIEW ONLY · NO CHANGES SENT" if preview else "APPLIED · CONFIRMED BY VRCHAT"
        self._event(
            f"{action} · {'would change' if preview else 'saved'}: {counts['updated']}, "
            f"unchanged: {counts['unchanged']}, failed: {counts['failed']}"
        )
        self.progress_label.setText("Preview only · Nothing sent" if preview else "VRChat updates finished")
        self.statusBar().showMessage(
            f"{'Preview only' if preview else 'VRChat confirmed'} · "
            f"{counts['updated']} avatar(s) · {counts['failed']} failed"
        )
        self.activity_status.setText(
            f"{'Preview only' if preview else 'Applied & confirmed'} · "
            f"{counts['updated']} changed · {counts['failed']} failed"
        )
        message = (
            f"{counts['updated']} avatar(s) would change. No changes were sent to VRChat."
            if preview else
            f"VRChat confirmed {counts['updated']} avatar update(s). "
            f"{counts['unchanged']} already matched. {counts['failed']} failed. "
            "Review Activity for details."
        )
        QMessageBox.information(
            self, "Preview complete" if preview else "VRChat update results", message
        )

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
            self.preview_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.render_avatars()
        def failed(message):
            self.running = False
            self.run_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)
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
        # QThread's destructor aborts the entire macOS app if the worker is
        # still running. Request cooperative cancellation and let the *last*
        # finished signal close the window. Never destroy a running QThread.
        active = [worker for worker in self.workers if worker.isRunning()]
        if active:
            self._closing_requested = True
            self._avatar_render_timer.stop()
            self.statusBar().showMessage(
                "Finishing current VRChat request before closing safely…"
            )
            for worker in active:
                cancelled = getattr(worker, "cancelled", None)
                if cancelled is not None:
                    cancelled.set()
                if isinstance(worker, LoginWorker):
                    worker.submit_code("")  # release any outstanding 2FA wait
            event.ignore()
            return
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VRChat Avatar Tagger")
    app.setOrganizationName("VRChat Avatar Tagger")
    app.setWindowIcon(QIcon(resource_file("app-icon.png")))
    win = TaggerApp()

    def handle_unexpected_exception(exc_type, exc, tb):
        # An unhandled Qt slot exception must not cause Python to finalize
        # while background QThreads are still alive (Qt aborts on that).
        # Keep diagnostics in the local application data directory.
        from pathlib import Path
        import os
        log_path = Path(DATA_DIR) / "tagger_error.log"
        try:
            fd = os.open(
                str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
            )
            with os.fdopen(fd, "a", encoding="utf-8") as logfile:
                traceback.print_exception(exc_type, exc, tb, file=logfile)
            win.statusBar().showMessage(
                "An unexpected error occurred · See tagger_error.log in app data"
            )
        except Exception:
            traceback.print_exception(exc_type, exc, tb, file=sys.stderr)

    sys.excepthook = handle_unexpected_exception
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
