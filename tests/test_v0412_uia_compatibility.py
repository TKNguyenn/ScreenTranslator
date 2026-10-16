from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.quickux.uia_reader import read_selected_text


class GenericControl:
    """UIA provider with generic GetPattern, without typed convenience methods."""

    def __init__(self, text=None, *, password=False, pid=101, children=()):
        self.text = text
        self.IsPassword = password
        self.ProcessId = pid
        self.ControlTypeName = "CustomControl"
        self.AutomationId = ""
        self.ClassName = "Custom"
        self.NativeWindowHandle = 0
        self.children = list(children)
        self.next_sibling = None
        for left, right in zip(self.children, self.children[1:]):
            left.next_sibling = right

    def GetPattern(self, pattern_id):
        if pattern_id == 10014 and self.text is not None:
            return SimpleNamespace(GetSelection=lambda: [
                SimpleNamespace(GetText=lambda maximum: self.text[:maximum])])
        return None

    def GetParentControl(self):
        return None

    def GetFirstChildControl(self):
        return self.children[0] if self.children else None

    def GetNextSiblingControl(self):
        return self.next_sibling


class UiaCompatibilityTests(unittest.TestCase):
    def probe(self, focused, root=None, *, foreground=None):
        backend = SimpleNamespace(
            PatternId=SimpleNamespace(TextPattern=10014, ValuePattern=10002),
            GetFocusedControl=lambda: focused,
            ControlFromHandle=lambda hwnd: root,
        )
        statuses = []
        with patch("app.quickux.uia_reader.WindowService.get_foreground_window",
                   side_effect=foreground if foreground else None, return_value=55), \
             patch("app.quickux.uia_reader.WindowService.get_window_process_id", return_value=101):
            snapshot = read_selected_text(backend, 55, 100, on_status=statuses.append)
        return snapshot, statuses[-1]

    def test_generic_pattern_detects_selection_without_typed_getter(self):
        selected, _ = self.probe(GenericControl("selected text"))
        self.assertEqual(selected.text, "selected text")
        self.assertFalse(selected.replace_allowed)

    def test_descendant_document_detected_from_window_container(self):
        editor = GenericControl("document selection")
        root = GenericControl(children=[GenericControl(children=[editor])])
        selected, _ = self.probe(root, root)
        self.assertEqual(selected.text, "document selection")

    def test_password_focus_blocks_even_other_document_selection(self):
        selected, status = self.probe(GenericControl("secret", password=True),
                                      GenericControl("unrelated selection"))
        self.assertIsNone(selected)
        self.assertIn("password", status)

    def test_password_subtree_not_read(self):
        root = GenericControl(children=[GenericControl(password=True,
                               children=[GenericControl("secret")])])
        selected, _ = self.probe(root, root)
        self.assertIsNone(selected)

    def test_foreign_process_document_not_read(self):
        selected, _ = self.probe(GenericControl("foreign text", pid=999))
        self.assertIsNone(selected)

    def test_long_selection_is_rejected_without_scanning_other_documents(self):
        selected, status = self.probe(GenericControl("x" * 200), GenericControl("other"))
        self.assertIsNone(selected)
        self.assertIn("limit", status)

    def test_foreground_change_during_probe_rejected(self):
        selected, status = self.probe(GenericControl("original"), foreground=[55, 66])
        self.assertIsNone(selected)
        self.assertIn("changed", status)

    def test_error_status_does_not_include_provider_content(self):
        control = GenericControl()
        def fail(pattern_id):
            raise RuntimeError("private document content")
        control.GetPattern = fail
        with self.assertLogs("app.quickux.uia_reader", level="INFO") as logs:
            selected, status = self.probe(control)
        self.assertIsNone(selected)
        self.assertIn("RuntimeError", status)
        self.assertNotIn("private document content", status + str(logs.output))

    def test_tree_search_has_node_budget(self):
        root = GenericControl(children=[GenericControl() for _ in range(100)])
        selected, status = self.probe(root, root)
        self.assertIsNone(selected)
        self.assertIn("controls=64", status)


if __name__ == "__main__":
    unittest.main()
