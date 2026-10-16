from __future__ import annotations

import unittest

from app.prompts import build_translation_instructions


class PromptTests(unittest.TestCase):
    def test_engineering_prompt(self) -> None:
        prompt = build_translation_instructions("auto", "vi", "engineering", "quality")
        self.assertIn("industrial automation", prompt)
        self.assertIn("PLC", prompt)
        self.assertIn("Return only the translated text", prompt)

    def test_email_prompt(self) -> None:
        prompt = build_translation_instructions("vi", "en", "email", "quality")
        self.assertIn("professional", prompt)

    def test_chat_prompt(self) -> None:
        prompt = build_translation_instructions("auto", "vi", "chat", "quality")
        self.assertIn("conversational", prompt)


class PerformancePromptTests(unittest.TestCase):
    def test_ultra_fast_is_shorter_than_fast_and_quality(self) -> None:
        ultra = build_translation_instructions("auto", "vi", "engineering", "ultra_fast")
        fast = build_translation_instructions("auto", "vi", "engineering", "fast")
        quality = build_translation_instructions("auto", "vi", "engineering", "quality")
        self.assertLess(len(ultra), len(fast))
        self.assertLess(len(fast), len(quality))
        self.assertIn("Output translation only", ultra)

    def test_ultra_fast_context_changes_style(self) -> None:
        engineering = build_translation_instructions("auto", "vi", "engineering", "ultra_fast")
        email = build_translation_instructions("auto", "vi", "email", "ultra_fast")
        chat = build_translation_instructions("auto", "vi", "chat", "ultra_fast")
        self.assertIn("industrial automation", engineering)
        self.assertIn("professional email", email)
        self.assertIn("natural chat", chat)
