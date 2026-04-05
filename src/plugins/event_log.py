"""
示例插件：事件日志

功能：
- 记录所有收到的游戏事件
- 界面显示事件时间线
"""

from plugin_manager import BasePlugin, PluginInfo, make_plugin_icon
from shared_types import (
    GameStartedEvent,
    GameEndedEvent,
    BoardUpdateEvent,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGroupBox,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QColor


class EventLogPlugin(BasePlugin):
    """事件日志插件"""

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="event_log",
            description="事件日志记录器",
            icon=make_plugin_icon("#e65100", "📝"),
        )

    def __init__(self, info):
        super().__init__(info)

    def _setup_subscriptions(self) -> None:
        self.subscribe(GameStartedEvent, self._on_game_started)
        self.subscribe(GameEndedEvent, self._on_game_ended)
        self.subscribe(BoardUpdateEvent, self._on_board_update)

    def _create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 事件表格
        group = QGroupBox("事件流")
        glayout = QVBoxLayout(group)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["时间", "类型", "详情"])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        glayout.addWidget(self._table)
        layout.addWidget(group)

        # 统计
        sgroup = QGroupBox("统计")
        slayout = QVBoxLayout(sgroup)

        self._stats_label = QLabel("等待事件...")
        slayout.addWidget(self._stats_label)
        layout.addWidget(sgroup)

        return widget

    def _add_event(self, event_type: str, detail: str, color: str | None = None) -> None:
        if not hasattr(self, "_table"):
            return

        row = self._table.rowCount()
        self._table.insertRow(row)

        time_item = QTableWidgetItem(
            QDateTime.currentDateTime().toString("HH:mm:ss.zzz")
        )
        type_item = QTableWidgetItem(event_type)
        detail_item = QTableWidgetItem(detail)

        if color:
            for item in (time_item, type_item, detail_item):
                item.setForeground(QColor(color))

        self._table.setItem(row, 0, time_item)
        self._table.setItem(row, 1, type_item)
        self._table.setItem(row, 2, detail_item)

        self._table.scrollToBottom()

    def _update_stats(self):
        total = self._table.rowCount()
        if hasattr(self, "_stats_label"):
            self._stats_label.setText(f"已记录 {total} 条事件")

    def _on_game_started(self, event: GameStartedEvent) -> None:
        msg = f"{event.rows}x{event.cols}, {event.mines}雷"
        self._add_event("GameStarted", msg, "#1976d2")
        self.logger.info(f"GameStarted: {msg}")
        self._update_stats()

    def _on_game_ended(self, event: GameEndedEvent) -> None:
        result = "胜利" if event.is_win else "失败"
        color = "#2e7d32" if event.is_win else "#c62828"
        msg = f"{result}, 用时 {event.time:.3f}s"
        self._add_event("GameEnded", msg, color)
        self.logger.info(f"GameEnded: {msg}")
        self._update_stats()

    def _on_board_update(self, event: BoardUpdateEvent) -> None:
        rows = len(event.board)
        cols = len(event.board[0]) if rows else 0
        msg = f"{rows}x{cols}"
        self._add_event("BoardUpdate", msg, "#757575")
        self.logger.debug(f"BoardUpdate: {msg}")
        self._update_stats()

    def on_initialized(self) -> None:
        self.logger.info("事件日志插件已初始化")
