from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from memory.automation_engine import (
    _record_automation_run,
    add_automation,
    clear_automation_history,
    get_automation_history,
    list_automations,
    set_automation_active,
)
from tools.automation_tools import try_handle_automation_request


class AutomationControlTests(unittest.TestCase):
    def test_pause_and_resume_preserve_automation(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch(
            "memory.automation_engine.DATA_DIR", tempdir
        ):
            saved = add_automation("user-1", {"type": "news_summary", "active": True})

            self.assertTrue(set_automation_active("user-1", saved["id"], False))
            self.assertFalse(list_automations("user-1")[0]["active"])
            self.assertTrue(set_automation_active("user-1", saved["id"], True))
            self.assertTrue(list_automations("user-1")[0]["active"])

    def test_natural_language_controls_workflow_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch(
            "memory.automation_engine.DATA_DIR", tempdir
        ):
            saved = add_automation("user-1", {"type": "news_summary", "active": True})

            reply = try_handle_automation_request(
                "user-1", f"pause automation {saved['id']}"
            )

            self.assertIn("paused", reply.lower())
            self.assertFalse(list_automations("user-1")[0]["active"])

    def test_execution_history_is_recorded_and_rendered(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch(
            "memory.automation_engine.DATA_DIR", tempdir
        ):
            saved = add_automation("user-1", {"type": "news_summary", "active": True})
            _record_automation_run("user-1", saved["id"], "Daily update complete", "completed")

            history = get_automation_history("user-1", saved["id"])
            reply = try_handle_automation_request(
                "user-1", f"automation history {saved['id']}"
            )

            self.assertEqual(history[0]["status"], "completed")
            self.assertIn("Daily update complete", reply)

    def test_clear_history_keeps_automation(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch(
            "memory.automation_engine.DATA_DIR", tempdir
        ):
            saved = add_automation("user-1", {"type": "news_summary", "active": True})
            _record_automation_run("user-1", saved["id"], "old result", "completed")

            self.assertTrue(clear_automation_history("user-1", saved["id"]))
            self.assertEqual(get_automation_history("user-1", saved["id"]), [])
            self.assertEqual(len(list_automations("user-1")), 1)

    def test_run_now_records_result_without_changing_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch(
            "memory.automation_engine.DATA_DIR", tempdir
        ), patch(
            "memory.automation_engine._execute_automation",
            return_value=("manual result", "completed"),
        ), patch("memory.automation_engine._deliver_result"):
            saved = add_automation("user-1", {"type": "news_summary", "active": False})

            from memory.automation_engine import run_automation_now

            success, result = run_automation_now("user-1", saved["id"])
            self.assertTrue(success)
            self.assertEqual(result, "manual result")
            self.assertFalse(list_automations("user-1")[0]["active"])
            self.assertEqual(get_automation_history("user-1", saved["id"])[0]["result"], "manual result")


if __name__ == "__main__":
    unittest.main()
