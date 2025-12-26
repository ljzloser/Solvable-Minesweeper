from enum import Enum
from fileinput import filename
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTableWidget, QMenu, \
    QAction, QTableWidgetItem, QHeaderView, QTableView, QMessageBox, QFileDialog, \
    QComboBox, QLineEdit
from PyQt5.QtCore import QDateTime, Qt, QCoreApplication
from datetime import datetime
import inspect
from utils import GameBoardState, BaseDiaPlayEnum, get_paths, patch_env
_translate = QCoreApplication.translate
# 逻辑符


class LogicSymbol(BaseDiaPlayEnum):
    And = 0
    Or = 1

    @property
    def display_name(self):
        match self:
            case LogicSymbol.And:
                return _translate("Form", "与")
            case LogicSymbol.Or:
                return _translate("Form", "或")
# 比较符


class CompareSymbol(BaseDiaPlayEnum):
    Equal = 0
    NotEqual = 1
    GreaterThan = 2
    LessThan = 3
    GreaterThanOrEqual = 4
    LessThanOrEqual = 5
    Contains = 6
    NotContains = 7

    @property
    def display_name(self):
        match self:
            case CompareSymbol.Equal:
                return _translate("Form", "等于")
            case CompareSymbol.NotEqual:
                return _translate("Form", "不等于")
            case CompareSymbol.GreaterThan:
                return _translate("Form", "大于")
            case CompareSymbol.LessThan:
                return _translate("Form", "小于")
            case CompareSymbol.GreaterThanOrEqual:
                return _translate("Form", "大于等于")
            case CompareSymbol.LessThanOrEqual:
                return _translate("Form", "小于等于")
            case CompareSymbol.Contains:
                return _translate("Form", "包含")
            case CompareSymbol.NotContains:
                return _translate("Form", "不包含")


class HistoryData:
    replay_id: int = 0
    game_board_state: GameBoardState = GameBoardState.Win
    rtime: float = 0
    left: int = 0
    right: int = 0
    double: int = 0
    left_s: float = 0.0
    right_s: float = 0.0
    double_s: float = 0.0
    level: int = 0
    cl: int = 0
    cl_s: float = 0.0
    ce: int = 0
    ce_s: float = 0.0
    rce: int = 0
    lce: int = 0
    dce: int = 0
    bbbv: int = 0
    bbbv_solved: int = 0
    bbbv_s: float = 0.0
    flag: int = 0
    path: float = 0.0
    etime: float = datetime.now()
    start_time: datetime = datetime.now()
    end_time: datetime = datetime.now()
    mode: int = 0
    software: str = ""
    player_identifier: str = ""
    race_identifier: str = ""
    uniqueness_identifier: str = ""
    stnb: float = 0.0
    corr: float = 0.0
    thrp: float = 0.0
    ioe: float = 0.0
    is_official: int = 0
    is_fair: int = 0
    op: int = 0
    isl: int = 0

    @classmethod
    def fields(cls):
        return [name for name, value in inspect.getmembers(cls) if not name.startswith("__") and not callable(value) and not name.startswith("_")]

    @classmethod
    def query_all(cls):
        return f"select {','.join(cls.fields())} from history"

    @classmethod
    def from_dict(cls, data: dict):
        instance = cls()
        for name, value in inspect.getmembers(cls):
            if not name.startswith("__") and not callable(value) and not name.startswith("_"):
                new_value = data.get(name)
                if isinstance(value, datetime):
                    value = datetime.fromtimestamp(new_value / 1_000_000)
                elif isinstance(value, float):
                    value = round(new_value, 4)
                elif isinstance(value, BaseDiaPlayEnum):
                    value = value.__class__(new_value)
                else:
                    value = new_value
                setattr(instance, name, value)
        return instance


class FliterWidget(QWidget):
    def __init__(self, parent: QWidget | None = ...) -> None:
        super().__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["左括号", "字段", "比较符", "值", "右括号", "逻辑符"])
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        # 自定义右键菜单
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.vbox.addWidget(self.table)
        self.setLayout(self.vbox)
        self.add_row()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction(_translate("Form", "添加"), self.add_row)
        menu.addAction(_translate("Form", "删除"), self.del_row)
        menu.addAction(_translate("Form", "插入"),
                       lambda: self.insert_row(self.table.currentRow()))
        menu.exec_(self.table.mapToGlobal(pos))

    def build_left_bracket_Widget(self):
        widget = QComboBox(self)
        widget.addItems(["", "(", "(("])
        return widget

    def build_field_Widget(self):
        widget = QComboBox(self)
        widget.addItems(HistoryData.fields())
        return widget

    def build_compare_Widget(self):
        widget = QComboBox(self)
        widget.addItems(CompareSymbol.display_names())
        return widget

    def build_value_Widget(self):
        widget = QLineEdit(self)
        return widget

    def build_right_bracket_Widget(self):
        widget = QComboBox(self)
        widget.addItems(["", ")", "))"])
        return widget

    def build_logic_Widget(self):
        widget = QComboBox(self)
        widget.addItems(LogicSymbol.display_names())
        return widget

    def add_row(self):
        self.insert_row(self.table.rowCount())

    def del_row(self):
        pass

    def insert_row(self, row: int):
        self.table.insertRow(row)
        self.table.setCellWidget(row, 0, self.build_left_bracket_Widget())
        self.table.setCellWidget(row, 1, self.build_field_Widget())
        self.table.setCellWidget(row, 2, self.build_compare_Widget())
        self.table.setCellWidget(row, 3, self.build_value_Widget())
        self.table.setCellWidget(row, 4, self.build_right_bracket_Widget())
        self.table.setCellWidget(row, 5, self.build_logic_Widget())


