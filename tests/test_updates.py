from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QObject, QTimer
from PySide6.QtNetwork import QNetworkReply

from app.services import updates


def release_payload(content=b"installer", version="0.4.1.10"):
    name = f"AI-Screen-Translator-{version}-Setup.exe"
    return {"tag_name": "v" + version, "draft": False, "prerelease": False, "assets": [{
        "name": name, "size": len(content), "state": "uploaded",
        "browser_download_url": f"https://github.com/TKNguyenn/ScreenTranslator/releases/download/v{version}/{name}",
        "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
    }]}


class ReleaseTests(unittest.TestCase):
    def test_numeric_versions_do_not_downgrade_or_compare_as_strings(self):
        self.assertGreater(updates.version_tuple("v0.4.1.10"), updates.version_tuple("0.4.1.9"))
        self.assertEqual(updates.version_tuple("1.2.3"), updates.version_tuple("1.2.3.0"))
        for invalid in ("latest", "v1.2.3-beta", "1.2", "1.2.3.4.5"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                updates.version_tuple(invalid)

    def test_release_selects_exact_installer_and_requires_github_hash(self):
        payload = release_payload()
        payload["assets"].insert(0, {"name": "Uninstall.exe"})
        info = updates.parse_release(payload)
        self.assertEqual(info.version, "0.4.1.10")
        self.assertEqual(info.size, len(b"installer"))
        self.assertEqual(info.sha256, hashlib.sha256(b"installer").hexdigest())
        for field, value in (("digest", None), ("size", -1), ("size", True),
                             ("browser_download_url", "https://evil.test/Setup.exe")):
            with self.subTest(field=field):
                broken = release_payload()
                broken["assets"][0][field] = value
                with self.assertRaises(ValueError):
                    updates.parse_release(broken)
        for key in ("draft", "prerelease"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                updates.parse_release(dict(release_payload(), **{key: True}))
        with self.assertRaises(ValueError):
            updates.parse_release(dict(release_payload(), assets=[]))

    def test_source_run_cannot_launch_installer_and_frozen_arguments_preserve_paths(self):
        with tempfile.TemporaryDirectory(prefix="ast-update-unit-") as tmp:
            root = Path(tmp)
            app = root / "custom app"
            app.mkdir()
            setup = root / "Setup.exe"
            setup.write_bytes(b"fixture")
            with patch.object(updates.sys, "frozen", False, create=True), self.assertRaises(RuntimeError):
                updates.launch_installer(setup, "0" * 64)
            (app / "Update.exe").write_bytes(b"helper fixture")
            (app / "unins000.exe").write_bytes(b"installed")
            with patch.object(updates.sys, "frozen", True, create=True), \
                 patch.object(updates.sys, "executable", str(app / "ScreenTranslator.exe")), \
                 patch.object(updates.subprocess, "Popen") as launch:
                updates.launch_installer(setup, hashlib.sha256(b"fixture").hexdigest())
                argv = launch.call_args.args[0]
                self.assertEqual(Path(argv[0]).parent, setup.parent)
                self.assertEqual(argv[1:4], [str(setup), hashlib.sha256(b"fixture").hexdigest(), str(app)])
                self.assertEqual(argv[4], str(os.getpid()))


class UpdateManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Other widget tests may share this process, so keep QApplication semantics.
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_verified_download_emits_only_after_exact_size_and_hash_match(self):
        # Exercise the download integrity gate without downloading or executing an installer.
        from PySide6.QtCore import QByteArray
        class Reply(QObject):
            def __init__(self, data):
                super().__init__()
                self.data = data
            def readAll(self):
                data, self.data = self.data, b""
                return QByteArray(data)
            def error(self):
                return QNetworkReply.NoError
            def abort(self):
                pass
            def deleteLater(self):
                pass
        for received, ok in ((b"installer", True), (b"corrupted", False), (b"short", False),
                             (b"installer-extra", False)):
            with self.subTest(received=received):
                manager = updates.UpdateManager()
                manager._release = updates.parse_release(release_payload())
                manager._download_dir = Path(tempfile.mkdtemp(prefix="ast-update-unit-"))
                manager._file = (manager._download_dir / "download.part").open("wb")
                manager._hash = hashlib.sha256()
                manager._received = 0
                manager._reply = Reply(received)
                completed, errors = [], []
                manager.downloaded.connect(completed.append)
                manager.failed.connect(errors.append)
                manager._read_download()
                if manager._reply is not None:
                    manager._download_finished()
                self.assertEqual(bool(completed), ok)
                self.assertEqual(bool(errors), not ok)
                if ok:
                    self.assertEqual(Path(completed[0]).read_bytes(), received)
                else:
                    self.assertIsNone(manager._download_dir)
                manager.close()

    def test_cancel_cleans_partial_download_and_does_not_emit_ready(self):
        manager = updates.UpdateManager()
        manager._download_dir = Path(tempfile.mkdtemp(prefix="ast-update-unit-"))
        folder = manager._download_dir
        manager._file = (folder / "download.part").open("wb")
        manager._file.write(b"partial")
        completed = []
        manager.downloaded.connect(completed.append)
        manager.close()
        self.assertFalse(folder.exists())
        self.assertEqual(completed, [])

    def test_real_qt_requests_retry_after_http_error_and_download_verified_bytes(self):
        content = b"fixture installer" * 4096
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/limited":
                    self.send_error(403)
                    return
                body = content if self.path == "/installer" else json.dumps(release_payload(content)).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        manager = updates.UpdateManager()
        checked, errors, completed = [], [], []
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        manager.checked.connect(lambda result: (checked.append(result), loop.quit()))
        manager.failed.connect(lambda error: (errors.append(error), loop.quit()))
        manager.downloaded.connect(lambda path: (completed.append(Path(path)), loop.quit()))
        try:
            with patch.object(updates, "UPDATES_API", base + "/limited"):
                manager.check()
                timer.start(5000)
                loop.exec()
            self.assertEqual(len(errors), 1, "HTTP error did not finish asynchronously")
            self.assertIsNone(manager._reply)
            with patch.object(updates, "UPDATES_API", base + "/latest"):
                manager.check()
                timer.start(5000)
                loop.exec()
            self.assertEqual(len(checked), 1, "Retry did not return a release")
            original_request = manager._request
            with tempfile.TemporaryDirectory(prefix="ast-update-network-") as tmp, \
                 patch.object(updates, "installed_app_root", return_value=Path(tmp)), \
                 patch.object(manager, "_request", side_effect=lambda _url: original_request(base + "/installer")):
                manager.download(checked[0])
                timer.start(5000)
                loop.exec()
                self.assertEqual(len(completed), 1)
                self.assertEqual(completed[0].read_bytes(), content)
                self.assertTrue(completed[0].is_relative_to(Path(tmp) / "data/updates"))
                manager.close()
        finally:
            timer.stop()
            manager.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
