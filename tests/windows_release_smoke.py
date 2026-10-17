"""Build a sandbox installer, test the real frozen app, then uninstall only the sandbox."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from uuid import uuid4
import winreg

ROOT = Path(__file__).resolve().parents[1]


def known_folder(csidl):
    buffer = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
    return Path(buffer.value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iscc", type=Path, default=ROOT / ".build-tools/InnoSetup/ISCC.exe")
    args = parser.parse_args()
    assert os.name == "nt"
    assert (ROOT / "dist/ScreenTranslator/ScreenTranslator.exe").is_file(), "Build the exe first"
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="ast-release-smoke-")).resolve()
    assert sandbox.parent == Path(tempfile.gettempdir()).resolve() and sandbox.name.startswith("ast-release-smoke-")
    default_dir = sandbox / "default-app"
    app_dir = sandbox / "custom install location" / "app"
    local = sandbox / "local"
    user_data = app_dir
    legacy_data = local / "AIScreenTranslator"
    shortcut_name = "AI Screen Translator Test " + uuid4().hex[:8]
    install_id = "AIScreenTranslator-Test-" + uuid4().hex
    sentinel = sandbox / "unrelated-file.txt"
    sentinel.write_text("must survive uninstall", encoding="utf-8")
    launcher_source = sandbox / "Uninstall.cs"
    launcher_source.write_text((ROOT / "packaging/Uninstall.cs").read_text().replace(
        "AIScreenTranslator-96F65CB7-531C-4202-B340-B90251E5B2AC", install_id))
    launcher = sandbox / "Uninstall.exe"
    compiler_cs = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    subprocess.run([str(compiler_cs), "/nologo", "/target:winexe", "/reference:System.Windows.Forms.dll",
                    f"/out:{launcher}", str(launcher_source)], check=True)
    compiler = [str(args.iscc), "/Qp", f"/O{sandbox}", "/DSetupName=SandboxSetup",
                f"/DInstallId={install_id}", f"/DInstallDir={default_dir}",
                f"/DLegacyDataDir={legacy_data}", f"/DShortcutName={shortcut_name}",
                f"/DLauncherPath={launcher}",
                str(ROOT / "packaging/installer.iss")]
    subprocess.run(compiler, check=True, timeout=300)
    setup = sandbox / "SandboxSetup.exe"
    install_args = [str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-",
                    f"/DIR={app_dir}", f"/LOG={sandbox / 'install.log'}"]
    # Upgrade a legacy install whose append-only uninstall log deletes the old data root.
    legacy_data.mkdir(parents=True)
    for name in ("config.json", "providers.json", "prompts.json"):
        (legacy_data / name).write_bytes((ROOT / "app/defaults" / name).read_bytes())
    old_config = json.loads((legacy_data / "config.json").read_text(encoding="utf-8"))
    old_config["translation"]["target_language"] = "zh-Hant"
    (legacy_data / "config.json").write_text(json.dumps(old_config), encoding="utf-8")
    (legacy_data / ".env").write_text("# synthetic migration fixture\n")
    (legacy_data / "data/logs").mkdir(parents=True)
    (legacy_data / "data/logs/old.log").write_text("legacy log")
    old_script = sandbox / "legacy.iss"
    old_script.write_text(
        f'[Setup]\nAppId={install_id}\nAppName=AI Screen Translator Test\nAppVersion=0.4.1.7\n'
        f'DefaultDirName={app_dir}\nPrivilegesRequired=lowest\nArchitecturesInstallIn64BitMode=x64compatible\n'
        f'OutputDir={sandbox}\nOutputBaseFilename=LegacySetup\nUninstallLogMode=append\n'
        f'[Files]\nSource: "{sentinel}"; DestDir: "{{app}}"; DestName: "README.txt"\n'
        f'[UninstallDelete]\nType: filesandordirs; Name: "{legacy_data}"\n', encoding="utf-8")
    subprocess.run([str(args.iscc), "/Qp", str(old_script)], check=True, timeout=30)
    subprocess.run([str(sandbox / "LegacySetup.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/SP-"],
                   check=True, timeout=60)
    too_long = sandbox / ("long-folder-" * 10) / ("nest-" * 6)
    assert 180 < len(str(too_long)) < 250
    rejected = subprocess.run([arg for arg in install_args if not arg.startswith("/DIR=")]
                              + [f"/DIR={too_long}"], timeout=180)
    assert rejected.returncode != 0 and not too_long.exists(), "Unsafe long path was accepted"
    nested_legacy = legacy_data / "data/nested-app"
    rejected = subprocess.run([arg for arg in install_args if not arg.startswith("/DIR=")]
                              + [f"/DIR={nested_legacy}"], timeout=180)
    assert rejected.returncode != 0 and not nested_legacy.exists(), "Recursive legacy migration path was accepted"
    subprocess.run(install_args, check=True, timeout=180)
    exe = app_dir / "ScreenTranslator.exe"
    uninstaller = app_dir / "unins000.exe"
    assert exe.is_file() and uninstaller.is_file() and (app_dir / "Uninstall.exe").is_file()
    assert (app_dir / "Update.exe").is_file(), "Update helper is missing from installed app"
    assert not (app_dir / "Uninstall.bat").exists()
    assert not default_dir.exists(), "Custom install path was ignored"
    desktop_link = known_folder(0x10) / (shortcut_name + ".lnk")
    menu = known_folder(0x02) / shortcut_name
    assert desktop_link.is_file() and menu.is_dir()
    for name in ("config.json", "providers.json", "prompts.json", ".env", "data/logs/old.log"):
        assert (user_data / name).read_bytes() == (legacy_data / name).read_bytes(), f"Migration failed: {name}"
    environment = dict(os.environ, LOCALAPPDATA=str(local))
    for name in ("APP_CONFIG_PATH", "PROVIDER_CATALOG_PATH", "PROMPT_CATALOG_PATH", "QT_QPA_PLATFORM", "PYTHONPATH"):
        environment.pop(name, None)
    # Launch the bundled exe from an unrelated working directory, with no source imports.
    subprocess.run([str(exe), "--self-check"], cwd=sandbox, env=environment, check=True, timeout=180)
    report = json.loads((user_data / "self-check.json").read_text(encoding="utf-8"))
    assert report["ok"], report
    (artifacts / "release-self-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    raw = json.loads((user_data / "config.json").read_text(encoding="utf-8"))
    raw["translation"]["target_language"] = "en"
    (user_data / "config.json").write_text(json.dumps(raw), encoding="utf-8")
    subprocess.run(install_args, check=True, timeout=180)
    assert json.loads((user_data / "config.json").read_text(encoding="utf-8"))["translation"]["target_language"] == "en"
    assert (legacy_data / "config.json").read_text() != (user_data / "config.json").read_text()
    # Create representative user files, all strictly inside the sandbox's app-owned data directory.
    data = user_data / "data"
    (data / "logs").mkdir(parents=True, exist_ok=True)
    (data / "logs/app.log").write_text("synthetic log", encoding="utf-8")
    (data / "translation_cache.sqlite3").write_bytes(b"synthetic cache")
    unrelated_in_app = app_dir / "my-own-file.txt"
    unrelated_in_app.write_text("must survive uninstall")
    catalogs = {name: (user_data / name).read_bytes() + b"\n "
                for name in ("providers.json", "prompts.json")}
    for name, content in catalogs.items():
        (user_data / name).write_bytes(content)
    outside_dir = sandbox / "unrelated-directory"
    outside_dir.mkdir()
    (outside_dir / "keep.txt").write_text("keep", encoding="utf-8")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(data / "junction"), str(outside_dir)],
                   check=True, capture_output=True)
    uninstall_command = [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                         f"/LOG={sandbox / 'uninstall.log'}"]
    create_mutex = ctypes.windll.kernel32.CreateMutexW
    create_mutex.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    create_mutex.restype = wintypes.HANDLE
    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    mutex = create_mutex(None, False, "Local\\AIScreenTranslator_Running")
    assert mutex
    try:
        blocked = subprocess.run(uninstall_command, cwd=sandbox, timeout=30)
        assert blocked.returncode != 0 and exe.is_file() and user_data.is_dir(), "Running-app guard failed"
    finally:
        close_handle(mutex)
    invalid = subprocess.run(uninstall_command + ["/DATA=invalid"], cwd=sandbox, timeout=30)
    assert invalid.returncode != 0 and exe.is_file() and user_data.is_dir(), "Invalid mode removed files"
    # If a catalog cannot be copied, uninstall must stop before deleting app/data.
    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create_file.restype = wintypes.HANDLE
    locked = create_file(str(user_data / "providers.json"), 0x80000000, 0, None, 3, 0, None)
    assert locked not in (None, ctypes.c_void_p(-1).value)
    try:
        blocked = subprocess.run(uninstall_command, cwd=sandbox, timeout=30)
        assert blocked.returncode != 0 and exe.is_file() and user_data.is_dir(), "Backup failure deleted app/data"
    finally:
        close_handle(locked)
    # The standalone exe resolves a custom location; no /DATA defaults to keep.
    subprocess.run([str(launcher), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                   cwd=sandbox, check=True, timeout=30)
    # Inno launches a temporary uninstaller; allow it to remove its own original exe.
    deadline = time.monotonic() + 30
    while ((app_dir / "unins000.exe").exists() or (app_dir / "config.json").exists()
           or list(local.glob("AIScreenTranslator.keep-*"))) and time.monotonic() < deadline:
        time.sleep(.2)
    assert {path.name for path in user_data.iterdir()} == set(catalogs) | {unrelated_in_app.name}, "Keep mode retained app files"
    assert unrelated_in_app.read_text() == "must survive uninstall"
    assert not legacy_data.exists(), "Legacy app data was not removed"
    assert all((user_data / name).read_bytes() == content for name, content in catalogs.items())
    assert not list(local.glob("AIScreenTranslator.keep-*")), "Recovery folder left after successful preservation"
    assert (outside_dir / "keep.txt").read_text() == "keep"
    subprocess.run(install_args, check=True, timeout=180)
    assert all((user_data / name).read_bytes() == content for name, content in catalogs.items()), "Reinstall overwrote catalogs"
    # Add data again and exercise full removal through the installed launcher.
    (user_data / "config.json").write_text("synthetic settings")
    data.mkdir(exist_ok=True)
    (data / "cache.sqlite3").write_bytes(b"synthetic cache")
    subprocess.run([str(app_dir / "Uninstall.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DATA=all"],
                   cwd=sandbox, check=True, timeout=30)
    deadline = time.monotonic() + 30
    while (app_dir / "unins000.exe").exists() and time.monotonic() < deadline:
        time.sleep(.2)
    assert {path.name for path in app_dir.iterdir()} == {unrelated_in_app.name}, "Full uninstall left app data/files"
    assert unrelated_in_app.read_text() == "must survive uninstall"
    unrelated_in_app.unlink()
    app_dir.rmdir()
    # A clean reinstall has no legacy source; full removal should remove the now-empty root too.
    subprocess.run(install_args + ["/UPDATE=1"], check=True, timeout=180)
    assert not desktop_link.exists(), "Silent update recreated a desktop shortcut the user omitted"
    subprocess.run([str(app_dir / "Uninstall.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DATA=all"],
                   cwd=sandbox, check=True, timeout=30)
    deadline = time.monotonic() + 30
    while app_dir.exists() and time.monotonic() < deadline:
        time.sleep(.2)
    assert not app_dir.exists(), "Clean full uninstall left an empty installation directory"
    assert not desktop_link.exists() and not menu.exists(), "Uninstall left shortcuts behind"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{install_id}_is1"):
            raise AssertionError("Uninstall registration remains")
    except FileNotFoundError:
        pass
    assert sentinel.read_text(encoding="utf-8") == "must survive uninstall"
    assert (outside_dir / "keep.txt").read_text(encoding="utf-8") == "keep"
    result = {"ok": True, "sandbox": str(sandbox), "checks": report["checks"] + [
        "Long/nested legacy install paths rejected before file installation", "Custom install path and standalone Uninstall.exe",
        "Keep mode retains exactly providers.json/prompts.json byte-for-byte; reinstall preserves both",
        "Locked catalog aborts uninstall without deleting app/data", "Full removal through installed Uninstall.exe",
        "Config, catalogs, dotenv and logs migrate from legacy data without changing originals during setup",
        "App/config/data share the chosen install folder; reinstall retains local config",
        "Old unconditional uninstall log is safe with relocated catalogs",
        "Update helper installed; silent update does not recreate an omitted desktop shortcut",
        "Uninstall removes app, config/cache/logs, shortcuts and registry entry",
        "Running-app mutex blocks uninstall", "Unrelated sentinel and junction target survive"]}
    (artifacts / "release-install-uninstall.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
