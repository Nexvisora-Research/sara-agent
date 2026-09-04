"""Task execution loop with Observe→Analyze→Plan→Execute→Verify→Repeat.

Uses the existing Sara vision AI pipeline for screen understanding and
the agent planner for task decomposition.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from ..config import ComputerUseConfig
from ..permissions import PermissionLevel

logger = logging.getLogger(__name__)


class TaskPlanner:
    """Observe-Analyze-Plan-Execute-Verify loop for desktop tasks."""

    def __init__(self, config: ComputerUseConfig, computer_agent):
        self.config = config
        self._agent = computer_agent
        self._llm_available = False
        self._init_llm()

    def _init_llm(self):
        try:
            from ..vision.llm import call_text_llm
            self._call_llm = call_text_llm
            self._llm_available = True
        except ImportError:
            self._call_llm = None
            self._llm_available = False

    def analyze_screen(self, observation: Dict[str, Any], task: str) -> Dict[str, Any]:
        elements = observation.get("elements", [])
        active_window = observation.get("active_window", {})
        windows = observation.get("windows", [])
        ui_tree = observation.get("ui_tree", {})

        analysis = {
            "task": task,
            "active_window_title": (active_window or {}).get("title", "Unknown"),
            "detected_elements": elements,
            "window_count": len(windows),
            "element_count": len(elements),
            "summary": "",
        }

        if self._llm_available:
            try:
                element_summary = json.dumps([
                    {"type": e.get("type"), "text": e.get("text", "")[:50],
                     "source": e.get("source")}
                    for e in elements[:30]
                ], indent=2)
                prompt = (
                    f"Current desktop state for task: {task}\n"
                    f"Active window: {analysis['active_window_title']}\n"
                    f"Detected UI elements ({len(elements)} total):\n{element_summary}\n\n"
                    "Analyze what is currently on screen. Identify what needs to happen next. "
                    "Return a brief analysis and what the first action should be."
                )
                text = self._call_llm(prompt, config=self.config)
                if text:
                    analysis["summary"] = text
            except Exception as e:
                logger.debug("LLM screen analysis failed: %s", e)

        return analysis

    def create_plan(self, analysis: Dict[str, Any], task: str) -> List[Dict[str, Any]]:
        plan = []

        if self._llm_available:
            try:
                prompt = (
                    f"Task: {task}\n"
                    f"Screen analysis: {analysis.get('summary', '')}\n"
                    f"Active window: {analysis.get('active_window_title', '')}\n"
                    f"Detected elements: {analysis.get('element_count', 0)}\n\n"
                    "Create a step-by-step plan of desktop actions. "
                    "Each step must be one of: move_mouse, click, double_click, drag, "
                    "scroll, type_text, press_key, hotkey, wait.\n"
                    "Return JSON: {\"steps\": [{\"action\": \"click\", \"params\": "
                    "{\"x\": 100, \"y\": 200}}]}\n"
                    "Include coordinates based on element positions."
                )
                text = self._call_llm(prompt, config=self.config)
                if text:
                    json_match = __import__("re").search(r'\{[\s\S]*"steps"[\s\S]*\}', text)
                    if json_match:
                        data = json.loads(json_match.group())
                        for step in data.get("steps", []):
                            action = step.get("action", "wait")
                            params = step.get("params", {})
                            plan.append({"type": action, **params})
            except Exception as e:
                logger.debug("LLM planning failed: %s", e)

        if not plan:
            plan.append({"type": "wait", "seconds": 0.5})

        return plan

    def execute_task_loop(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        permission_level: PermissionLevel = PermissionLevel.SMART,
    ) -> Dict[str, Any]:
        logger.info("Starting computer use task: %s", task)
        max_iter = self.config.planner_max_iterations
        all_results = []
        task_complete = False
        failure_count = 0

        for iteration in range(max_iter):
            logger.debug("Task loop iteration %d/%d", iteration + 1, max_iter)

            observation = self._agent.observe()
            analysis = self.analyze_screen(observation, task)
            plan = self.create_plan(analysis, task)

            if not plan:
                break

            iteration_result = {
                "iteration": iteration + 1,
                "analysis": analysis,
                "plan": plan,
                "actions": [],
            }

            for step in plan:
                action_result = self._agent.execute_action(step)
                iteration_result["actions"].append({
                    "action": step,
                    "result": action_result,
                })

                if not action_result.get("success"):
                    failure_count += 1
                    if failure_count >= self.config.planner_verify_retries:
                        logger.warning("Too many failures, aborting task")
                        iteration_result["aborted"] = True
                        break
                else:
                    failure_count = 0

                verify_result = self._agent.verify(action_result, task)
                iteration_result["verify"] = verify_result

                if verify_result.get("task_complete"):
                    task_complete = True
                    break

                time.sleep(0.3)

            all_results.append(iteration_result)

            if task_complete:
                break

            if iteration_result.get("aborted"):
                break

        final_state = self._agent.observe() if not task_complete else None

        return {
            "success": task_complete,
            "task": task,
            "iterations": len(all_results),
            "actions_taken": sum(len(r["actions"]) for r in all_results),
            "loop_results": all_results,
            "final_state": final_state,
        }
