"""
修仙升级界面组件
"""

from __future__ import annotations

import struct
from datetime import datetime
from pathlib import Path

_XOR_KEY = b"XianNiAssetKey2026!"

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QHeaderView, QProgressBar,
    QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QResizeEvent


class AspectLabel(QLabel):
    """自动保持宽高比缩放图片的 QLabel"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw: QPixmap | None = None

    def set_raw(self, pm: QPixmap | None):
        self._raw = pm
        self._update_pixmap()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self):
        if self._raw and not self._raw.isNull():
            scaled = self._raw.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            super().setPixmap(scaled)
        else:
            super().setPixmap(QPixmap())


class LevelDisplay(QWidget):
    """等级和仙躯形象展示区"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧：等级信息
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background: white; padding: 16px; }")
        info_frame.setMinimumWidth(400)
        info_layout = QVBoxLayout(info_frame)

        self._rank_label = QLabel("凡人")
        self._rank_label.setStyleSheet("color: #01579B; font-size: 28px; font-weight: bold; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif;")
        self._rank_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._rank_label)

        self._level_label = QLabel("Lv.0")
        self._level_label.setStyleSheet("color: #0277BD; font-size: 16px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif;")
        self._level_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._level_label)

        self._total_xp_label = QLabel("累计经验: 0")
        self._total_xp_label.setStyleSheet("color: #0288D1; font-size: 14px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif;")
        self._total_xp_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._total_xp_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(24)
        self._progress.setStyleSheet(
            "QProgressBar { border: none; "
            " background: #BBDEFB; text-align: center; font-size: 12px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 #42A5F5, stop:1 #1E88E5);}"
        )
        info_layout.addWidget(self._progress)

        layout.addWidget(info_frame, stretch=1)

        # 右侧：仙躯形象
        self._image_label = AspectLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet(
            "QLabel { background: #E1F5FE; "
            " border: 2px solid #4FC3F7; color: #0277BD; font-size: 14px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; }"
        )
        self._image_label.setText("等待仙躯\n形象加载...")
        layout.addWidget(self._image_label)

    def set_image(self, png_bytes: bytes | None):
        if png_bytes:
            try:
                pixmap = QPixmap()
                pixmap.loadFromData(png_bytes, "PNG")
                if not pixmap.isNull():
                    self._image_label.set_raw(pixmap)
                    return
            except Exception:
                pass
        self._image_label.set_raw(None)
        self._image_label.setText("暂无仙躯\n形象")

    def update_info(self, rank: str, level: int, total_xp: int, xp_curr: int, xp_need: int):
        self._rank_label.setText(rank)
        self._level_label.setText(f"Lv.{level}")
        self._total_xp_label.setText(f"累计经验: {total_xp}")
        if xp_need > 0:
            pct = min(xp_curr * 100 // xp_need, 100)
            self._progress.setValue(pct)
            self._progress.setFormat(f"{pct}% | 还需 {xp_need - xp_curr} 经验")
        else:
            self._progress.setValue(100)
            self._progress.setFormat("已满级")


class XianNiUpgradeUI(QWidget):
    """修仙升级主界面"""

    _signal_update = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_dir: Path | None = None
        self._assets: dict[int, bytes] = {}
        self._setup_ui()
        self._signal_update.connect(self._do_update)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._level_display = LevelDisplay()
        self._level_display.setStyleSheet("margin-bottom: 4px;")
        layout.addWidget(self._level_display, 3)

        group = QGroupBox("经验历史记录")
        group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; }")
        group_layout = QVBoxLayout(group)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setMinimumHeight(130)
        self._table.setStyleSheet("QTableWidget { font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; } QHeaderView::section { font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; }")
        self._table.setHorizontalHeaderLabels(["时间", "级别", "模式", "用时(秒)", "3BV", "获得经验"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        group_layout.addWidget(self._table)

        layout.addWidget(group, 2)

    def set_image_dir(self, image_dir: Path):
        self._image_dir = image_dir
        self._assets.clear()
        fp = image_dir / "assets.dat"
        if fp.exists():
            try:
                raw = bytearray(fp.read_bytes())
                for j in range(len(raw)):
                    raw[j] ^= _XOR_KEY[j % len(_XOR_KEY)]
                raw = bytes(raw)
                count = struct.unpack_from('>I', raw, 0)[0]
                off = 4
                for i in range(count):
                    length = struct.unpack_from('>I', raw, off)[0]
                    off += 4
                    self._assets[i + 1] = raw[off:off + length]
                    off += length
            except Exception:
                self._assets.clear()

    def _do_update(self, data: dict):
        self._level_display.update_info(
            data["rank"], data["level"], data["total_xp"], data["xp_curr"], data["xp_need"]
        )
        idx = data["image_index"]
        self._level_display.set_image(self._assets.get(idx))

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
