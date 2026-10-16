from __future__ import annotations

import threading
import unittest

from app.ocr.mock_engine import MockOcrEngine
from app.workers.ocr_worker import OcrWorker


class OcrWorkerTests(unittest.TestCase):
    def test_worker_returns_text_without_blocking_caller(self) -> None:
        event = threading.Event()
        results = []
        worker = OcrWorker(MockOcrEngine("設備就緒"), lambda result: (results.append(result), event.set()))
        worker.start()
        try:
            worker.submit("job-1", b"fake-png")
            self.assertTrue(event.wait(1.0))
            self.assertEqual(results[0].job_id, "job-1")
            self.assertEqual(results[0].text, "設備就緒")
            self.assertIsNone(results[0].error)
        finally:
            worker.stop()

    def test_engine_reload_is_ordered_in_queue(self) -> None:
        event = threading.Event()
        results = []
        worker = OcrWorker(MockOcrEngine("old"), lambda result: (results.append(result), event.set()))
        worker.start()
        try:
            worker.replace_engine(MockOcrEngine("new"))
            worker.submit("job-2", b"fake")
            self.assertTrue(event.wait(1.0))
            self.assertEqual(results[0].text, "new")
        finally:
            worker.stop()


if __name__ == "__main__":
    unittest.main()
