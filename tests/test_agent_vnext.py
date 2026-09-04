import os
import shutil
import unittest
import uuid
from unittest.mock import patch

from agent.agent_loop import PendingConfirmationState, process_turn
from agent.planner import ExecutionPlan, Subtask, ToolCall, _infer_tool_calls
from memory.context_manager import add_message, get_context, get_full_history
from memory.memory_engine import auto_update_profile, finalize_turn_memory, retrieve_relevant_memories


class SaraVNextTests(unittest.TestCase):
    def setUp(self):
        self.user_id = f"test_vnext_{uuid.uuid4().hex[:8]}"
        self.user_dir = os.path.join("memory", "data", self.user_id)

    def tearDown(self):
        shutil.rmtree(self.user_dir, ignore_errors=True)

    def test_pending_confirmation_expires(self):
        state = PendingConfirmationState(
            user_input="install requests",
            completed_results=[],
            pending_subtasks=[],
            created_at=0,
        )
        self.assertTrue(state.is_expired(now=601))
        self.assertFalse(state.is_expired(now=599))

    def test_full_history_is_preserved_while_prompt_context_stays_bounded(self):
        for index in range(25):
            add_message(self.user_id, "user", f"message {index}", channel="test")

        history = get_full_history(self.user_id)
        context = get_context(self.user_id, max_messages=5)

        self.assertEqual(len(history), 25)
        self.assertIn("message 24", context)
        self.assertNotIn("message 2\n", context)

    def test_layered_memory_retrieves_relevant_stable_memory(self):
        auto_update_profile(self.user_id, "I want to learn Python step by step")
        finalize_turn_memory(
            self.user_id,
            "I want to learn Python step by step",
            "Sure, I'll help you learn Python step by step.",
            action_summaries=["generate_text(python plan)"],
        )

        memories = retrieve_relevant_memories(self.user_id, "python learning plan", limit=5)
        joined = " ".join(memory.content.lower() for memory in memories)

        self.assertIn("python", joined)
        self.assertTrue(any(memory.memory_type in {"goal", "task", "preference"} for memory in memories))

    def test_simple_chat_uses_direct_response(self):
        response = process_turn(self.user_id, "hi", channel="test")

        self.assertEqual(response.status, "final")
        self.assertIn("help", response.final_text.lower())

    def test_complex_safe_plan_runs_without_confirmation(self):
        plan = ExecutionPlan(
            user_goal="tell me the time and a joke",
            subtasks=[
                Subtask(
                    id="task_1",
                    goal="Get the current time",
                    tool_calls=[ToolCall("get_time", "")],
                    risk_level="safe_read",
                    expected_output="Current time",
                    parallelizable=True,
                ),
                Subtask(
                    id="task_2",
                    goal="Tell a joke",
                    tool_calls=[ToolCall("tell_joke", "")],
                    risk_level="safe_read",
                    expected_output="A joke",
                    parallelizable=True,
                ),
            ],
        )

        with patch("agent.agent_loop.plan_complex_task", return_value=plan):
            with patch("agent.planner.execute_tool", side_effect=["🕐 Current time: 10:00", "😄 Joke"]):
                response = process_turn(
                    self.user_id,
                    "please tell me the time and also tell me a joke",
                    channel="test",
                )

        self.assertEqual(response.status, "final")
        self.assertFalse(response.requires_confirmation)
        self.assertIn("Done:", response.final_text)

    def test_risky_subtasks_require_confirmation(self):
        plan = ExecutionPlan(
            user_goal="check time and install requests",
            subtasks=[
                Subtask(
                    id="task_1",
                    goal="Get the current time",
                    tool_calls=[ToolCall("get_time", "")],
                    risk_level="safe_read",
                    expected_output="Current time",
                    parallelizable=True,
                ),
                Subtask(
                    id="task_2",
                    goal="Install requests",
                    tool_calls=[ToolCall("install_package", "requests")],
                    risk_level="risky",
                    expected_output="Install output",
                    parallelizable=False,
                ),
            ],
        )

        with patch("agent.agent_loop.plan_complex_task", return_value=plan):
            with patch("agent.planner.execute_tool", return_value="🕐 Current time: 10:00"):
                response = process_turn(
                    self.user_id,
                    "please check the time and then install requests for me",
                    channel="test",
                )

        self.assertTrue(response.requires_confirmation)
        self.assertIn("approval", response.final_text.lower())

        stop_response = process_turn(self.user_id, "no", channel="test")
        self.assertIn("stopped", stop_response.final_text.lower())

    def test_power_commands_use_confirmation_route(self):
        response = process_turn(self.user_id, "shutdown pc", channel="test")

        self.assertTrue(response.requires_confirmation)
        self.assertIn("shutdown", response.final_text.lower())

    def test_run_command_phrase_routes_to_terminal_command(self):
        response = process_turn(self.user_id, "run command echo hello", channel="test")

        self.assertTrue(response.requires_confirmation)
        self.assertIn("run terminal", response.final_text.lower())
        self.assertIn("echo hello", response.final_text.lower())

    def test_install_app_phrase_routes_to_smart_open_app(self):
        response = process_turn(self.user_id, "install app chrome", channel="test")

        self.assertTrue(response.requires_confirmation)
        self.assertIn("smart_open_app", response.final_text)
        self.assertIn("chrome", response.final_text.lower())

    def test_heuristic_planner_recognizes_power_and_terminal_phrases(self):
        shutdown_call = _infer_tool_calls("restart computer")[0]
        terminal_call = _infer_tool_calls("open terminal run command npm run dev")[0]
        install_call = _infer_tool_calls("install app firefox")[0]
        delegate_call = _infer_tool_calls("delegate: improve this project")[0]

        self.assertEqual(shutdown_call.action, "restart_pc")
        self.assertEqual(terminal_call.action, "open_terminal")
        self.assertEqual(terminal_call.input, "npm run dev")
        self.assertEqual(install_call.action, "smart_open_app")
        self.assertEqual(install_call.input, "firefox")
        self.assertEqual(delegate_call.action, "delegate_task")
        self.assertEqual(delegate_call.input, "improve this project")

    def test_multi_agent_status_tool_is_registered(self):
        response = process_turn(self.user_id, "agents status", channel="test")

        self.assertEqual(response.status, "final")
        self.assertIn("multi-agent runtime", response.final_text.lower())
        self.assertIn(".agents", response.final_text)

    def test_multi_agent_delegate_route_uses_delegate_tool(self):
        with patch("agent.multi_agent.ask_ai_smart") as smart:
            with patch("agent.multi_agent.ask_ai_creative") as creative:
                smart.side_effect = [
                    '{"tasks":[{"id":"task_1","agent":"planner","goal":"Plan the work","context":""}]}',
                    "Planner output",
                ]
                creative.return_value = "Final multi-agent answer"

                response = process_turn(self.user_id, "use agents to plan a feature", channel="test")

        self.assertEqual(response.status, "final")
        self.assertIn("Final multi-agent answer", response.final_text)


if __name__ == "__main__":
    unittest.main()
