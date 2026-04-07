"""
实时游戏统计面板

展示计数器、表格等常见 UI 元素的用法。
"""
from __future__ import annotations

import json
from collections import defaultdict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QHeaderView,
)
from PyQt5.QtCore import pyqtSignal

from plugin_manager import BasePlugin, PluginInfo, make_plugin_icon, WindowMode
from shared_types.events import VideoSaveEvent


class StatsPanel(QWidget):
    """统计面板 UI"""

    _signal_update_stats = pyqtSignal(dict)
    _signal_add_record = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total_games = 0
        self._stats_by_level = defaultdict(lambda: {"count": 0, "best_time": float('inf')})

        self._setup_ui()
        self._signal_update_stats.connect(self._do_update_stats)
        self._signal_add_record.connect(self._do_add_record)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        cards_layout = QHBoxLayout()

        self._lbl_total = self._make_stat_card("Total", "0", "#1976D2")
        self._lbl_best = self._make_stat_card("Best", "--", "#F57C00")

        for card in [self._lbl_total, self._lbl_best]:
            cards_layout.addWidget(card)

        main_layout.addLayout(cards_layout)

        group = QGroupBox("Recent Games")
        group_layout = QVBoxLayout(group)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Level", "Time(s)", "3BV", "Clicks"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        group_layout.addWidget(self._table)

        main_layout.addWidget(group)

    @staticmethod
    def _make_stat_card(title: str, value: str, color: str) -> QWidget:
        card = QWidget()
        card.setStyleSheet(f"background: {color}; border-radius: 8px; padding: 8px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        return card

    def _do_update_stats(self, data: dict):
        level = data.get("level", "?")
        rtime = data.get("rtime", 0)

        self._total_games += 1
        self._lbl_total.findChild(QLabel).setText(str(self._total_games))

        stats = self._stats_by_level[level]
        stats["count"] += 1
        if rtime > 0 and rtime < stats["best_time"]:
            stats["best_time"] = rtime
            self._lbl_best.findChild(QLabel).setText(f"{rtime:.2f}")

    def _do_add_record(self, data: dict):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(str(data.get("level", "?"))))
        self._table.setItem(row, 1, QTableWidgetItem(f"{data.get('rtime', 0):.2f}"))
        self._table.setItem(row, 2, QTableWidgetItem(str(data.get("bbbv", 0))))
        ops = int(data.get("left", 0)) + int(data.get("right", 0))
        self._table.setItem(row, 3, QTableWidgetItem(str(ops)))


class StatsPlugin(BasePlugin):
    """实时游戏统计插件"""

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="stats_panel",
            version="1.0.0",
            author="Example",
            description="Real-time game statistics panel with table and counters",
            icon=make_plugin_icon("#E91E63", "S", 64),
            window_mode=WindowMode.TAB,
        )

    def _setup_subscriptions(self) -> None:
        self.subscribe(VideoSaveEvent, self._on_video_save)

    def _create_widget(self) -> QWidget:
        self._panel = StatsPanel()
        return self._panel

    def on_initialized(self) -> None:
        saved = self.data_dir / "saved_stats.json"
        if saved.exists():
            try:
                data = json.loads(saved.read_text(encoding='utf-8'))
                self.logger.info(f"Restored {len(data)} records from disk")
            except Exception as e:
                self.logger.warning(f"Failed to load saved stats: {e}")

    def on_shutdown(self) -> None:
        self.logger.info("StatsPlugin shutting down")

    def _on_video_save(self, event: VideoSaveEvent):
        self.logger.info(f"[{event.level}] {event.rtime:.2f}s | 3BV={event.bbbv}")

        event_dict = {
            "level": event.level,
            "rtime": event.rtime,
            "bbbv": event.bbbv,
            "left": event.left,
            "right": event.right,
        }
        self._panel._signal_update_stats.emit(event_dict)
        self._panel._signal_add_record.emit(event_dict)
