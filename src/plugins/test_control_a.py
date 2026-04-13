"""
测试控制插件 A

声明需要 NewGameCommand 控制权限
"""
from __future__ import annotations

from PyQt5.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal

from plugin_sdk import BasePlugin, PluginInfo, make_plugin_icon, WindowMode
from shared_types.commands import NewGameCommand
from shared_types.events import VideoSaveEvent


class TestControlWidgetA(QWidget):
    """测试插件 A 的界面"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        self._title = QLabel("测试控制插件 A")
        self._title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self._title)

        self._status = QLabel("状态: 等待初始化...")
        layout.addWidget(self._status)

        self._btn = QPushButton("开始新游戏 (16x30x99)")
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

    def _on_click(self) -> None:
        # 由插件连接
        pass


class TestControlPluginA(BasePlugin):
    """测试控制插件 A"""

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="test_control_a",
            version="1.0.0",
            author="Test",
            description="测试控制权限 A - NewGameCommand",
            icon=make_plugin_icon("#e91e63", "A"),
            window_mode=WindowMode.TAB,
            required_controls=[NewGameCommand],  # 声明需要的控制权限
        )

    def _setup_subscriptions(self) -> None:
        self.subscribe(VideoSaveEvent, self._on_video_save)

    def _create_widget(self) -> QWidget:
        self._widget = TestControlWidgetA()
        self._widget._btn.clicked.connect(self._on_new_game_click)
        return self._widget

    def on_initialized(self) -> None:
        self.logger.info("TestControlPluginA 初始化")

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
        if self.has_control_auth(NewGameCommand):
            self.logger.info("发送 NewGameCommand")
            result = self.request(NewGameCommand(rows=16, cols=30, mines=99))
            if result is not None:
                QMessageBox.information(
                    self.widget, "NewGameCommand 响应", f"请求 ID: {result.request_id}, 成功: {result.success}")
        else:
            self.logger.warning("没有 NewGameCommand 权限")

    def _on_video_save(self, event: VideoSaveEvent) -> None:
        self.logger.info(f"收到游戏结束事件: {event.rtime}s")

    def on_shutdown(self) -> None:
        self.logger.info("TestControlPluginA 关闭")

    def on_control_auth_changed(self, command_type: type, granted: bool) -> None:
        # if command_type == NewGameCommand:
        #     self.run_on_gui(self._widget.set_has_permission, granted)
        pass
