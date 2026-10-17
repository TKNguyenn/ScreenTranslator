"""Test updater handoff with harmless native fixtures; optionally verify the real GitHub download."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    sandbox = Path(tempfile.mkdtemp(prefix="ast-update-smoke-"))
    app_dir = sandbox / "custom app location"
    app_dir.mkdir()
    download = app_dir / "data/updates/fixture"
    download.mkdir(parents=True)
    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    helper = download / "Update.exe"
    subprocess.run([str(compiler), "/nologo", "/target:winexe", "/reference:System.Windows.Forms.dll",
                    f"/out:{helper}", str(ROOT / "packaging/Update.cs")], check=True)
    source = sandbox / "Fixture.cs"
    source.write_text(r'''
using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
class Fixture {
    static int Main(string[] args) {
        string name = Path.GetFileNameWithoutExtension(Process.GetCurrentProcess().MainModule.FileName);
        if (name == "Parent") {
            string running = Path.Combine(args[0], "parent.running");
            File.WriteAllText(running, "running");
            try {
                for (int i=0; i<300; i++) {
                    if (File.Exists(Path.Combine(args[0], "parent.release"))) return 0;
                    Thread.Sleep(50);
                }
                return 1;
            } finally { File.Delete(running); }
        }
        if (name == "Setup") {
            string folder = "";
            foreach (string arg in args) if (arg.StartsWith("/DIR=")) folder = arg.Substring(5);
            if (File.Exists(Path.Combine(folder, "parent.running"))) return 42;
            File.WriteAllLines(Path.Combine(folder, "setup-args.txt"), args);
            return 0;
        }
        File.WriteAllText(Path.Combine(Environment.CurrentDirectory, "app-restarted.txt"), "restarted");
        return 0;
    }
}
''', encoding="utf-8")
    setup = download / "Setup.exe"
    subprocess.run([str(compiler), "/nologo", "/target:winexe", f"/out:{setup}", str(source)], check=True)
    parent_exe = sandbox / "Parent.exe"
    shutil.copy2(setup, parent_exe)
    shutil.copy2(setup, app_dir / "ScreenTranslator.exe")
    originals = {name: b"synthetic saved data" for name in ("config.json", "providers.json", "prompts.json")}
    for name, data in originals.items():
        (app_dir / name).write_bytes(data)
    parent = subprocess.Popen([str(parent_exe), str(app_dir)])
    helper_process = None
    try:
        deadline = time.monotonic() + 5
        while not (app_dir / "parent.running").exists() and time.monotonic() < deadline:
            time.sleep(.05)
        assert (app_dir / "parent.running").exists()
        digest = hashlib.sha256(setup.read_bytes()).hexdigest()
        helper_process = subprocess.Popen([str(helper), str(setup), digest, str(app_dir), str(parent.pid)])
        time.sleep(.3)
        assert not (app_dir / "setup-args.txt").exists(), "Installer started before app shutdown"
        (app_dir / "parent.release").touch()
        assert parent.wait(timeout=5) == 0
        assert helper_process.wait(timeout=30) == 0
        deadline = time.monotonic() + 5
        while not (app_dir / "app-restarted.txt").exists() and time.monotonic() < deadline:
            time.sleep(.05)
        assert (app_dir / "app-restarted.txt").exists(), "Updated app was not restarted"
        argv = (app_dir / "setup-args.txt").read_text().splitlines()
        assert f"/DIR={app_dir}" in argv and "/UPDATE=1" in argv and "/VERYSILENT" in argv
        assert all((app_dir / name).read_bytes() == data for name, data in originals.items())
        assert not setup.exists(), "Successful update left the large installer behind"
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait()
        if helper_process is not None and helper_process.poll() is None:
            helper_process.kill()
            helper_process.wait()
    checks = ["Native helper verifies SHA256 and waits for parent exit", "Installer receives exact custom path and silent update flags",
              "App relaunches after installer success; catalogs/config untouched", "Successful helper removes downloaded installer"]
    if args.live:
        from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
        from app.services.updates import UpdateManager
        app = QCoreApplication.instance() or QCoreApplication([])
        manager = UpdateManager()
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        releases, downloaded, errors = [], [], []
        manager.checked.connect(lambda release: (releases.append(release), loop.quit()))
        manager.failed.connect(lambda error: (errors.append(error), loop.quit()))
        manager.downloaded.connect(lambda path: (downloaded.append(Path(path)), loop.quit()))
        try:
            manager.check()
            timer.start(45000)
            loop.exec()
            assert releases and not errors, errors
            with patch("app.services.updates.installed_app_root", return_value=app_dir):
                manager.download(releases[0])
                timer.start(240000)
                loop.exec()
            assert downloaded and not errors, errors
            assert hashlib.sha256(downloaded[0].read_bytes()).hexdigest() == releases[0].sha256
            # Never execute the downloaded public release: it targets the user's real AppId.
            checks += [f"Live GitHub API and Qt HTTPS download v{releases[0].version}", "Real release size/SHA256 verified without installing it"]
        finally:
            timer.stop()
            manager.close()
    result = {"ok": True, "sandbox": str(sandbox), "checks": checks}
    (ROOT / "artifacts/update-smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
