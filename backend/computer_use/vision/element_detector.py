"""UI element detection with coordinate mapping.

Priority chain: AT-SPI → Accessibility APIs → OCR → Vision AI.
Returns structured JSON with element type, text, bounds, and confidence.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from ..config import ComputerUseConfig

logger = logging.getLogger(__name__)


class ElementDetector:
    """Detects UI elements on screen using multiple strategies."""

    def __init__(self, config: ComputerUseConfig):
        self.config = config
        self._opencv = None
        self._tesseract = None
        self._init_optional()

    def _init_optional(self):
        try:
            import cv2
            self._opencv = cv2
        except ImportError:
            pass
        try:
            import pytesseract
            self._tesseract = pytesseract
        except ImportError:
            pass

    def detect_all(self, screenshot_b64: str) -> List[Dict[str, Any]]:
        elements = []
        elements.extend(self._detect_from_atspi())
        elements.extend(self._detect_from_ocr(screenshot_b64))
        elements.extend(self._detect_from_vision(screenshot_b64))
        elements = self._deduplicate(elements)
        return elements

    def _detect_from_atspi(self) -> List[Dict[str, Any]]:
        try:
            from ..accessibility.atspi_bridge import ATSPIBridge
            bridge = ATSPIBridge()
            tree = bridge.get_ui_tree()
            return self._extract_elements_from_tree(tree)
        except Exception as e:
            logger.debug("AT-SPI element detection failed: %s", e)
            return []

    def _extract_elements_from_tree(self, node: dict, depth: int = 0) -> List[Dict[str, Any]]:
        if depth > 10:
            return []
        elements = []
        role = (node.get("role") or "").lower()
        name = (node.get("name") or "").strip()
        rect = node.get("rect") or {}

        if role in ("push button", "toggle button", "button", "menu item", "check box", "radio button"):
            elements.append({
                "type": "button",
                "text": name,
                "bounds": rect,
                "confidence": 0.95,
                "source": "atspi",
                "children_count": len(node.get("children", [])),
            })
        elif role in ("text", "entry", "password text", "combo box", "spin button"):
            elements.append({
                "type": "input",
                "text": name,
                "bounds": rect,
                "confidence": 0.95,
                "source": "atspi",
            })
        elif role in ("menu", "popup menu", "sub menu"):
            items = self._extract_elements_from_tree(node, depth + 1)
            elements.append({
                "type": "menu",
                "text": name,
                "bounds": rect,
                "confidence": 0.9,
                "source": "atspi",
                "children": items,
            })
        elif role in ("page tab", "tab"):
            elements.append({
                "type": "tab",
                "text": name,
                "bounds": rect,
                "confidence": 0.9,
                "source": "atspi",
            })
        elif role in ("dialog", "alert", "window", "frame"):
            children = self._extract_elements_from_tree(node, depth + 1)
            elements.append({
                "type": "dialog" if role in ("dialog", "alert") else "window",
                "text": name,
                "bounds": rect,
                "confidence": 0.85,
                "source": "atspi",
                "children": children,
            })
        elif role in ("notification", "panel") and name:
            elements.append({
                "type": "notification" if role == "notification" else "panel",
                "text": name,
                "bounds": rect,
                "confidence": 0.8,
                "source": "atspi",
            })

        for child in node.get("children", []):
            elements.extend(self._extract_elements_from_tree(child, depth + 1))

        return elements

    def _detect_from_ocr(self, screenshot_b64: str) -> List[Dict[str, Any]]:
        if not self._tesseract or not screenshot_b64:
            return []
        try:
            import base64
            from PIL import Image
            import io
            img_data = base64.b64decode(screenshot_b64)
            img = Image.open(io.BytesIO(img_data))

            ocr_data = self._tesseract.image_to_data(img, output_type=self._tesseract.Output.DICT)
            elements = []
            n_boxes = len(ocr_data.get("text", []))
            for i in range(n_boxes):
                text = (ocr_data.get("text", [""])[i] or "").strip()
                conf = int(ocr_data.get("conf", [0])[i] or 0)
                if not text or conf < self.config.ocr_confidence * 100:
                    continue
                x = ocr_data.get("left", [0])[i]
                y = ocr_data.get("top", [0])[i]
                w = ocr_data.get("width", [0])[i]
                h = ocr_data.get("height", [0])[i]
                element_type = self._classify_text_element(text, x, y, w, h, img)
                elements.append({
                    "type": element_type,
                    "text": text,
                    "bounds": {"x": x, "y": y, "width": w, "height": h},
                    "confidence": conf / 100.0,
                    "source": "ocr",
                })
            return elements
        except Exception as e:
            logger.debug("OCR detection failed: %s", e)
            return []

    def _classify_text_element(self, text: str, x: int, y: int, w: int, h: int, img) -> str:
        upper = text.upper()
        if re.search(r'^(OK|SAVE|SUBMIT|CANCEL|YES|NO|NEXT|BACK|LOGIN|SIGN.?IN|SEARCH|SEND|OPEN|CLOSE|DELETE|EDIT)$', upper):
            return "button"
        if re.search(r'^(SEARCH|FIND|TYPE|ENTER|INPUT|USERNAME|EMAIL|PASSWORD)$', upper):
            return "input"
        if re.search(r'^(FILE|EDIT|VIEW|HELP|TOOLS|SETTINGS|OPTIONS|WINDOW)$', upper):
            return "menu"
        if text.startswith("http") or text.startswith("www"):
            return "link"
        if h > 30 and w > 100:
            return "button" if h < 60 else "dialog_title"
        return "label"

    def _detect_from_vision(self, screenshot_b64: str) -> List[Dict[str, Any]]:
        if not screenshot_b64:
            return []
        try:
            from .llm import call_vision_llm
            prompt = (
                "You are a UI element detector. Analyze this screenshot and list all "
                "interactive UI elements (buttons, inputs, menus, tabs, dialogs, "
                "notifications, links, checkboxes, dropdowns). Return ONLY valid JSON:\n"
                "{\"elements\": [{\"type\": \"button|input|menu|tab|dialog|notification|link|checkbox|dropdown\", "
                "\"text\": \"element text\", \"bounds_estimate\": \"top-left region description\", "
                "\"confidence\": 0.0-1.0}]}\n"
                "Do NOT include markdown formatting or explanation."
            )
            text = call_vision_llm(prompt, screenshot_b64, config=self.config)
            if not text:
                return []
            json_match = re.search(r'\{[\s\S]*"elements"[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                for el in data.get("elements", []):
                    el["source"] = "vision"
                    if "bounds" not in el:
                        el["bounds"] = {}
                return data.get("elements", [])
        except Exception as e:
            logger.debug("Vision-based element detection failed: %s", e)
        return []

    def _deduplicate(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for el in sorted(elements, key=lambda e: -e.get("confidence", 0)):
            key = (el.get("type", ""), el.get("text", ""),
                   str(el.get("bounds", {}).get("x", "")),
                   str(el.get("bounds", {}).get("y", "")))
            if key not in seen:
                seen.add(key)
                unique.append(el)
        return unique