class HistoryTable(QWidget):
    def __init__(self, showFields: set[str], parent: QWidget | None = ...) -> None:
        super().__init__(parent)
        self.layout: QVBoxLayout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        # 设置不可编辑
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 添加右键菜单
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.showFields: set[str] = showFields
        self.headers = [
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
        ]
        self.table.setColumnCount(len(self.showFields))
        self.table.setHorizontalHeaderLabels(self.headers)
        # 居中显示文字
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        # 选中整行
        self.table.setSelectionBehavior(QTableView.SelectRows)

        # 自适应列宽
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        # 初始化隐藏列
        for i, field in enumerate(self.headers):
            self.table.setColumnHidden(i, field not in self.showFields)

    def load(self, data: list[HistoryData]):
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, field in enumerate(self.headers):
                value = getattr(row, field)

                self.table.setItem(i, j, self.build_item(value))

    def build_item(self, value: Any):
        if isinstance(value, datetime):
            new_value = value.strftime("%Y-%m-%d %H:%M:%S.%f")
        if isinstance(value, BaseDiaPlayEnum):
            new_value = value.display_name
        else:
            new_value = value
        item = QTableWidgetItem(str(new_value))
        item.setData(Qt.UserRole, value)
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        return item

    def refresh(self):
        parent: 'HistoryGUI' = self.parent()
        parent.load_data()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        action1 = menu.addAction(_translate("Form", "播放"), self.play_row)
        action2 = menu.addAction(_translate("Form", "导出"), self.export_row)
        action3 = menu.addAction(_translate("Form", "刷新"), self.refresh)
        # 给action3添加子菜单
        submenu = QMenu(_translate("Form", "显示字段"), self)
        # 遍历所有字段，添加一个action
        for field in self.headers:
            action = QAction(field, self)
            action.setCheckable(True)
            action.setChecked(field in self.showFields)
            action.triggered.connect(
                lambda checked: self.on_action_triggered(checked))
            submenu.addAction(action)
        menu.addMenu(submenu)
        menu.exec_(self.table.mapToGlobal(pos))

    def on_action_triggered(self, checked: bool):
        action: QAction = self.sender()
        name = action.text()
        self.table.setColumnHidden(
            self.table.horizontalHeader().logicalIndex(
                self.headers.index(name)), not checked)
        if checked:
            self.showFields.add(name)
        else:
            self.showFields.remove(name)

    def save_evf(self, evf_path: str):
        row_index = self.table.currentRow()
        if row_index < 0:
            return
        row = self.table.item(row_index, 0).data(Qt.UserRole)
        for filed in self.headers:
            if filed == "replay_id":
                replay_id = self.table.item(
                    row_index, self.headers.index(filed)).data(Qt.UserRole)
        conn = sqlite3.connect(Path(get_paths()) / "history.db")
        conn.row_factory = sqlite3.Row  # 设置行工厂
        cursor = conn.cursor()
        cursor.execute(
            "select raw_data from history where replay_id = ?", (replay_id,))

        raw_data = cursor.fetchone()[0]
        with open(evf_path, "wb") as f:
            f.write(raw_data)
        conn.close()

    def play_row(self):
        temp_filename = Path(get_paths())/f"tmp.evf"
        self.save_evf(temp_filename)
        # 检查当前目录是否存在main.py
        if (Path(get_paths()) / "main.py").exists():
            subprocess.Popen(
                [
                    sys.executable,
                    str(Path(get_paths()) / "main.py"),
                    temp_filename
                ],
                env=patch_env(),
            )
        elif (Path(get_paths()) / "metaminesweeper.exe").exists():
            subprocess.Popen(
                [
                    Path(get_paths()) / "metaminesweeper.exe",
                    temp_filename
                ]
            )
        else:
            QMessageBox.warning(
                self, "错误", "当前目录下不存在main.py或metaminesweeper.exe")
            return

    def export_row(self):
        file_path, _ = QFileDialog.getSaveFileName(self, _translate(
            "Form", "导出evf文件"), get_paths(), "evf文件 (*.evf)")

        if not file_path:
            return
        self.save_evf(file_path)


class HistoryGUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_translate("Form", "历史记录"))
        self.resize(800, 600)
        self.layout = QVBoxLayout(self)
        self.table = HistoryTable(self.get_show_fields(), self)
        self.fliterWidget = FliterWidget(self)
        self.layout.addWidget(self.fliterWidget)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        self.load_data()

    def load_data(self):
        conn = sqlite3.connect(Path(get_paths()) / "history.db")
        conn.row_factory = sqlite3.Row  # 设置行工厂
        cursor = conn.cursor()
        cursor.execute(HistoryData.query_all())
        datas = cursor.fetchall()
        history_data = [HistoryData.from_dict(dict(data)) for data in datas]
        self.table.load(history_data)

    @property
    def config_path(self):
        return Path(get_paths()) / "history_show_fields.json"

    def get_show_fields(self):
        # 先判断是否存在展示列的json文件
        if not (self.config_path).exists():
            return set(HistoryData.fields())
        with open(self.config_path, "r") as f:
            return set(json.load(f))

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        with open(self.config_path, "w") as f:
            json.dump(list(self.table.showFields), f)
        return super().closeEvent(a0)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    gui = HistoryGUI()

    gui.show()

    sys.exit(app.exec_())
