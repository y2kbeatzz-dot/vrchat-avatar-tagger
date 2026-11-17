"""Offline avatar listing speed and safe Qt thread lifecycle regression tests.

No real VRChat API requests are performed.
"""
import os
import sys
import time
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tagger_core import FETCH_PAGE_DELAY, REQUEST_DELAY, fetch_owned_avatars


def avatar(index):
    return SimpleNamespace(
        id=f"avtr_{index}", name=f"Avatar {index}", tags=[]
    )


class FakeApi:
    def __init__(self, count, latency=0):
        self.records = [avatar(i) for i in range(count)]
        self.calls = []
        self.latency = latency

    def search_avatars(self, **kwargs):
        self.calls.append(kwargs)
        if self.latency:
            time.sleep(self.latency)
        return self.records[
            kwargs["offset"]:kwargs["offset"] + kwargs["n"]
        ]


class FastPaginationTests(unittest.TestCase):
    def test_read_delay_is_not_write_delay(self):
        self.assertLessEqual(FETCH_PAGE_DELAY, 2.0)
        self.assertGreater(REQUEST_DELAY, FETCH_PAGE_DELAY)

    def test_three_pages_emit_incrementally_without_long_sleep(self):
        api = FakeApi(235)
        received = []
        started = time.monotonic()
        result = fetch_owned_avatars(
            api, on_page=lambda page, total: received.append((len(page), total)),
            page_delay=0,
        )
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertEqual(len(result), 235)
        self.assertEqual(received, [(100, 100), (100, 200), (35, 235)])
        self.assertEqual([r["offset"] for r in api.calls], [0, 100, 200])
        self.assertTrue(
            all(call["_request_timeout"] == (8, 20) for call in api.calls)
        )

    def test_cancel_while_loading_prevents_next_page(self):
        api = FakeApi(500)
        stop = threading.Event()
        received = []
        def first_page(page, total):
            received.append(total)
            stop.set()
        result = fetch_owned_avatars(
            api, stopped=stop.is_set, cancel_event=stop,
            on_page=first_page, page_delay=1.0,
        )
        self.assertEqual(len(result), 100)
        self.assertEqual(received, [100])
        self.assertEqual(len(api.calls), 1)


@unittest.skipUnless(os.environ.get("QT_QPA_PLATFORM") == "offscreen",
                     "Requires headless Qt environment")
class QtLifecycleTests(unittest.TestCase):
    def test_close_during_fetch_cancels_without_destroying_thread(self):
        from PySide6.QtWidgets import QApplication
        from tag_avatars_qt import TaggerApp
        app = QApplication.instance() or QApplication([])
        window = TaggerApp()
        window.stack.setCurrentIndex(1)
        window.api = FakeApi(400, latency=0.35)
        window.show()
        window.refresh()
        worker = window.fetch_worker
        self.assertIsNotNone(worker)
        self.assertTrue(worker.isRunning())
        # A close request must not destroy a running QThread.
        window.close()
        self.assertTrue(window._closing_requested)
        self.assertTrue(worker.cancelled.is_set())
        self.assertTrue(window.isVisible())

        deadline = time.monotonic() + 8
        while window.isVisible() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.015)
        app.processEvents()
        self.assertFalse(window.isVisible())
        self.assertFalse(worker.isRunning())
        self.assertEqual(len(window.workers), 0)
        self.assertLessEqual(len(window.api.calls), 1)


if __name__ == "__main__":
    unittest.main()
