"""Ensure only one WaveMash process runs; raise the existing window on relaunch."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Slot
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "WaveMash.SingleInstance.v1"


class SingleInstanceGuard(QObject):
    """Listen for second-instance launches and forward them to the main window."""

    def __init__(self, on_raise: Callable[[], None], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._on_raise = on_raise
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._handle_connection)

    def listen(self) -> bool:
        QLocalServer.removeServer(SERVER_NAME)
        return self._server.listen(SERVER_NAME)

    @Slot()
    def _handle_connection(self) -> None:
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        socket.waitForReadyRead(300)
        socket.readAll()
        socket.disconnectFromServer()
        self._on_raise()


def try_activate_existing_instance() -> bool:
    """If another WaveMash is running, wake it and return True."""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(400):
        return False
    socket.write(b"raise")
    socket.flush()
    socket.waitForBytesWritten(400)
    socket.disconnectFromServer()
    return True
