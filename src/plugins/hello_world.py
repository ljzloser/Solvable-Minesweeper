"""
Hello World 示例插件

演示基本的事件订阅、pyqtSignal 跨线程 GUI 更新。
"""
from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import pyqtSignal

from plugin_manager import BasePlugin, PluginInfo, make_plugin_icon, WindowMode
from shared_types.events import VideoSaveEvent


class HelloWidget(QWidget):
    """简单的 UI 界面"""

    _update_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0

        layout = QVBoxLayout(self)

        self._title = QLabel("Hello World Plugin")
        self._title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(self._title)

        self._info = QLabel("Waiting for game data...")
        layout.addWidget(self._info)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log)

        self._update_signal.connect(self._append_log)

    def _append_log(self, text: str):
        """Slot: executed on main thread"""
        self._log.append(text)
        self._count += 1
        self._info.setText(f"Received {self._count} record(s)")


class HelloPlugin(BasePlugin):

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="hello_world",
            version="1.0.0",
            author="Example",
            description="Hello World - demonstrates event subscription and pyqtSignal GUI update",
            icon=make_plugin_icon("#4CAF50", "H", 64),
            window_mode=WindowMode.TAB,
        )

    def _setup_subscriptions(self) -> None:
        self.subscribe(VideoSaveEvent, self._on_video_save)

    def _create_widget(self) -> QWidget:
        self._widget = HelloWidget()
        return self._widget

    def on_initialized(self) -> None:
        self.logger.info("HelloPlugin initialized")

    def on_shutdown(self) -> None:
        self.logger.info("HelloPlugin shutting down")

    def _on_video_save(self, event: VideoSaveEvent):
        self.logger.info(
            f"Game: time={event.rtime}s, level={event.level}, "
            f"3BV={event.bbbv}, L={event.left} R={event.right}"
        )
        info_text = (
            f"[{event.rtime:.2f}s] {event.level} | "
            f"3BV={event.bbbv} | L={event.left} R={event.right}"
        )
        # pyqtSignal emit -> auto QueuedConnection cross-thread to main thread
        self._widget._update_signal.emit(info_text)
