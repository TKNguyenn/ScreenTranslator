from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from app.models import OcrResult
from app.ocr.base import OcrEngine


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OcrTask:
    job_id: str
    image_png: bytes


@dataclass(frozen=True)
class OcrReloadTask:
    engine: OcrEngine


class OcrWorker:
    """Dedicated OCR queue so local inference never blocks the Qt UI thread."""

    def __init__(self, engine: OcrEngine, on_result: Callable[[OcrResult], None]) -> None:
        self._engine = engine
        self._on_result = on_result
        self._queue: queue.Queue[OcrTask | OcrReloadTask | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="OcrWorker", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._close_engine(self._engine)

    def submit(self, job_id: str, image_png: bytes) -> None:
        self._queue.put(OcrTask(job_id=job_id, image_png=image_png))

    def replace_engine(self, engine: OcrEngine) -> None:
        """Queue engine replacement behind any OCR already in progress."""
        self._queue.put(OcrReloadTask(engine=engine))

    def _run(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                return
            if isinstance(task, OcrReloadTask):
                old = self._engine
                self._engine = task.engine
                self._close_engine(old)
                logger.info("OCR engine switched to %s", self._engine.engine_id)
                continue
            self._recognize(task)

    def _recognize(self, task: OcrTask) -> None:
        started = time.monotonic()
        try:
            text, blocks = self._engine.recognize(task.image_png)
            if not text.strip():
                raise RuntimeError(
                    "OCR không tìm thấy chữ đủ độ tin cậy trong vùng đã chọn. "
                    "Hãy chọn vùng chữ rõ hơn hoặc giảm ocr.min_confidence."
                )
            elapsed = time.monotonic() - started
            logger.info(
                "OCR completed job_id=%s engine=%s elapsed=%.3fs blocks=%s chars=%s",
                task.job_id,
                self._engine.engine_id,
                elapsed,
                len(blocks),
                len(text),
            )
            self._on_result(OcrResult(job_id=task.job_id, text=text, blocks=blocks))
        except Exception as exc:
            elapsed = time.monotonic() - started
            logger.exception(
                "OCR failed job_id=%s engine=%s elapsed=%.3fs",
                task.job_id,
                self._engine.engine_id,
                elapsed,
            )
            self._on_result(OcrResult(job_id=task.job_id, text="", error=str(exc)))

    @staticmethod
    def _close_engine(engine: OcrEngine) -> None:
        try:
            engine.close()
        except Exception:
            logger.exception("Failed to close OCR engine")
