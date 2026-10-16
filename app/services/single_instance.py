from __future__ import annotations

import ctypes
import sys
from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGuard(QObject):
    """Ensure only one application instance owns the tray/hotkeys.

    A second launch sends a short SHOW message to the first instance and exits.
    """

    message_received = Signal(str)

    def __init__(self, server_name: str = "AI_Screen_Translator") -> None:
        super().__init__()
        self._server_name = server_name
        self._server = QLocalServer(self)
        self._installer_mutex = None
        self._server.newConnection.connect(self._drain_connections)

    def acquire_or_notify(self, message: str = "SHOW") -> bool:
        probe = QLocalSocket()
        probe.connectToServer(self._server_name)
        if probe.waitForConnected(180):
            payload = (message.strip() + "\n").encode("utf-8")
            probe.write(payload)
            probe.flush()
            probe.waitForBytesWritten(180)
            probe.disconnectFromServer()
            return False

        # Remove a stale local endpoint left behind by an unclean shutdown.
        QLocalServer.removeServer(self._server_name)
        if not self._server.listen(self._server_name):
            raise RuntimeError(
                f"Cannot create single-instance server '{self._server_name}': "
                f"{self._server.errorString()}"
            )
        if getattr(sys, "frozen", False) and sys.platform == "win32":
            create_mutex = ctypes.windll.kernel32.CreateMutexW
            create_mutex.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
            create_mutex.restype = ctypes.c_void_p
            # Inno Setup uses this mutex to require exit before install/uninstall.
            self._installer_mutex = create_mutex(None, False, "Local\\AIScreenTranslator_Running")
        return True

    def close(self) -> None:
        if self._server.isListening():
            self._server.close()
        QLocalServer.removeServer(self._server_name)
        if self._installer_mutex:
            close_handle = ctypes.windll.kernel32.CloseHandle
            close_handle.argtypes = [ctypes.c_void_p]
            close_handle.restype = ctypes.c_bool
            close_handle(self._installer_mutex)
            self._installer_mutex = None

    def _drain_connections(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            if not socket.waitForReadyRead(200):
                socket.disconnectFromServer()
                continue
            data = bytes(socket.readAll()).decode("utf-8", errors="replace")
            message = data.strip() or "SHOW"
            self.message_received.emit(message)
            socket.disconnectFromServer()
