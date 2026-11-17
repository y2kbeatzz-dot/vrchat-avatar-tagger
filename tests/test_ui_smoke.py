"""Offline smoke checks for the desktop presentation layer.

Does not log in, contact VRChat, or change any avatar.
Run with QT_QPA_PLATFORM=offscreen python tests/test_ui_smoke.py
"""
from types import SimpleNamespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from tag_avatars_qt import TaggerApp


def avatar(name, identifier, tags):
    return SimpleNamespace(name=name, id=identifier, tags=tags)


def test_app():
    qt = QApplication([])
    window = TaggerApp()
    assert window.stack.count() == 2
    assert window.pages.count() == 3
    assert not window.running
    assert window.run_btn.text().startswith("Preview")
    assert window.filter_mode.count() == 5

    sample = [
        avatar("Nova", "avtr_nova", ["content_sex", "fantasy"]),
        avatar("Moonlight", "avtr_moon", []),
        avatar("Snowfall", "avtr_snow", ["custom"]),
    ]
    window.avatars_loaded(sample)
    assert window.library.rowCount() == 3
    assert window.total_stat.text() == "3"
    assert window.tagged_stat.text() == "1"
    assert window.library.item(0, 1).data(0x0100) == ["content_sex", "fantasy"]

    window.filter_mode.setCurrentIndex(1)  # Content warnings
    assert window.library.rowCount() == 1
    assert window.library.item(0, 0).text() == "Nova"

    window.filter_mode.setCurrentIndex(4)  # Untagged
    assert window.library.rowCount() == 1
    assert window.library.item(0, 0).text() == "Moonlight"

    window.filter_mode.setCurrentIndex(0)
    window.search.setText("snow")
    assert window.library.rowCount() == 1
    assert window.library.item(0, 0).text() == "Snowfall"

    window.search.clear()
    window.select_visible()
    assert len(window.selected_avatar_ids) == 3
    window.clear_selection()
    assert not window.selected_avatar_ids

    window.dry.setChecked(False)
    assert window.run_btn.text().startswith("Apply")
    window.dry.setChecked(True)
    assert window.run_btn.text().startswith("Preview")

    window.toggle_theme()
    assert window.light
    window.toggle_theme()
    assert not window.light

    window.update_progress(2, 3)
    assert window.progress.value() == 2
    assert window.activity_progress.value() == 2
    window.show()
    qt.processEvents()
    # Exercise the custom avatar rows without ever making an API request.
    assert not window.library.viewport().grab().isNull()
    window.close()
    qt.processEvents()
    print("Desktop UI smoke tests passed.")


if __name__ == "__main__":
    test_app()
