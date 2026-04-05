import math
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from turtle import right
from typing import Any
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTableWidget, QMenu, \
    QAction, QTableWidgetItem, QHeaderView, QTableView, QMessageBox, QFileDialog, \
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QHBoxLayout, QPushButton, \
    QSpacerItem, QSizePolicy, QLabel
from PyQt5.QtCore import Qt, QCoreApplication, QAbstractTableModel, QModelIndex
from datetime import datetime
import inspect
from utils import GameBoardState, BaseDiaPlayEnum, get_paths, patch_env, GameMode, GameLevel
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

    @property
    def to_sql(self):
        match self:
            case LogicSymbol.And:
                return "and"
            case LogicSymbol.Or:
                return "or"


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

    @property
    def to_sql(self):
        match self:
            case CompareSymbol.Equal:
                return "="
            case CompareSymbol.NotEqual:
                return "!="
            case CompareSymbol.GreaterThan:
                return ">"
            case CompareSymbol.LessThan:
                return "<"
            case CompareSymbol.GreaterThanOrEqual:
                return ">="
            case CompareSymbol.LessThanOrEqual:
                return "<="
            case CompareSymbol.Contains:
                return "in"
            case CompareSymbol.NotContains:
                return "not in"


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
    level: GameLevel = GameLevel.BEGINNER
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
    mode: GameMode = GameMode.Standard
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
    pluck: float = 0.0

    @classmethod
    def get_field_value(cls, field_name: str):
        for name, value in inspect.getmembers(cls):
            if not name.startswith("__") and not callable(value) and not name.startswith("_") and name == field_name:
                return value

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


