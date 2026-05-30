"""
修仙升级界面组件
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QHeaderView, QProgressBar,
    QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap


class LevelDisplay(QWidget):
    """等级和仙躯形象展示区"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧：等级信息
        info_frame = QFrame()
        info_frame.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            " stop:0 #4527A0, stop:1 #7B1FA2);"
            " border-radius: 12px; padding: 16px; }"
        )
        info_layout = QVBoxLayout(info_frame)

        self._rank_label = QLabel("凡人")
        self._rank_label.setStyleSheet("color: #FFD54F; font-size: 28px; font-weight: bold;")
        self._rank_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._rank_label)

        self._level_label = QLabel("Lv.0")
        self._level_label.setStyleSheet("color: #E1BEE7; font-size: 16px;")
        self._level_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._level_label)

        self._xp_label = QLabel("经验: 0 / 0")
        self._xp_label.setStyleSheet("color: #CE93D8; font-size: 14px;")
        self._xp_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._xp_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(24)
        self._progress.setStyleSheet(
            "QProgressBar { border: none; border-radius: 12px;"
            " background: #D1C4E9; text-align: center; font-size: 12px; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 #7C4DFF, stop:1 #E040FB);"
            " border-radius: 12px; }"
        )
        info_layout.addWidget(self._progress)

        layout.addWidget(info_frame, stretch=1)

        # 右侧：仙躯形象
        self._image_label = QLabel()
        self._image_label.setFixedSize(160, 200)
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet(
            "QLabel { background: #1A1A2E; border-radius: 12px;"
            " border: 2px solid #7C4DFF; color: #7C4DFF; font-size: 14px; }"
        )
        self._image_label.setText("等待仙躯\n形象加载...")
        layout.addWidget(self._image_label)

    def set_image(self, image_path: Path | None):
        if image_path and image_path.exists():
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                self._image_label.setPixmap(
                    pixmap.scaled(160, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        self._image_label.setText("暂无仙躯\n形象")

    def update_info(self, rank: str, level: int, xp: int, xp_next: int):
        self._rank_label.setText(rank)
        self._level_label.setText(f"Lv.{level}")
        self._xp_label.setText(f"经验: {xp} / {xp_next}")
        if xp_next > 0:
            self._progress.setRange(0, xp_next)
            self._progress.setValue(xp)
            pct = xp * 100 // xp_next
            self._progress.setFormat(f"{xp} / {xp_next} ({pct}%)")


class XianNiUpgradeUI(QWidget):
    """修仙升级主界面"""

    _signal_update = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_dir: Path | None = None
        self._setup_ui()
        self._signal_update.connect(self._do_update)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._level_display = LevelDisplay()
        self._level_display.setStyleSheet("margin-bottom: 8px;")
        layout.addWidget(self._level_display)

        group = QGroupBox("修仙之路")
        group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; margin-top: 12px; }")
        group_layout = QVBoxLayout(group)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["时间", "级别", "模式", "用时(秒)", "3BV", "获得经验"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        group_layout.addWidget(self._table)

        layout.addWidget(group)

    def set_image_dir(self, image_dir: Path):
        self._image_dir = image_dir

    def _do_update(self, data: dict):
        self._level_display.update_info(
            data["rank"], data["level"], data["xp"], data["xp_next"]
        )
        idx = data["image_index"]
        if self._image_dir is not None:
            self._level_display.set_image(self._image_dir / f"{idx:02d}.png")

        history = data["history"]
        self._table.setRowCount(len(history))
        for i, h in enumerate(history):
            time_value = h["time"]
            if isinstance(time_value, (int, float)):
                time_value = datetime.fromtimestamp(int(time_value)).strftime("%Y-%m-%d %H:%M:%S")
            self._table.setItem(i, 0, QTableWidgetItem(str(time_value)))
            self._table.setItem(i, 1, QTableWidgetItem(h["level"]))
            self._table.setItem(i, 2, QTableWidgetItem(h["mode"]))
            self._table.setItem(i, 3, QTableWidgetItem(f'{h["rtime"]:.3f}'))
            self._table.setItem(i, 4, QTableWidgetItem(str(h["bbbv"])))
            self._table.setItem(i, 5, QTableWidgetItem(str(h["xp"])))
