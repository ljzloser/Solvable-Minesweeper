"""
示例插件：统计面板

功能：
- 统计游戏胜率、平均用时
- 界面显示统计图表和数字
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


class StatsPlugin(BasePlugin):
    """游戏统计插件"""

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="stats",
            description="游戏统计面板",
            icon=make_plugin_icon("#7b1fa2", "📊"),
        )

    def __init__(self, info):
        super().__init__(info)
        self._total_games = 0
        self._wins = 0
        self._losses = 0
        self._total_time = 0.0

    def _setup_subscriptions(self) -> None:
        self.subscribe(GameStartedEvent, self._on_game_started)
        self.subscribe(GameEndedEvent, self._on_game_ended)

    def _create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计概览
        group = QGroupBox("统计概览")
        glayout = QVBoxLayout(group)

        self._summary_label = QLabel("暂无数据")
        self._summary_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        glayout.addWidget(self._summary_label)
        layout.addWidget(group)

        # 详细表格
        tgroup = QGroupBox("历史记录")
        tlayout = QVBoxLayout(tgroup)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["结果", "用时(秒)", "备注"])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        tlayout.addWidget(self._table)
        layout.addWidget(tgroup)

        # 日志
        lgroup = QGroupBox("事件日志")
        llayout = QVBoxLayout(lgroup)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(100)
        llayout.addWidget(self._log_text)
        layout.addWidget(lgroup)

        return widget

    def _log(self, msg: str) -> None:
        if self._log_text:
            self._log_text.append(msg)
            sb = self._log_text.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _update_summary(self) -> None:
        if not hasattr(self, "_summary_label"):
            return
        win_rate = (self._wins / self._total_games * 100) if self._total_games else 0
        avg_time = (self._total_time / self._total_games) if self._total_games else 0
        self._summary_label.setText(
            f"总计: {self._total_games} 场  |  "
            f"胜: {self._wins}  |  "
            f"负: {self._losses}  |  "
            f"胜率: {win_rate:.1f}%  |  "
            f"均时: {avg_time:.2f}s"
        )

    def _on_game_started(self, event: GameStartedEvent) -> None:
        self._log(f"🎮 游戏开始: {event.rows}x{event.cols}, {event.mines}雷")
        self.logger.info(f"游戏开始: {event.rows}x{event.cols}, {event.mines}雷")

    def _on_game_ended(self, event: GameEndedEvent) -> None:
        self._total_games += 1
        self._total_time += event.time
        result = "胜利" if event.is_win else "失败"
        if event.is_win:
            self._wins += 1
        else:
            self._losses += 1

        # 添加到表格
        if hasattr(self, "_table"):
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(result))
            self._table.setItem(row, 1, QTableWidgetItem(f"{event.time:.2f}"))
            self._table.setItem(row, 2, QTableWidgetItem("" if event.is_win else "踩雷"))

        self._update_summary()
        msg = f"{'🎉' if event.is_win else '💥'} {result}! 用时 {event.time:.2f}秒"
        self._log(msg)
        self.logger.info(f"游戏结束: {result}, 用时 {event.time:.2f}s, "
                         f"总场次={self._total_games}")

    def on_initialized(self) -> None:
        self._log("✅ 统计插件已初始化")
        self.logger.info("统计插件已初始化")