class HistoryTableModel(QAbstractTableModel):
    def __init__(self, data: list[HistoryData], headers: list[str], show_fields: set[str], parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = headers
        self._show_fields = show_fields
        # 只显示在show_fields中的列
        self._visible_headers = [h for h in headers if h in show_fields]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._visible_headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= len(self._data) or col >= len(self._visible_headers):
            return None

        if role == Qt.DisplayRole:
            field_name = self._visible_headers[col]
            value = getattr(self._data[row], field_name)

            # 格式化显示值
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M:%S.%f")
            elif isinstance(value, BaseDiaPlayEnum):
                return value.display_name
            else:
                return str(value)

        elif role == Qt.UserRole:
            # 返回原始值
            field_name = self._visible_headers[col]
            return getattr(self._data[row], field_name)

        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter | Qt.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if section < len(self._visible_headers):
                return self._visible_headers[section]
        return None

    def update_data(self, data: list[HistoryData]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def update_show_fields(self, show_fields: set[str]):
        self.beginResetModel()
        self._show_fields = show_fields
        self._visible_headers = [h for h in self._headers if h in show_fields]
        self.endResetModel()


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
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.vbox.addWidget(self.table)
        self.setLayout(self.vbox)

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
        widget.currentIndexChanged.connect(self.on_field_changed)
        return widget

    def build_compare_Widget(self):
        widget = QComboBox(self)
        widget.addItems(CompareSymbol.display_names())
        widget.currentIndexChanged.connect(self.on_compare_changed)
        return widget

    def build_right_bracket_Widget(self):
        widget = QComboBox(self)
        widget.addItems(["", ")", "))"])
        return widget

    def build_logic_Widget(self):
        widget = QComboBox(self)
        widget.addItems(LogicSymbol.display_names())

        return widget

    def on_field_changed(self, index):
        combo: QComboBox = self.sender()
        item_index = self.table.indexAt(combo.pos())
        filed_name = combo.currentText()
        if item_index.isValid():
            row = item_index.row()
            compareSymbol_widget = self.table.cellWidget(row, 2)
            compare_name = compareSymbol_widget.currentText()
            compare = CompareSymbol.from_display_name(compare_name)
            field_cls = HistoryData.get_field_value(filed_name)
            widget = self.build_value_widget(compare, field_cls)
            self.table.setCellWidget(row, 3, widget)

    def on_compare_changed(self, index):
        combo: QComboBox = self.sender()
        item_index = self.table.indexAt(combo.pos())
        if item_index.isValid():
            row = item_index.row()
            field_widget = self.table.cellWidget(row, 1)
            filed_name = field_widget.currentText()
            compare_name = combo.currentText()
            compare = CompareSymbol.from_display_name(compare_name)
            field_cls = HistoryData.get_field_value(filed_name)
            widget = self.build_value_widget(compare, field_cls)
            self.table.setCellWidget(row, 3, widget)

    def build_value_widget(self, compare: CompareSymbol, field_value: Any):
        if compare not in (CompareSymbol.Contains, CompareSymbol.NotContains):
            if isinstance(field_value, int):
                widget = QSpinBox(self)
            elif isinstance(field_value, float):
                widget = QDoubleSpinBox(self)
            elif isinstance(field_value, str):
                widget = QLineEdit(self)
            elif isinstance(field_value, datetime):
                widget = QDateTimeEdit(self)
            elif isinstance(field_value, BaseDiaPlayEnum):
                widget = QComboBox(self)
                widget.addItems(field_value.display_names())
        else:
            widget = QLineEdit(self)
        return widget

    def add_row(self):
        self.insert_row(self.table.rowCount())

    def del_row(self):
        self.table.removeRow(self.table.currentRow())

    def insert_row(self, row: int):
        self.table.insertRow(row)
        field_widget = self.build_field_Widget()
        compare_widget = self.build_compare_Widget()
        compare = CompareSymbol.from_display_name(compare_widget.currentText())
        field_value = HistoryData.get_field_value(field_widget.currentText())
        self.table.setCellWidget(row, 0, self.build_left_bracket_Widget())
        self.table.setCellWidget(row, 1, field_widget)
        self.table.setCellWidget(row, 2, compare_widget)
        self.table.setCellWidget(
            row, 3, self.build_value_widget(compare, field_value))
        self.table.setCellWidget(row, 4, self.build_right_bracket_Widget())
        self.table.setCellWidget(row, 5, self.build_logic_Widget())

    def gen_fliter_str(self):
        fliter_str = ""
        left_count = 0
        right_count = 0
        for row in range(self.table.rowCount()):

            left_bracket_widget = self.table.cellWidget(row, 0)
            field_widget = self.table.cellWidget(row, 1)
            compare_widget = self.table.cellWidget(row, 2)
            value_widget = self.table.cellWidget(row, 3)
            right_bracket_widget = self.table.cellWidget(row, 4)
            logic_widget = self.table.cellWidget(row, 5)
            left_bracket = left_bracket_widget.currentText()
            field = field_widget.currentText()
            field_init_value = HistoryData.get_field_value(field)
            compare = CompareSymbol.from_display_name(
                compare_widget.currentText())
            right_bracket = right_bracket_widget.currentText()
            logic = LogicSymbol.from_display_name(
                logic_widget.currentText()).to_sql
            if left_bracket == "(":
                left_count += 1
            elif left_bracket == "((":
                left_count += 2

            if right_bracket == ")":
                right_count += 1
            elif right_bracket == "))":
                right_count += 2

            if right_count > left_count:
                QMessageBox.warning(self, "错误", f"第{row}行 右括号数量大于左括号数量，请检查")
                return

            if isinstance(value_widget, QComboBox):
                filed_cls = type(field_init_value)
                value = filed_cls.from_display_name(
                    value_widget.currentText()).value
            elif isinstance(value_widget, QDateTimeEdit):
                value = int(value_widget.dateTime(
                ).toPyDateTime().timestamp() * 1_000_000)
            elif isinstance(value_widget, QSpinBox):
                value = str(value_widget.value())
            elif isinstance(value_widget, QDoubleSpinBox):
                value = str(value_widget.value())
            elif isinstance(value_widget, QLineEdit):
                if compare in (CompareSymbol.Contains, CompareSymbol.NotContains):
                    if isinstance(field_init_value, (int, float)):
                        values = value_widget.text().split(",")
                        for v in values:
                            if not v.isdigit():
                                QMessageBox.warning(
                                    self, "错误", f"第{row}行 {v} 不是数字，请输入数字")
                                return None
                        value = ",".join(str(v) for v in values)
                    elif isinstance(field_init_value, BaseDiaPlayEnum):
                        values = value_widget.text().split(",")
                        filed_cls = type(field_init_value)
                        for v in values:
                            if v not in field_init_value.display_names():
                                QMessageBox.warning(
                                    self, "错误", f"第{row}行 {v} 不是合法的枚举值，请输入合法的枚举值")
                                return None
                        values = [filed_cls.from_display_name(
                            v).value for v in values]
                        value = ",".join(str(v) for v in values)
                    elif isinstance(field_init_value, datetime):
                        values = value_widget.text().split(",")
                        for v in values:
                            try:
                                d = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                QMessageBox.warning(
                                    self, "错误", f"第{row}行 {v} 不是合法的日期时间戳，请输入合法的日期时间戳,格式为: %Y-%m-%d %H:%M:%S")
                                return None
                        values = [int(datetime.strptime(
                            v, "%Y-%m-%d %H:%M:%S").timestamp() * 1_000_000) for d in values]
                        value = ",".join(str(v) for v in values)
                    else:
                        value = ",".join(
                            f"'{v}'" for v in value_widget.text().split(","))
                    value = f"({value})"
                else:
                    value = f"'{value_widget.text()}'"
            if row == self.table.rowCount() - 1:
                fliter_str += f" {left_bracket} {field} {compare.to_sql} {value} {right_bracket} "
            else:
                fliter_str += f" {left_bracket} {field} {compare.to_sql} {value} {right_bracket} {logic}"
        if left_count != right_count:
            QMessageBox.warning(self, "错误", f"左括号数量和右括号数量不匹配，请检查")
            return None
        return fliter_str


class HistoryTable(QWidget):
    def __init__(self, showFields: set[str], parent: QWidget | None = ...) -> None:
        super().__init__(parent)
        self.layout: QVBoxLayout = QVBoxLayout(self)
        self.table = QTableView(self)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        # 设置不可编辑
        self.table.setEditTriggers(QTableView.NoEditTriggers)
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
            "pluck"
        ]

        # 创建模型
        self.model = HistoryTableModel([], self.headers, self.showFields, self)
        self.table.setModel(self.model)

        # 居中显示文字
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        # 选中整行
        self.table.setSelectionBehavior(QTableView.SelectRows)
        # 自适应列宽
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)

    def load(self, data: list[HistoryData]):
        # 使用模型更新数据
        self.model.update_data(data)

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
        if checked:
            self.showFields.add(name)
        else:
            self.showFields.remove(name)

        # 更新模型的显示字段
        self.model.update_show_fields(self.showFields)

    def save_evf(self, evf_path: str):
        row_index = self.table.currentIndex().row()
        if row_index < 0:
            return

        # 从模型获取数据
        replay_id_index = self.model._visible_headers.index(
            "replay_id") if "replay_id" in self.model._visible_headers else -1
        if replay_id_index >= 0:
            replay_id = self.model.data(self.model.index(
                row_index, replay_id_index), Qt.UserRole)
        else:
            # 如果replay_id不在显示字段中，从原始数据获取
            replay_id = getattr(self.model._data[row_index], "replay_id")
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
        self.button_layout = QHBoxLayout()
        self.query_button = QPushButton(_translate("Form", "查询"))
        self.button_layout.addWidget(self.query_button)
        self.button_layout.addItem(QSpacerItem(
            10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.table = HistoryTable(self.get_show_fields(), self)
        self.fliterWidget = FliterWidget(self)

        self.limit_layout = QHBoxLayout()
        self.previous_button = QPushButton(_translate("Form", "上一页"))
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setValue(1)
        self.next_button = QPushButton(_translate("Form", "下一页"))
        self.one_page_combo = QComboBox()
        self.one_page_combo.addItems(
            ["10", "20", "50", "100", "200", "500", "1000"])
        self.limit_label = QLabel("")
        self.limit_layout.addItem(QSpacerItem(
            10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.limit_layout.addWidget(self.limit_label)
        self.limit_layout.addWidget(self.previous_button)
        self.limit_layout.addWidget(self.page_spin)
        self.limit_layout.addWidget(self.next_button)
        self.limit_layout.addWidget(self.one_page_combo)

        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.fliterWidget)
        self.layout.addWidget(self.table)
        self.layout.addLayout(self.limit_layout)
        self.setLayout(self.layout)

        self.init_connect()
        self.load_data()

    def init_connect(self):
        self.query_button.clicked.connect(self.on_query_button_clicked)
        self.previous_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        self.one_page_combo.currentTextChanged.connect(self.one_page_changed)
        self.page_spin.valueChanged.connect(self.page_changed)

    def on_query_button_clicked(self):
        if self.page_spin.value() > 1:
            self.page_spin.setValue(1)
        else:
            self.load_data()

    def previous_page(self):
        self.page_spin.setValue(self.page_spin.value() - 1)

    def next_page(self):
        self.page_spin.setValue(self.page_spin.value() + 1)

    def one_page_changed(self, text):
        self.limit_changed()

    def page_changed(self, value):
        self.limit_changed()

    def limit_changed(self):
        self.load_data()

    def get_limit_str(self):
        return f" limit {self.one_page_combo.currentText()} offset {(self.page_spin.value() - 1) * int(self.one_page_combo.currentText())}"

    def load_data(self):
        # 判断是否存在历史记录数据库
        if not (Path(get_paths()) / "history.db").exists():
            QMessageBox.warning(self, "错误", "历史记录数据库不存在")
            return
        try:
            conn = sqlite3.connect(Path(get_paths()) / "history.db")
            conn.row_factory = sqlite3.Row  # 设置行工厂
            cursor = conn.cursor()
            filter_str = self.fliterWidget.gen_fliter_str()
            sql = f"select *,COUNT(*) OVER() AS total_count from history"
            if filter_str:
                sql += " where " + filter_str
            elif filter_str is None:
                return
            sql += self.get_limit_str()
            cursor.execute(sql)
            datas = cursor.fetchall()

            if not datas:
                self.page_spin.setMaximum(1)
                self.limit_label.setText(f'共0行,0页')
            else:
                self.page_spin.setMaximum(
                    math.ceil(datas[0]['total_count'] / int(self.one_page_combo.currentText())))
                self.limit_label.setText(
                    f'共{datas[0]["total_count"]}行,{self.page_spin.maximum()}页')

            history_data = [HistoryData.from_dict(
                dict(data)) for data in datas]
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.warning(
                self, "错误", f"加载历史记录数据失败: {e}")
            return

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
