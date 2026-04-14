"""
UI 组件
"""

from __future__ import annotations

import json
import math
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QCloseEvent as _QCloseEvent
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QMenu,
    QAction,
    QTableView,
    QMessageBox,
    QFileDialog,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QDateTimeEdit,
    QHBoxLayout,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QLabel,
    QHeaderView,
)

from plugin_manager.app_paths import get_executable_dir

from .models import HistoryData, LogicSymbol, CompareSymbol
from .table_model import HistoryTableModel

_translate = QCoreApplication.translate


class FilterWidget(QWidget):
    """筛选条件控件"""

    def __init__(self, float_decimals: int = 2, parent=None):
        super().__init__(parent)
        self._float_decimals = float_decimals
        vbox = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["左括号", "字段", "比较符", "值", "右括号", "逻辑符"]
        )
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        vbox.addWidget(self.table)
        self.setLayout(vbox)
    
    def set_float_decimals(self, decimals: int) -> None:
        """动态设置小数位数"""
        self._float_decimals = decimals

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction(_translate("Form", "添加"), self.add_row)
        menu.addAction(_translate("Form", "删除"), self.del_row)
        menu.addAction(
            _translate("Form", "插入"), lambda: self.insert_row(
                self.table.currentRow())
        )
        menu.exec_(self.table.mapToGlobal(pos))

    def _build_left_bracket(self):
        w = QComboBox(self)
        w.addItems(["", "(", "(("])
        return w

    def _build_field(self):
        w = QComboBox(self)
        w.addItems(HistoryData.fields())
        w.currentIndexChanged.connect(self.on_field_changed)
        return w

    def _build_compare(self):
        w = QComboBox(self)
        w.addItems(CompareSymbol.display_names())
        w.currentIndexChanged.connect(self.on_compare_changed)
        return w

    def _build_right_bracket(self):
        w = QComboBox(self)
        w.addItems(["", ")", "))"])
        return w

    def _build_logic(self):
        w = QComboBox(self)
        w.addItems(LogicSymbol.display_names())
        return w

    def on_field_changed(self, index):
        combo: QComboBox = self.sender()
        item_index = self.table.indexAt(combo.pos())
        if not item_index.isValid():
            return
        row = item_index.row()
        field_name = combo.currentText()
        compare_w: QComboBox = self.table.cellWidget(row, 2)
        compare = CompareSymbol.from_display_name(compare_w.currentText())
        field_cls = HistoryData.get_field_value(field_name)
        self.table.setCellWidget(
            row, 3, self._build_value_widget(compare, field_cls))

    def on_compare_changed(self, index):
        combo: QComboBox = self.sender()
        item_index = self.table.indexAt(combo.pos())
        if not item_index.isValid():
            return
        row = item_index.row()
        field_w: QComboBox = self.table.cellWidget(row, 1)
        field_name = field_w.currentText()
        compare = CompareSymbol.from_display_name(combo.currentText())
        field_cls = HistoryData.get_field_value(field_name)
        self.table.setCellWidget(
            row, 3, self._build_value_widget(compare, field_cls))

    def _build_value_widget(self, compare: CompareSymbol, field_value: Any):
        from shared_types.enums import BaseDiaPlayEnum
        
        if compare not in (CompareSymbol.Contains, CompareSymbol.NotContains):
            if isinstance(field_value, BaseDiaPlayEnum):
                w = QComboBox(self)
                # 获取该枚举类的所有成员的 display_name
                enum_cls = field_value.__class__
                w.addItems([e.display_name for e in enum_cls])
                return w
            elif isinstance(field_value, int):
                return QSpinBox(self)
            elif isinstance(field_value, float):
                w = QDoubleSpinBox(self)
                w.setDecimals(self._float_decimals)
                return w
            elif isinstance(field_value, str):
                return QLineEdit(self)
            elif isinstance(field_value, datetime):
                w = QDateTimeEdit(self)
                w.setDateTime(datetime.now())  # 默认当前时间
                return w
        return QLineEdit(self)

    def add_row(self):
        self.insert_row(self.table.rowCount())

    def del_row(self):
        self.table.removeRow(self.table.currentRow())

    def insert_row(self, row: int):
        self.table.insertRow(row)
        field_w = self._build_field()
        compare_w = self._build_compare()
        compare = CompareSymbol.from_display_name(compare_w.currentText())
        field_value = HistoryData.get_field_value(field_w.currentText())
        self.table.setCellWidget(row, 0, self._build_left_bracket())
        self.table.setCellWidget(row, 1, field_w)
        self.table.setCellWidget(row, 2, compare_w)
        self.table.setCellWidget(
            row, 3, self._build_value_widget(compare, field_value))
        self.table.setCellWidget(row, 4, self._build_right_bracket())
        self.table.setCellWidget(row, 5, self._build_logic())

    def gen_filter_str(self):
        filter_str = ""
        left_count = 0
        right_count = 0
        for row in range(self.table.rowCount()):
            left_bracket_w = self.table.cellWidget(row, 0)
            field_w = self.table.cellWidget(row, 1)
            compare_w = self.table.cellWidget(row, 2)
            value_w = self.table.cellWidget(row, 3)
            right_bracket_w = self.table.cellWidget(row, 4)
            logic_w = self.table.cellWidget(row, 5)

            left_bracket = left_bracket_w.currentText()
            field = field_w.currentText()
            field_init_value = HistoryData.get_field_value(field)
            compare = CompareSymbol.from_display_name(compare_w.currentText())
            right_bracket = right_bracket_w.currentText()
            logic = LogicSymbol.from_display_name(logic_w.currentText()).to_sql

            if left_bracket == "(":
                left_count += 1
            elif left_bracket == "((":
                left_count += 2
            if right_bracket == ")":
                right_count += 1
            elif right_bracket == "))":
                right_count += 2

            if right_count > left_count:
                QMessageBox.warning(
                    self, "错误", f"第{row}行 右括号数量大于左括号数量，请检查"
                )
                return None

            # 获取值
            from shared_types.enums import BaseDiaPlayEnum
            if isinstance(value_w, QComboBox):
                # 如果字段是 Enum 类型，需要获取对应的枚举值
                if isinstance(field_init_value, BaseDiaPlayEnum):
                    enum_cls = field_init_value.__class__
                    display_name = value_w.currentText()
                    # 找到对应的枚举成员
                    for e in enum_cls:
                        if e.display_name == display_name:
                            value = str(e.value)
                            break
                    else:
                        value = value_w.currentText()
                else:
                    value = value_w.currentText()
            elif isinstance(value_w, QDateTimeEdit):
                value = int(
                    value_w.dateTime().toPyDateTime().timestamp() * 1_000_000)
            elif isinstance(value_w, QSpinBox):
                value = str(value_w.value())
            elif isinstance(value_w, QDoubleSpinBox):
                value = str(value_w.value())
            elif isinstance(value_w, QLineEdit):
                if compare in (CompareSymbol.Contains, CompareSymbol.NotContains):
                    if isinstance(field_init_value, (int, float)):
                        values = value_w.text().split(",")
                        for v in values:
                            if not v.replace("-", "").isdigit():
                                QMessageBox.warning(
                                    self, "错误", f"第{row}行 {v} 不是数字"
                                )
                                return None
                        value = ",".join(v for v in values)
                    elif isinstance(field_init_value, datetime):
                        values = value_w.text().split(",")
                        for v in values:
                            try:
                                datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                QMessageBox.warning(
                                    self, "错误", f"第{row}行 {v} 不是合法的日期时间"
                                )
                                return None
                        values = [
                            int(
                                datetime.strptime(
                                    v, "%Y-%m-%d %H:%M:%S").timestamp()
                                * 1_000_000
                            )
                            for v in values
                        ]
                        value = ",".join(str(v) for v in values)
                    else:
                        value = ",".join(
                            f"'{v}'" for v in value_w.text().split(","))
                    value = f"({value})"
                else:
                    value = f"'{value_w.text()}'"
            else:
                value = str(
                    getattr(value_w, "value", value_w.text())
                    if hasattr(value_w, "value")
                    else ""
                )

            is_last = row == self.table.rowCount() - 1
            filter_str += (
                f" {left_bracket} {field} {compare.to_sql} {value} {right_bracket} "
            )
            if not is_last:
                filter_str += logic

        if left_count != right_count:
            QMessageBox.warning(self, "错误", "左括号数量和右括号数量不匹配，请检查")
            return None
        return filter_str


