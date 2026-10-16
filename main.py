from __future__ import annotations

import logging
import sys
import traceback

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config import AppConfig, PROJECT_ROOT, resolve_config_path
from app.controller import AppController
from app.logging_setup import configure_logging
from app.services.single_instance import SingleInstanceGuard
from app.ui.theme import apply_theme


def main() -> int:
    load_dotenv(resolve_config_path().parent / ".env")
    if "--self-check" in sys.argv:
        from app.self_check import run_self_check
        return run_self_check(PROJECT_ROOT / "self-check.json")
    app = QApplication(sys.argv)
    apply_theme(app)
    app.setApplicationName("AI Screen Translator")
    app.setQuitOnLastWindowClosed(False)

    instance_guard = SingleInstanceGuard()
    try:
        if not instance_guard.acquire_or_notify("SHOW"):
            return 0
        config = AppConfig.load()
        configure_logging(config)
        app.setApplicationName(config.app.name)

        controller = AppController(app=app, config=config)
        instance_guard.message_received.connect(
            lambda message: controller.show_main_window() if message == "SHOW" else None
        )
        app.aboutToQuit.connect(controller.shutdown)
        app.aboutToQuit.connect(instance_guard.close)
        controller.start()
        return app.exec()
    except Exception as exc:
        logging.exception("Fatal startup error")
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle("AI Screen Translator - Startup error")
        box.setText(str(exc))
        box.setDetailedText(traceback.format_exc())
        box.exec()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
