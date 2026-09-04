from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.storage import load_json, save_json, user_directory, validate_user_id


class MemoryStorageTests(unittest.TestCase):
    def test_valid_user_ids_are_scoped_to_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = user_directory(tempdir, "telegram-123_abc")
            self.assertEqual(directory, Path(tempdir) / "telegram-123_abc")
            self.assertTrue(directory.is_dir())

    def test_invalid_user_ids_are_rejected(self) -> None:
        for user_id in ("", ".", "..", "../outside", "user/id", "a" * 129):
            with self.subTest(user_id=user_id):
                with self.assertRaises(ValueError):
                    validate_user_id(user_id)

    def test_save_json_is_readable_after_atomic_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "profile.json"
            value = {"name": "Sara", "message": "こんにちは 😊"}
            save_json(path, value)

            self.assertEqual(load_json(path, {}), value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), value)


if __name__ == "__main__":
    unittest.main()
