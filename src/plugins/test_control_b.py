"""
测试控制插件 B

声明需要 NewGameCommand 控制权限
"""
from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSpinBox
from PyQt5.QtCore import pyqtSignal, Qt

from plugin_sdk import BasePlugin, PluginInfo, make_plugin_icon, WindowMode
from shared_types.commands import NewGameCommand
from shared_types.events import VideoSaveEvent


class TestControlWidgetB(QWidget):
    """测试插件 B 的界面"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        self._title = QLabel("测试控制插件 B")
        self._title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self._title)

        self._status = QLabel("状态: 等待初始化...")
        layout.addWidget(self._status)

        # 游戏参数输入
        self._rows_spin = QSpinBox()
        self._rows_spin.setRange(1, 100)
        self._rows_spin.setValue(16)
        layout.addWidget(QLabel("行数:"))
        layout.addWidget(self._rows_spin)

        self._cols_spin = QSpinBox()
        self._cols_spin.setRange(1, 100)
        self._cols_spin.setValue(30)
        layout.addWidget(QLabel("列数:"))
        layout.addWidget(self._cols_spin)

        self._mines_spin = QSpinBox()
        self._mines_spin.setRange(1, 999)
        self._mines_spin.setValue(99)
        layout.addWidget(QLabel("雷数:"))
        layout.addWidget(self._mines_spin)

        self._btn = QPushButton("开始新游戏")
        self._btn.setEnabled(False)
        layout.addWidget(self._btn)

        self._btn.clicked.connect(self._on_click)

    def set_has_permission(self, has: bool) -> None:
        if has:
            self._status.setText("状态: ✅ 已获得 NewGameCommand 权限")
            self._btn.setEnabled(True)
        else:
            self._status.setText("状态: ❌ 未获得 NewGameCommand 权限")
            self._btn.setEnabled(False)

    def get_params(self) -> tuple[int, int, int]:
        return (
            self._rows_spin.value(),
            self._cols_spin.value(),
            self._mines_spin.value(),
        )

    def _on_click(self) -> None:
        # 由插件连接
        pass


class TestControlPluginB(BasePlugin):
    """测试控制插件 B"""

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="test_control_b",
            version="1.0.0",
            author="Test",
            description="测试控制权限 B - NewGameCommand",
            icon=make_plugin_icon("#2196f3", "B"),
            window_mode=WindowMode.TAB,
            required_controls=[NewGameCommand],  # 声明需要的控制权限
        )

    def _setup_subscriptions(self) -> None:
        self.subscribe(VideoSaveEvent, self._on_video_save)

    def _create_widget(self) -> QWidget:
        self._widget = TestControlWidgetB()
        self._widget._btn.clicked.connect(self._on_new_game_click)
        return self._widget

    def on_initialized(self) -> None:
        self.logger.info("TestControlPluginB 初始化")

        # 检查是否有控制权限
        has_auth = self.has_control_auth(NewGameCommand)
        self.logger.info(f"NewGameCommand 权限: {has_auth}")

        # 更新界面
        self.run_on_gui(self._widget.set_has_permission, has_auth)

    def on_control_auth_changed(self, command_type: type, granted: bool) -> None:
        """权限变更回调"""
        if command_type == NewGameCommand:
            self.logger.info(f"NewGameCommand 权限变更: {granted}")
            self.run_on_gui(self._widget.set_has_permission, granted)

    def _on_new_game_click(self) -> None:
        rows, cols, mines = self._widget.get_params()
        if self.has_control_auth(NewGameCommand):
            self.logger.info(f"发送 NewGameCommand: {rows}x{cols}x{mines}")
            self.send_command(NewGameCommand(rows=rows, cols=cols, mines=mines))
        else:
            self.logger.warning("没有 NewGameCommand 权限")

    def _on_video_save(self, event: VideoSaveEvent) -> None:
        self.logger.info(f"收到游戏结束事件: {event.rtime}s")

    def on_shutdown(self) -> None:
        self.logger.info("TestControlPluginB 关闭")