"""Native Windows provider UI smoke using synthetic config, no API or hooks."""
from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from app.config import AppConfig, ProviderProfile, ProviderSection
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def main():
    app = QApplication([])
    if os.name != "nt" or app.platformName() != "windows":
        raise SystemExit("Native Windows Qt required")
    apply_theme(app)
    config = AppConfig(providers=ProviderSection(active_profile="Synthetic AI", profiles={
        "Synthetic AI": ProviderProfile(model="test-model", api_key=""),
    }))
    window = MainWindow(app, config)
    window.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
    window.setAttribute(Qt.WA_ShowWithoutActivating, True)
    window.move(-32000, -32000)
    output = Path(__file__).resolve().parents[1] / "artifacts" / "google-v0415"
    output.mkdir(parents=True, exist_ok=True)
    try:
        window.resize(900, 620)
        window._nav.setCurrentRow(1)
        window.show()
        for name, filename in (("Google Translate Free", "google-free.png"),
                               ("Google Cloud Translate", "google-cloud.png")):
            window._add_google_provider(name)
            app.processEvents()
            assert window._active_profile_combo.currentText() == "Synthetic AI"
            assert not window._endpoint_combo.isEnabled()
            assert not window._stream_quality.isEnabled()
            assert window._models_group.isHidden()
            assert window._stream_group.isHidden()
            assert window._api_key_edit.isEnabled() == (name == "Google Cloud Translate")
            page = window._pages.widget(1)
            assert page.widget().minimumSizeHint().width() <= page.viewport().width()
            assert window.grab().save(str(output / filename))
        window._provider_list.setCurrentRow(0)
        assert window._endpoint_combo.isEnabled()
        assert window._stream_quality.isEnabled()
        assert not window._models_group.isHidden()
        assert not window._stream_group.isHidden()
        assert window._api_key_edit.isEnabled()
        print("PASS: native Google preset forms, compact layout, active provider retained, AI controls restored")
    finally:
        window.allow_close()
        window.close()


if __name__ == "__main__":
    main()
