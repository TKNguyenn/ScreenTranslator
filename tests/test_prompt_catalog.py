from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.prompts import (
    build_translation_instructions,
    default_prompt_template,
    prompt_is_custom,
    render_prompt_template,
    validate_prompt_template,
)
from app.services.prompt_catalog import PromptCatalogStore


class PromptCatalogTests(unittest.TestCase):
    def test_empty_catalog_uses_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PromptCatalogStore(Path(tmp) / "prompts.json")
            overrides = store.read_overrides()
            self.assertEqual(overrides, {})
            self.assertFalse(prompt_is_custom("fast", "engineering", overrides))
            prompt = build_translation_instructions(
                "auto", "vi", "engineering", "fast", prompt_overrides=overrides
            )
            self.assertIn("industrial automation", prompt)

    def test_independent_speed_and_style_overrides_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompts.json"
            store = PromptCatalogStore(path)
            store.set_override(
                "fast", "engineering", "CUSTOM FAST ENG -> {target_language}"
            )
            store.set_override(
                "quality", "email", "CUSTOM QUALITY EMAIL -> {target_language}"
            )
            overrides = store.read_overrides()
            self.assertEqual(
                overrides["fast"]["engineering"],
                "CUSTOM FAST ENG -> {target_language}",
            )
            self.assertEqual(
                overrides["quality"]["email"],
                "CUSTOM QUALITY EMAIL -> {target_language}",
            )
            self.assertNotIn("chat", overrides.get("fast", {}))

            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["schema_version"], 1)
            self.assertIn("overrides", raw)

    def test_reset_one_does_not_remove_other_custom_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PromptCatalogStore(Path(tmp) / "prompts.json")
            store.set_override("fast", "engineering", "A {target_language}")
            store.set_override("fast", "chat", "B {target_language}")
            store.reset_override("fast", "engineering")
            overrides = store.read_overrides()
            self.assertNotIn("engineering", overrides["fast"])
            self.assertEqual(overrides["fast"]["chat"], "B {target_language}")

    def test_reset_all_returns_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PromptCatalogStore(Path(tmp) / "prompts.json")
            store.set_override("ultra_fast", "chat", "CUSTOM {target_language}")
            store.reset_all()
            self.assertEqual(store.read_overrides(), {})
            self.assertEqual(
                build_translation_instructions("auto", "vi", "chat", "ultra_fast"),
                render_prompt_template(
                    default_prompt_template("ultra_fast", "chat"),
                    source_language="auto",
                    target_language="vi",
                    context_preset="chat",
                ),
            )

    def test_unknown_placeholder_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_prompt_template("Translate to {target_language}. {unknown_variable}")

    def test_custom_prompt_renders_variables(self) -> None:
        overrides = {
            "fast": {
                "email": "From {source_language} to {target_language}. Style={style}. {glossary}"
            }
        }
        prompt = build_translation_instructions(
            "vi",
            "en",
            "email",
            "fast",
            prompt_overrides=overrides,
            glossary="TERM=VALUE",
        )
        self.assertIn("Vietnamese", prompt)
        self.assertIn("English", prompt)
        self.assertIn("professional business email", prompt)
        self.assertIn("TERM=VALUE", prompt)


if __name__ == "__main__":
    unittest.main()
