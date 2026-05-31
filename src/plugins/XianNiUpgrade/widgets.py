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
    QFrame, QAbstractItemView, QPushButton, QFileDialog,
    QMessageBox, QDialog, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QResizeEvent

from .models import LEVEL_LABELS, MODE_LABELS


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


class AbsorbDialog(QDialog):
    """吸收灵气对话框：选择校验程序+录像目录后直接确认"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("吸收灵气")
        self.resize(500, 150)
        layout = QVBoxLayout(self)

        exe_row = QHBoxLayout()
        self._exe_edit = QLineEdit()
        self._exe_edit.setPlaceholderText("选择验证法器...")
        browse_exe = QPushButton("浏览")
        browse_exe.clicked.connect(self._browse_exe)
        exe_row.addWidget(QLabel("验证法器:"))
        exe_row.addWidget(self._exe_edit)
        exe_row.addWidget(browse_exe)
        layout.addLayout(exe_row)

        replay_row = QHBoxLayout()
        self._replay_edit = QLineEdit()
        self._replay_edit.setPlaceholderText("选择灵箓目录...")
        browse_replay = QPushButton("浏览")
        browse_replay.clicked.connect(self._browse_replay)
        replay_row.addWidget(QLabel("灵箓目录:"))
        replay_row.addWidget(self._replay_edit)
        replay_row.addWidget(browse_replay)
        layout.addLayout(replay_row)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确认")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择验证法器", "", "法器 (*.exe);;所有文件 (*)")
        if path:
            self._exe_edit.setText(path)

    def _browse_replay(self):
        path = QFileDialog.getExistingDirectory(self, "选择灵箓目录")
        if path:
            self._replay_edit.setText(path)

    def get_paths(self) -> tuple[str, str]:
        return self._exe_edit.text().strip(), self._replay_edit.text().strip()


class LevelDisplay(QWidget):
    """等级和仙躯形象展示区"""

    absorb_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧：等级信息
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background: white; padding: 8px; }")
        info_frame.setMinimumWidth(400)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)

        self._player_label = QLabel("")
        self._player_label.setStyleSheet("color: #01579B; font-size: 15px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif;")
        self._player_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._player_label)

        self._rank_label = QLabel("凡人")
        self._rank_label.setStyleSheet("color: #01579B; font-size: 28px; font-weight: bold; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif;")
        self._rank_label.setAlignment(Qt.AlignCenter)
        self._rank_label.setWordWrap(True)
        info_layout.addWidget(self._rank_label)

        self._level_label = QLabel("Lv.0")
        self._level_label.setStyleSheet("color: #0277BD; font-size: 16px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif;")
        self._level_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._level_label)

        self._total_xp_label = QLabel("修为: 0")
        self._total_xp_label.setStyleSheet("color: #0288D1; font-size: 14px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif;")
        self._total_xp_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._total_xp_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(26)
        self._progress.setStyleSheet(
            "QProgressBar { border: none; "
            " background: #BBDEFB; text-align: center; font-size: 11px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 #42A5F5, stop:1 #1E88E5);}"
        )
        info_layout.addWidget(self._progress)

        absorb_btn = QPushButton("吸收灵气")
        absorb_btn.setFixedHeight(22)
        absorb_btn.setCursor(Qt.PointingHandCursor)
        absorb_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #64B5F6; border: none; "
            "font-size: 12px; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; }"
            "QPushButton:hover { color: #42A5F5; }"
        )
        absorb_btn.clicked.connect(self.absorb_clicked.emit)
        info_layout.addWidget(absorb_btn, alignment=Qt.AlignRight)

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

    def update_info(self, player_name: str, rank: str, level: int, total_xp: int, xp_curr: int, xp_need: int):
        self._player_label.setText(player_name)
        self._rank_label.setText(rank)
        self._level_label.setText(f"Lv.{level}")
        self._total_xp_label.setText(f"修为: {total_xp}")
        if xp_need > 0:
            pct = min(xp_curr * 100 // xp_need, 100)
            self._progress.setValue(pct)
            self._progress.setFormat(f"{pct}% | 还需 {xp_need - xp_curr} 道行")
        else:
            self._progress.setValue(100)
            self._progress.setFormat("已圆满")


class XianNiUpgradeUI(QWidget):
    """修仙升级主界面"""

    _signal_update = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_dir: Path | None = None
        self._assets: dict[int, bytes] = {}
        self._validate_cb = None
        self._absorb_cb = None
        self._setup_ui()
        self._signal_update.connect(self._do_update)

    def set_absorb_callbacks(self, validate_cb, absorb_cb):
        self._validate_cb = validate_cb
        self._absorb_cb = absorb_cb

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._level_display = LevelDisplay()
        self._level_display.setStyleSheet("margin-bottom: 4px;")
        self._level_display.absorb_clicked.connect(self._on_absorb_clicked)
        layout.addWidget(self._level_display, 3)

        group = QGroupBox("修行日志")
        group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; }")
        group_layout = QVBoxLayout(group)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setMinimumHeight(130)
        self._table.setStyleSheet("QTableWidget { font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; } QTableWidget::item { border-bottom: 1px solid #E0E0E0; } QHeaderView::section { font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', Arial, sans-serif; border: none; }")
        self._table.setShowGrid(False)
        self._table.setHorizontalHeaderLabels(["时刻", "境阶", "法式", "耗时", "衍数", "道行"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self._table.setColumnWidth(0, 150)
        for c in range(1, 6):
            self._table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self._table.verticalHeader().setDefaultSectionSize(22)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
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

    def _on_absorb_clicked(self):
        if not self._validate_cb or not self._absorb_cb:
            QMessageBox.warning(self, "提示", "插件未就绪")
            return
        dialog = AbsorbDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        exe_path, replay_path = dialog.get_paths()
        if not exe_path or not replay_path:
            QMessageBox.warning(self, "提示", "请填写验证法器和灵箓目录")
            return

        preview = self._validate_cb(exe_path, replay_path)
        if preview is None:
            QMessageBox.warning(self, "吸收灵气失败", "验证失败，请查看插件日志")
            return
        if not preview["new_files"]:
            QMessageBox.information(self, "吸收灵气", "没有新的灵箓需要导入")
            return

        gained = self._absorb_cb(preview)
        QMessageBox.information(
            self, "吸收灵气完成",
            f"新增 {len(preview['new_files'])} 道灵箓\n获得 {gained} 道行"
        )

    def _do_update(self, data: dict):
        self._level_display.update_info(
            data.get("player_name", ""), data["rank"], data["level"],
            data["total_xp"], data["xp_curr"], data["xp_need"]
        )
        idx = data["image_index"]
        self._level_display.set_image(self._assets.get(idx))

        history = data["history"]
        self._table.setRowCount(len(history))
        for i, h in enumerate(history):
            time_value = h["time"]
            if isinstance(time_value, (int, float)):
                time_value = datetime.fromtimestamp(int(time_value)).strftime("%Y-%m-%d %H:%M:%S")
            level_str = LEVEL_LABELS.get(h["level"], str(h["level"]))
            mode_str = MODE_LABELS.get(h["mode"], str(h["mode"]))
            for col, val in [(0, str(time_value)), (1, level_str), (2, mode_str),
                             (3, f'{h["rtime"]:.3f}'), (4, str(h["bbbv"])), (5, str(h["xp"]))]:
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(i, col, item)
