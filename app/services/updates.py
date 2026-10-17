"""GitHub stable releases and asynchronous, verified Windows installer downloads."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from app.version import APP_VERSION

REPOSITORY = "TKNguyenn/ScreenTranslator"
UPDATES_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"


def version_tuple(version: str) -> tuple[int, ...]:
    if not isinstance(version, str) or not re.fullmatch(r"v?[0-9]{1,5}(?:\.[0-9]{1,5}){2,3}", version):
        raise ValueError("GitHub trả về phiên bản không hợp lệ.")
    numbers = tuple(int(part) for part in version.removeprefix("v").split("."))
    return numbers + (0,) * (4 - len(numbers))


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    size: int
    sha256: str


def parse_release(payload: dict) -> Release:
    if not isinstance(payload, dict) or payload.get("draft") is not False or payload.get("prerelease") is not False:
        raise ValueError("Không tìm thấy bản phát hành ổn định hợp lệ.")
    tag = payload.get("tag_name")
    version_tuple(tag)
    version = tag.removeprefix("v")
    name = f"AI-Screen-Translator-{version}-Setup.exe"
    expected_url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ValueError("Danh sách file phát hành trên GitHub không hợp lệ.")
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("name") != name:
            continue
        size, digest = asset.get("size"), asset.get("digest")
        if (asset.get("browser_download_url") != expected_url or type(size) is not int
                or not 0 < size <= 1024 ** 3 or not isinstance(digest, str)
                or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest)):
            raise ValueError(f"Bộ cài v{version} chưa có URL, kích thước hoặc SHA256 hợp lệ trên GitHub.")
        return Release(version, expected_url, size, digest[7:].lower())
    raise ValueError(f"Bản v{version} chưa đính kèm {name} trên GitHub Releases.")


def installed_app_root() -> Path:
    root = Path(sys.executable).resolve().parent
    if (not getattr(sys, "frozen", False) or sys.platform != "win32"
            or not (root / "unins000.exe").is_file() or not (root / "Update.exe").is_file()):
        raise RuntimeError("Cập nhật tự động chỉ dùng trong bản Windows đã cài bằng Setup. Bản chạy Python cần cập nhật source bằng Git.")
    return root


def launch_installer(installer: Path, sha256: str) -> None:
    root = installed_app_root()
    # A separate copy lets Setup replace the installed helper while this copy is running.
    helper = installer.parent / "Update.exe"
    shutil.copy2(root / "Update.exe", helper)
    subprocess.Popen([str(helper), str(installer), sha256, str(root), str(os.getpid())],
                     cwd=str(installer.parent), close_fds=True,
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)


class UpdateManager(QObject):
    checked = Signal(object)
    downloaded = Signal(str)
    progress = Signal(int)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)
        self._reply = None
        self._metadata = bytearray()
        self._download_dir: Path | None = None
        self._file = None
        self._release: Release | None = None
        self._hash = hashlib.sha256()
        self._received = 0

    def _request(self, url: str) -> QNetworkReply:
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", f"AI-Screen-Translator/{APP_VERSION}".encode("ascii"))
        request.setRawHeader(b"Accept", b"application/vnd.github+json" if url == UPDATES_API else b"application/octet-stream")
        request.setTransferTimeout(30000)
        request.setMaximumRedirectsAllowed(5)
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.NoLessSafeRedirectPolicy)
        reply = self._network.get(request)
        reply.setReadBufferSize(1024 * 1024)
        return reply

    def check(self) -> None:
        if self._reply is not None:
            return
        self._metadata.clear()
        self._reply = self._request(UPDATES_API)
        self._reply.readyRead.connect(self._read_metadata)
        self._reply.finished.connect(self._check_finished)

    def _read_metadata(self) -> None:
        if self._reply is None:
            return
        self._metadata.extend(bytes(self._reply.readAll()))
        if len(self._metadata) > 1024 * 1024:
            self._fail("Phản hồi GitHub quá lớn. Hãy thử lại sau.")

    def _network_error(self) -> str | None:
        if self._reply.error() == QNetworkReply.NoError:
            return None
        status = self._reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status in (403, 429):
            return "GitHub đang giới hạn yêu cầu. Hãy thử lại sau."
        if status == 404:
            return "Không tìm thấy release hoặc bộ cài trên GitHub."
        return "Không kết nối được GitHub hoặc tải bị gián đoạn. Kiểm tra mạng rồi thử lại."

    def _check_finished(self) -> None:
        if self._reply is None:
            return
        error = self._network_error()
        if error:
            self._fail(error)
            return
        self._read_metadata()
        if self._reply is None:
            return
        try:
            release = parse_release(json.loads(self._metadata))
        except (ValueError, TypeError) as exc:
            self._fail(str(exc) if not isinstance(exc, json.JSONDecodeError) else "Phản hồi GitHub không hợp lệ.")
            return
        self._discard_reply()
        self.checked.emit(release)

    def download(self, release: Release) -> None:
        if self._reply is not None:
            return
        self.close()
        self._release = release
        self._hash = hashlib.sha256()
        self._received = 0
        try:
            cache = installed_app_root() / "data" / "updates"
            cache.mkdir(parents=True, exist_ok=True)
            self._download_dir = Path(tempfile.mkdtemp(prefix="update-", dir=cache))
            self._file = (self._download_dir / "download.part").open("wb")
        except (OSError, RuntimeError):
            self._fail("Không tạo được file tải về. Kiểm tra dung lượng và quyền ghi thư mục tạm.")
            return
        self._reply = self._request(release.url)
        self._reply.readyRead.connect(self._read_download)
        self._reply.finished.connect(self._download_finished)

    def _read_download(self) -> None:
        if self._reply is None:
            return
        chunk = bytes(self._reply.readAll())
        self._received += len(chunk)
        if self._received > self._release.size:
            self._fail("Kích thước bộ cài khác thông tin GitHub. Đã hủy cập nhật.")
            return
        try:
            self._file.write(chunk)
        except OSError:
            self._fail("Không ghi được bộ cài. Kiểm tra dung lượng ổ đĩa rồi thử lại.")
            return
        self._hash.update(chunk)
        self.progress.emit(min(99, self._received * 100 // self._release.size))

    def _download_finished(self) -> None:
        if self._reply is None:
            return
        error = self._network_error()
        if error:
            self._fail(error)
            return
        self._read_download()
        if self._reply is None:
            return
        try:
            self._file.close()
            self._file = None
            if self._received != self._release.size or self._hash.hexdigest() != self._release.sha256:
                raise ValueError("SHA256 hoặc kích thước bộ cài không khớp. Đã hủy cập nhật; app chưa thay đổi.")
            path = self._download_dir / f"AI-Screen-Translator-{self._release.version}-Setup.exe"
            (self._download_dir / "download.part").rename(path)
        except (OSError, ValueError) as exc:
            self._fail(str(exc))
            return
        self._discard_reply()
        self.progress.emit(100)
        self.downloaded.emit(str(path))

    def keep_download_for_installer(self) -> None:
        self._download_dir = None

    def _discard_reply(self) -> None:
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.blockSignals(True)
            reply.abort()
            reply.deleteLater()

    def close(self) -> None:
        self._discard_reply()
        if self._file is not None:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
        if self._download_dir is not None:
            shutil.rmtree(self._download_dir, ignore_errors=True)
            self._download_dir = None

    def _fail(self, message: str) -> None:
        self.close()
        self.failed.emit(message)