class HistoryTable(QWidget):
    """历史记录表格"""

    HEADERS = [
        "replay_id",
        "game_board_state",
        "rtime",
        "left",
        "right",
        "double",
        "left_s",
        "right_s",
        "double_s",
        "level",
        "cl",
        "cl_s",
        "ce",
        "ce_s",
        "rce",
        "lce",
        "dce",
        "bbbv",
        "bbbv_solved",
        "bbbv_s",
        "flag",
        "path",
        "etime",
        "start_time",
        "end_time",
        "mode",
        "software",
        "player_identifier",
        "race_identifier",
        "uniqueness_identifier",
        "stnb",
        "corr",
        "thrp",
        "ioe",
        "is_official",
        "is_fair",
        "op",
        "isl",
        "pluck",
    ]

    def __init__(self, show_fields: set[str], db_path: Path, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        layout = QVBoxLayout(self)
        self.table = QTableView(self)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.showFields: set[str] = show_fields
        self.headers = self.HEADERS

        self.model = HistoryTableModel([], self.headers, self.showFields, self)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def load(self, data: list[HistoryData]):
        self.model.update_data(data)

    def refresh(self):
        parent_widget = self.parent()
        if hasattr(parent_widget, "load_data"):
            parent_widget.load_data()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction(_translate("Form", "播放"), self.play_row)
        menu.addAction(_translate("Form", "导出"), self.export_row)
        menu.addAction(_translate("Form", "刷新"), self.refresh)
        submenu = QMenu(_translate("Form", "显示字段"), self)
        for field in self.headers:
            action = QAction(field, self)
            action.setCheckable(True)
            action.setChecked(field in self.showFields)
            action.triggered.connect(
                lambda checked, a=action: self._on_toggle_field(a))
            submenu.addAction(action)
        menu.addMenu(submenu)
        menu.exec_(self.table.mapToGlobal(pos))

    def _on_toggle_field(self, action: QAction):
        name = action.text()
        if action.isChecked():
            self.showFields.add(name)
        else:
            self.showFields.discard(name)
        self.model.update_show_fields(self.showFields)

    def _get_current_replay_id(self) -> int | None:
        row_idx = self.table.currentIndex().row()
        if row_idx < 0:
            return None
        visible = self.model._visible_headers
        if "replay_id" in visible:
            col = visible.index("replay_id")
            rid = self.model.data(self.model.index(row_idx, col), Qt.UserRole)
            return rid
        return getattr(self.model._data[row_idx], "replay_id", None)

    def _read_raw_data(self, replay_id: int) -> bytes | None:
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT raw_data FROM history WHERE replay_id = ?", (
                    replay_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def save_evf(self, evf_path: str):
        replay_id = self._get_current_replay_id()
        if replay_id is None:
            return
        raw_data = self._read_raw_data(replay_id)
        if raw_data is None:
            return
        with open(evf_path, "wb") as f:
            f.write(raw_data)

    def play_row(self):
        exec_dir = get_executable_dir()
        temp_filename = exec_dir / "tmp.evf"
        self.save_evf(str(temp_filename))

        exe = exec_dir / "metaminesweeper.exe"
        main_py = exec_dir / "main.py"

        if main_py.exists():
            subprocess.Popen(
                [sys.executable, str(main_py), str(temp_filename)])
        elif exe.exists():
            subprocess.Popen([str(exe), str(temp_filename)])
        else:
            QMessageBox.warning(
                self, "错误", "找不到主程序 (main.py 或 metaminesweeper.exe)"
            )

    def export_row(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            _translate("Form", "导出evf文件"),
            str(get_executable_dir()),
            "evf文件 (*.evf)",
        )
        if file_path:
            self.save_evf(file_path)


class HistoryMainWidget(QWidget):
    """历史记录插件的主界面（作为插件的 widget 返回）"""

    def __init__(
        self,
        db_path: Path,
        config_path: Path,
        float_decimals: int = 2,
        parent=None,
    ):
        super().__init__(parent)
        self._db_path = db_path
        self._config_path = config_path

        self.setWindowTitle(_translate("Form", "历史记录"))
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 查询按钮
        btn_layout = QHBoxLayout()
        self.query_button = QPushButton(_translate("Form", "查询"))
        btn_layout.addWidget(self.query_button)
        btn_layout.addItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # 筛选 + 表格
        self.filter_widget = FilterWidget(float_decimals, self)
        self.table = HistoryTable(self._get_show_fields(), db_path, self)

        # 分页
        limit_layout = QHBoxLayout()
        self.previous_button = QPushButton(_translate("Form", "上一页"))
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setValue(1)
        self.next_button = QPushButton(_translate("Form", "下一页"))
        self.one_page_combo = QComboBox()
        self.one_page_combo.addItems(
            ["10", "20", "50", "100", "200", "500", "1000"])

        self.limit_label = QLabel("")
        limit_layout.addItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        limit_layout.addWidget(self.limit_label)
        limit_layout.addWidget(self.previous_button)
        limit_layout.addWidget(self.page_spin)
        limit_layout.addWidget(self.next_button)
        limit_layout.addWidget(self.one_page_combo)

        layout.addLayout(btn_layout)
        layout.addWidget(self.filter_widget)
        layout.addWidget(self.table)
        layout.addLayout(limit_layout)
        self.setLayout(layout)

        self._connect_signals()
        self.load_data()

    def _connect_signals(self):
        self.query_button.clicked.connect(self._on_query)
        self.previous_button.clicked.connect(
            lambda: self.page_spin.setValue(self.page_spin.value() - 1)
        )
        self.next_button.clicked.connect(
            lambda: self.page_spin.setValue(self.page_spin.value() + 1)
        )
        self.one_page_combo.currentTextChanged.connect(self.load_data)
        self.page_spin.valueChanged.connect(self.load_data)

    def _on_query(self):
        if self.page_spin.value() > 1:
            self.page_spin.setValue(1)
        else:
            self.load_data()

    def _get_limit_str(self):
        per_page = int(self.one_page_combo.currentText())
        offset = (self.page_spin.value() - 1) * per_page
        return f" LIMIT {per_page} OFFSET {offset}"

    def _get_show_fields(self) -> set[str]:
        if not self._config_path.exists():
            return set(HistoryData.fields())
        with open(self._config_path, "r") as f:
            return set(json.load(f))

    def load_data(self):
        if not self._db_path.exists():
            QMessageBox.warning(self, "错误", "历史记录数据库不存在")
            return

        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            filter_str = self.filter_widget.gen_filter_str()
            sql = "SELECT *, COUNT(*) OVER() AS total_count FROM history"
            if filter_str:
                sql += " WHERE " + filter_str
            elif filter_str is None:
                return
            sql += self._get_limit_str()
            cursor.execute(sql)
            datas = cursor.fetchall()

            if not datas:
                self.page_spin.setMaximum(1)
                self.limit_label.setText("共0行,0页")
            else:
                per_page = int(self.one_page_combo.currentText())
                total = datas[0]["total_count"]
                max_page = math.ceil(total / per_page)
                self.page_spin.setMaximum(max_page)
                self.limit_label.setText(f"共{total}行,{max_page}页")

            history_data = [HistoryData.from_dict(dict(d)) for d in datas]
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.warning(self, "错误", f"加载历史记录失败: {e}")
            return

        self.table.load(history_data)

    def closeEvent(self, event: _QCloseEvent):
        """关闭时保存列显示配置"""
        with open(self._config_path, "w") as f:
            json.dump(list(self.table.showFields), f)
        super().closeEvent(event)
    
    def set_float_decimals(self, decimals: int) -> None:
        """动态设置小数位数"""
        self.filter_widget.set_float_decimals(decimals)
