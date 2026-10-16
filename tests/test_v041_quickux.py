from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import QuickUxSection, parse_quick_ux_section
from app.quickux.selection import MouseGestureRecognizer, SelectionSnapshot
from app.quickux.uia_reader import read_selected_text, WindowsUiaSelectionReader
from app.quickux.selection_worker import QuickSelectionWorker

PROJECT = Path(__file__).resolve().parents[1]


class QuickUxConfigTests(unittest.TestCase):
    def test_default_enabled_no_prompt_changes(self):
        default = QuickUxSection()
        self.assertTrue(default.auto_show_toolbar)
        self.assertEqual(default.selection_delay_ms, 250)
        self.assertEqual(default.languages, ('vi', 'en', 'zh-Hant'))

    def test_as_json_roundtrip(self):
        original = QuickUxSection(auto_show_toolbar=False, selection_delay_ms=350,
                                  languages=('en', 'vi'), toolbar_timeout_ms=12000)
        self.assertEqual(parse_quick_ux_section(original.as_json()), original)

    def test_invalid_toggles_rejected(self):
        for bad in ('yes', 1, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_quick_ux_section({'auto_show_toolbar': bad})

    def test_empty_and_unknown_languages_rejected(self):
        for bad in ([], ['ja'], ['vi','xx'], 'vi'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_quick_ux_section({'languages': bad})

    def test_timing_limits(self):
        for n in (149, 601, '250', True):
            with self.subTest(n=n), self.assertRaises(ValueError):
                parse_quick_ux_section({'selection_delay_ms': n})

    def test_language_duplicates_removed(self):
        self.assertEqual(parse_quick_ux_section({'languages':['vi','vi','en']}).languages, ('vi','en'))

    def test_default_config_file_quick_on(self):
        import json
        config = json.loads((PROJECT / 'config.json').read_text(encoding='utf-8'))
        self.assertTrue(config['quick_ux']['auto_show_toolbar'])
        self.assertNotIn('quick_ux', config['providers'])
        self.assertNotIn('quick_ux', config['translation'])


class MouseGestureTests(unittest.TestCase):
    def test_click_does_not_trigger(self):
        g = MouseGestureRecognizer()
        g.press(10, 10, 1.0, 33)
        self.assertFalse(g.release(11, 11, 1.1, 33))

    def test_drag_triggers(self):
        g = MouseGestureRecognizer()
        g.press(-800, 100, 1.0, 33)
        self.assertTrue(g.release(-650, 130, 1.3, 33))

    def test_double_click_triggers(self):
        g = MouseGestureRecognizer()
        g.press(20,20, 1.0, 33)
        self.assertFalse(g.release(20,20,1.05,33))
        g.press(20,20, 1.15, 33)
        self.assertTrue(g.release(20,20, 1.20, 33))

    def test_disjoint_or_slow_clicks_no_trigger(self):
        g = MouseGestureRecognizer()
        g.press(20,20, 1.0, 33)
        self.assertFalse(g.release(20,20,1.05,33))
        g.press(22,23, 2.0, 33)
        self.assertFalse(g.release(22,23,2.02,33))

    def test_different_windows_no_trigger(self):
        g = MouseGestureRecognizer()
        g.press(30,30, 1.0, 33)
        self.assertFalse(g.release(50,50,1.2,44))


class FakeRange:
    def __init__(self, text): self.text=text
    def GetText(self, maximum): return self.text[:maximum]

class FakePattern:
    def __init__(self, text): self.text=text
    def GetSelection(self): return [FakeRange(self.text)]

class FakeControl:
    def __init__(self, text, password=False, read_only=False, parent=None):
        self.text=text
        self.IsPassword=password
        self.IsReadOnly=read_only
        self.ProcessId=101
        self.ControlTypeName='EditControl'
        self.AutomationId='editor'
        self.ClassName='Edit'
        self.NativeWindowHandle=222
        self.parent=parent
        self.BoundingRectangle=SimpleNamespace(left=30,top=40,right=200,bottom=80)

    def GetTextPattern(self): return FakePattern(self.text) if self.text is not None else None
    def GetValuePattern(self): return SimpleNamespace(IsReadOnly=self.IsReadOnly)
    def GetParentControl(self): return self.parent


class UiaReaderTests(unittest.TestCase):
    def _probe(self, focused: FakeControl | None, *, pointed=None, limit=100):
        backend = SimpleNamespace(GetFocusedControl=lambda:focused,
                                  ControlFromPoint=lambda x,y:pointed)
        with patch('app.quickux.uia_reader.WindowService.get_foreground_window',return_value=55):
            return read_selected_text(backend, 55, limit, pointer=(100,100))

    def test_capture_exact_selected_text(self):
        actual = self._probe(FakeControl('設備設定'))
        self.assertIsNotNone(actual)
        self.assertEqual(actual.text,'設備設定')
        self.assertEqual(actual.hwnd,55)

    def test_password_guard(self):
        self.assertIsNone(self._probe(FakeControl('secret',password=True),
                                      pointed=FakeControl('other text')))

    def test_sensitive_automation_id_guard(self):
        secure=FakeControl('secret')
        secure.AutomationId='password-field'
        self.assertIsNone(self._probe(secure))

    def test_no_selection(self):
        self.assertIsNone(self._probe(FakeControl('')))

    def test_bounded_max_characters(self):
        self.assertIsNone(self._probe(FakeControl('abc'*100),limit=20))

    def test_readonly_disables_replace(self):
        selection = self._probe(FakeControl('text',read_only=True))
        self.assertIsNotNone(selection)
        self.assertFalse(selection.replace_allowed)

    def test_missing_value_pattern_does_not_enable_replace(self):
        control = FakeControl('selected in a document')
        control.GetValuePattern = lambda: None
        snapshot = self._probe(control)
        self.assertIsNotNone(snapshot)
        self.assertFalse(snapshot.replace_allowed)

    def test_parent_text_pattern_fallback(self):
        child=FakeControl(None,parent=FakeControl('parent selection'))
        selection=self._probe(child)
        self.assertEqual(selection.text,'parent selection')

    def test_foreground_must_match(self):
        backend = SimpleNamespace(GetFocusedControl=lambda:FakeControl('abc'))
        with patch('app.quickux.uia_reader.WindowService.get_foreground_window',return_value=56):
            self.assertIsNone(read_selected_text(backend,55,100))

    def test_verification_rejects_changed_text(self):
        snapshot=SelectionSnapshot('ABC',55,('x',),True)
        reader=WindowsUiaSelectionReader()
        with patch.object(reader,'probe',return_value=SelectionSnapshot('ABD',55,('x',),True)):
            self.assertFalse(reader.verify(snapshot))

    def test_verification_rejects_changed_control(self):
        snapshot=SelectionSnapshot('ABC',55,('x',),True)
        reader=WindowsUiaSelectionReader()
        with patch.object(reader,'probe',return_value=SelectionSnapshot('ABC',55,('y',),True)):
            self.assertFalse(reader.verify(snapshot))


class FakeReader:
    def __init__(self): self.max_characters=500
    def probe(self,hwnd,pointer): return SelectionSnapshot('text',hwnd,('x',),True)
    def verify(self,snapshot): return True


class WorkerTests(unittest.TestCase):
    def test_worker_emits_probe_and_verification_results(self):
        from queue import Queue
        probes, verifies = Queue(), Queue()
        worker=QuickSelectionWorker(probes.put,verifies.put, reader=FakeReader())
        worker.start()
        try:
            worker.probe(7, 55, -500, 300)
            self.assertEqual(probes.get(timeout=2).snapshot.text,'text')
            worker.verify('job',SelectionSnapshot('text',55,('x',),True))
            self.assertTrue(verifies.get(timeout=2).valid)
        finally:
            worker.stop()


class SourceArchitectureTests(unittest.TestCase):
    def _source(self, name):return (PROJECT / name).read_text(encoding='utf-8')
    def test_quick_popup_nofocus(self):
        for name in ('app/ui/quick_popup.py','app/ui/quick_toolbar.py'):
            source=self._source(name)
            self.assertIn('Qt.WindowDoesNotAcceptFocus',source)
            self.assertIn('Qt.WA_ShowWithoutActivating',source)

    def test_no_clipboard_access_in_auto_monitor(self):
        for name in ('app/quickux/mouse_monitor.py','app/quickux/uia_reader.py'):
            source=self._source(name)
            self.assertNotIn('pyperclip.',source)
            self.assertNotIn('keyboard.send(',source)

    def test_settings_tray_and_pipeline(self):
        controller=self._source('app/controller.py')
        self.assertIn('self._bridge.quick_probe.connect(self._on_quick_probe)',controller)
        self.assertIn('self._translation_worker.submit(request)',controller)
        self.assertIn('self._quick_selection_worker.verify(job_id, snapshot)',controller)
        self.assertIn('self._main_window.quick_ux_settings_requested.connect',controller)
        self.assertIn('expected_selected_text=snapshot.text',controller)
        self.assertIn('self._tray.set_quick_auto_enabled',controller)

    def test_legacy_hotkeys_untouched(self):
        source=self._source('app/services/hotkeys.py')
        self.assertIn('HotkeyAction.TRANSLATE_SELECTION',source)
        self.assertIn('HotkeyAction.TRANSLATE_AND_REPLACE',source)
        self.assertIn('on_escape',source)

    def test_main_window_and_tray_controls(self):
        self.assertIn('Lưu & áp dụng Quick UX',self._source('app/ui/main_window.py'))
        self.assertIn('Tự hiện Quick Toolbar khi bôi đen',self._source('app/ui/tray.py'))

    def test_explicit_replace_rechecks_at_input_worker(self):
        source=self._source('app/workers/input_worker.py')
        self.assertIn('expected_selected_text',source)
        self.assertIn('current.text != task.expected_selected_text',source)
        self.assertIn('self._service.capture_selection(None)', source)
        self.assertIn('destination = None if task.expected_selected_text', source)
        self.assertIn('cancel_event=task.cancel_event', source)

    def test_canceled_quick_translation_never_falls_through_to_old_paste(self):
        source=self._source('app/controller.py')
        self.assertIn('self._quick_translation_ids: set[str]', source)
        self.assertIn('if job_id in self._quick_translation_ids:', source)
        self.assertIn('if pending is None or not pending.quick:', source)
        self.assertIn('self._cancel_quick_replacements()', source)

    def test_popup_close_cancels_pending_replaces(self):
        self.assertIn('closed = Signal()', self._source('app/ui/quick_popup.py'))
        self.assertIn('self._quick_popup.closed.connect(self._on_quick_popup_closed)',
                      self._source('app/controller.py'))


if __name__=='__main__':
    unittest.main()
