"""Offline tests: tagging must perform real writes and verify the saved tags.

No live VRChat API calls or credentials are used.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tagger_core import ProgressStore, normalize_tag, update_avatar_tags
from tag_avatars_qt import TagWorker, SingleEditWorker


class FakeAvatarAPI:
    def __init__(self, accepted=True):
        self.requests = []
        self.accepted = accepted

    def update_avatar(self, avatar_id, update_avatar_request):
        self.requests.append((avatar_id, list(update_avatar_request.tags)))
        actual = list(update_avatar_request.tags) if self.accepted else []
        return SimpleNamespace(id=avatar_id, tags=actual)


def avatar(name, identifier, tags):
    return SimpleNamespace(name=name, id=identifier, tags=list(tags))


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.store = ProgressStore(Path(self.tempdir.name) / "progress.json")

    def test_sdk_response_verifies_saved_tags(self):
        api = FakeAvatarAPI()
        saved = update_avatar_tags(api, "avtr_one", {"content_sex", "author_tag_fantasy"})
        self.assertEqual(saved, ["author_tag_fantasy", "content_sex"])
        self.assertEqual(api.requests[0][0], "avtr_one")

    def test_rejected_or_unconfirmed_write_never_counts_as_success(self):
        api = FakeAvatarAPI(accepted=False)
        self.assertRaisesRegex(
            RuntimeError, "different tags",
            update_avatar_tags, api, "avtr_one", {"content_sex"}
        )

    def test_custom_tags_get_author_namespace(self):
        self.assertEqual(normalize_tag(" fantasy "), "author_tag_fantasy")
        self.assertEqual(normalize_tag("author_tag_Fantasy"), "author_tag_fantasy")
        with self.assertRaises(ValueError):
            normalize_tag("content_horror")

    def test_preview_does_not_issue_update(self):
        api = FakeAvatarAPI()
        a = avatar("Example", "avtr_one", ["author_tag_original"])
        worker = TagWorker(api, [a], {"content_sex"}, False, True, True, 0, self.store)
        results = []
        worker.complete.connect(results.append)
        worker.run()
        self.assertEqual(api.requests, [])
        self.assertEqual(results[-1]["updated"], 1)
        self.assertEqual(a.tags, ["author_tag_original"])
        self.assertFalse(self.store.done("add:content_sex", a.id))

    def test_apply_sends_real_write_and_preserves_other_tags(self):
        api = FakeAvatarAPI()
        a = avatar("Example", "avtr_one", ["author_tag_original"])
        worker = TagWorker(api, [a], {"content_sex"}, False, False, True, 0, self.store)
        results = []
        worker.complete.connect(results.append)
        worker.run()
        self.assertEqual(api.requests, [("avtr_one", ["author_tag_original", "content_sex"])])
        self.assertEqual(results[-1]["updated"], 1)
        self.assertEqual(a.tags, ["author_tag_original", "content_sex"])
        self.assertTrue(self.store.done("add:content_sex", a.id))

    def test_stale_resume_record_must_reapply(self):
        api = FakeAvatarAPI()
        a = avatar("Example", "avtr_one", [])
        self.store.mark("add:content_sex", a.id)
        worker = TagWorker(api, [a], {"content_sex"}, False, False, True, 0, self.store)
        results = []
        worker.complete.connect(results.append)
        worker.run()
        self.assertEqual(len(api.requests), 1)
        self.assertEqual(results[-1]["updated"], 1)

    def test_api_disagreement_does_not_mark_progress(self):
        api = FakeAvatarAPI(accepted=False)
        a = avatar("Example", "avtr_one", [])
        worker = TagWorker(api, [a], {"content_sex"}, False, False, True, 0, self.store)
        results = []
        worker.complete.connect(results.append)
        worker.run()
        self.assertEqual(results[-1]["failed"], 1)
        self.assertEqual(results[-1]["updated"], 0)
        self.assertFalse(self.store.done("add:content_sex", a.id))

    def test_single_edit_checks_server_response(self):
        api = FakeAvatarAPI()
        worker = SingleEditWorker(api, "avtr_one", ["author_tag_fantasy"])
        saved = []
        worker.success.connect(lambda avatar_id, tags: saved.append((avatar_id, tags)))
        worker.run()
        self.assertEqual(saved, [("avtr_one", ["author_tag_fantasy"])])


if __name__ == "__main__":
    unittest.main()
