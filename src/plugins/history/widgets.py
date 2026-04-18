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
from typing import Any, cast

from PyQt5.QtCore import QEvent, Qt, QCoreApplication, QModelIndex, QTimer, pyqtSignal
from PyQt5.QtGui import QCloseEvent as _QCloseEvent, QStandardItemModel, QStandardItem, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QWidget,
    QVBoxLayout,
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
    QSplitter,
    QSizePolicy,
    QLabel,
    QHeaderView,
    QStyledItemDelegate,
    QStyle,
    QApplication,
)

from plugin_manager.app_paths import get_executable_dir

from shared_types.widgets import EditableComboBox

from .models import HistoryData, LogicSymbol, CompareSymbol
from .table_model import HistoryTableModel

_translate = QCoreApplication.translate


class ComboBoxDelegate(QStyledItemDelegate):
    """通用的 ComboBox 代理"""

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        self._items = items

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self._items)
        return editor

    def setEditorData(self, editor: QComboBox, index):
        value = index.model().data(index, Qt.EditRole)
        if value:
            idx = editor.findText(value)
            if idx >= 0:
                editor.setCurrentIndex(idx)

    def setModelData(self, editor: QComboBox, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class EditableComboBoxDelegate(QStyledItemDelegate):
    """可编辑的 ComboBox 代理（带补全）"""

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        self._items = items

    def createEditor(self, parent, option, index):
        editor = EditableComboBox(self._items, parent)
        return editor

    def setEditorData(self, editor: EditableComboBox, index):
        value = index.model().data(index, Qt.EditRole)
        if value:
            editor.setCurrentText(value)

    def setModelData(self, editor: EditableComboBox, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class FilterValueDelegate(QStyledItemDelegate):
    """值列的智能代理，根据同行字段类型动态决定编辑器"""

    COL_FIELD = 1  # FilterModel.COL_FIELD
    COL_COMPARE = 2  # FilterModel.COL_COMPARE

    def __init__(self, float_decimals: int = 2, parent=None):
        super().__init__(parent)
        self._float_decimals = float_decimals
        self._editor_widgets = []  # 缓存创建的编辑器widget

    def paint(self, painter, option, index):
        """根据字段类型绘制单元格"""
        # 检查选中状态
        is_selected = option.state & QStyle.State_Selected

        if is_selected:  # type: ignore
            # 选中时绘制背景
            painter.fillRect(option.rect, option.palette.highlight())
            # 使用高亮文本颜色
            text_role = QPalette.HighlightedText
        else:
            text_role = QPalette.WindowText

        field_value, _, _ = self._get_field_info(index)
        raw_value = index.data(Qt.EditRole)

        if field_value is None or raw_value is None:
            super().paint(painter, option, index)
            return

        display_text = str(raw_value)

        if isinstance(field_value, datetime):
            # 日期类型显示为可读格式
            try:
                ts = int(raw_value)
                if ts > 1e15:  # 微秒
                    ts = ts / 1_000_000
                elif ts > 1e12:  # 毫秒
                    ts = ts / 1_000
                dt = datetime.fromtimestamp(ts)
                display_text = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError, OSError):
                display_text = raw_value
        elif isinstance(field_value, float):
            # 浮点数显示带小数位
            try:
                display_text = f"{float(raw_value):.{self._float_decimals}f}"
            except (ValueError, TypeError):
                display_text = raw_value

        # 使用 QStyle 绘制文本
        style = QApplication.style()
        style.drawItemText(
            painter,
            option.rect,
            Qt.AlignCenter | Qt.AlignVCenter,  # type: ignore
            option.palette,
            True,
            display_text,
            text_role
        )

    def _get_field_info(self, index: QModelIndex) -> tuple:
        """获取同行的字段信息和比较符"""
        model = index.model()
        row = index.row()

        # 获取字段名
        field_index = model.index(row, self.COL_FIELD)
        field_name = model.data(field_index, Qt.EditRole)

        # 获取比较符
        compare_index = model.index(row, self.COL_COMPARE)
        compare_text = model.data(compare_index, Qt.EditRole)

        if not field_name:
            return None, None, None

        try:
            field_value = HistoryData.get_field_value(field_name)
        except (KeyError, IndexError):
            return None, None, None

        compare = None
        if compare_text:
            try:
                compare = CompareSymbol.from_display_name(compare_text)
            except ValueError:
                pass

        return field_value, compare, field_name

    def _create_editor_by_type(self, parent, field_value, compare, field_name):
        """根据字段类型创建编辑器"""
        from shared_types.enums import BaseDiaPlayEnum

        # 如果是包含/不包含比较符，使用 LineEdit
        if compare and compare in (CompareSymbol.Contains, CompareSymbol.NotContains):
            return QLineEdit(parent)

        if isinstance(field_value, BaseDiaPlayEnum):
            editor = QComboBox(parent)
            editor.addItems([e.display_name for e in field_value.__class__])
            return editor
        elif isinstance(field_value, int):
            return QSpinBox(parent)
        elif isinstance(field_value, float):
            editor = QDoubleSpinBox(parent)
            editor.setDecimals(self._float_decimals)
            editor.setRange(-1e15, 1e15)
            return editor
        elif isinstance(field_value, datetime):
            editor = QDateTimeEdit(parent)
            editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            editor.setCalendarPopup(True)
            return editor
        else:
            return QLineEdit(parent)

    def createEditor(self, parent, option, index):
        field_value, compare, field_name = self._get_field_info(index)
        if field_value is None:
            return QLineEdit(parent)
        return self._create_editor_by_type(parent, field_value, compare, field_name)

    def setEditorData(self, editor, index):
        field_value, compare, field_name = self._get_field_info(index)
        if field_value is None:
            return

        raw_value = index.model().data(index, Qt.EditRole)

        from shared_types.enums import BaseDiaPlayEnum
        if isinstance(field_value, BaseDiaPlayEnum) and isinstance(editor, QComboBox):
            if raw_value:
                idx = editor.findText(raw_value)
                if idx >= 0:
                    editor.setCurrentIndex(idx)
        elif isinstance(field_value, int) and isinstance(editor, QSpinBox):
            try:
                editor.setValue(int(raw_value) if raw_value else 0)
            except (ValueError, TypeError):
                editor.setValue(0)
        elif isinstance(field_value, float) and isinstance(editor, QDoubleSpinBox):
            try:
                editor.setValue(float(raw_value) if raw_value else 0.0)
            except (ValueError, TypeError):
                editor.setValue(0.0)
        elif isinstance(field_value, datetime) and isinstance(editor, QDateTimeEdit):
            try:
                if raw_value:
                    # raw_value 可能是 int/float 时间戳，或字符串形式的时间戳
                    if isinstance(raw_value, (int, float)):
                        dt = datetime.fromtimestamp(raw_value / 1_000_000)
                    else:
                        # 先尝试作为字符串时间戳解析
                        try:
                            ts = int(raw_value)
                            if ts > 1e15:  # 微秒
                                ts = ts / 1_000_000
                            elif ts > 1e12:  # 毫秒
                                ts = ts / 1_000
                            dt = datetime.fromtimestamp(ts)
                        except (ValueError, TypeError):
                            # 再尝试解析日期时间字符串
                            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                                try:
                                    dt = datetime.strptime(raw_value, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                dt = datetime.now()
                else:
                    dt = datetime.now()
                editor.setDateTime(dt)
            except (ValueError, TypeError):
                editor.setDateTime(datetime.now())
        else:
            if isinstance(editor, QLineEdit):
                editor.setText(raw_value or "")

    def setModelData(self, editor, model, index):
        field_value, compare, field_name = self._get_field_info(index)
        if field_value is None:
            if isinstance(editor, QLineEdit):
                model.setData(index, editor.text(), Qt.EditRole)
            return

        from shared_types.enums import BaseDiaPlayEnum
        if isinstance(field_value, BaseDiaPlayEnum) and isinstance(editor, QComboBox):
            model.setData(index, editor.currentText(), Qt.EditRole)
        elif isinstance(field_value, (int, float)) and isinstance(editor, (QSpinBox, QDoubleSpinBox)):
            model.setData(index, str(editor.value()), Qt.EditRole)
        elif isinstance(field_value, datetime) and isinstance(editor, QDateTimeEdit):
            ts = int(editor.dateTime().toPyDateTime().timestamp() * 1_000_000)
            model.setData(index, str(ts), Qt.EditRole)
        else:
            if isinstance(editor, QLineEdit):
                model.setData(index, editor.text(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class AutoEditTableView(QTableView):
    """自动进入编辑状态的 TableView"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._auto_edit_columns = set()  # 需要自动编辑的列
        self.suppress_auto_edit = False  # 标记是否阻止自动编辑
        self.clicked.connect(self._on_click_auto_edit)
        # 垂直表头点击选中整行
        self.verticalHeader().sectionClicked.connect(self._on_header_select_row)
        self.verticalHeader().setMaximumWidth(24)
        self.verticalHeader().setMinimumWidth(24)

    def mousePressEvent(self, event):
        """鼠标按下事件：右键点击时阻止自动编辑"""
        # 右键点击，阻止自动编辑
        if event.button() == Qt.RightButton:
            self.suppress_auto_edit = True
        super().mousePressEvent(event)
        self.reset_suppress_flag()

    def reset_suppress_flag(self):
        """重置阻止自动编辑标志"""
        self.suppress_auto_edit = False

    def setAutoEditColumn(self, column: int):
        """设置指定列自动进入编辑"""
        self._auto_edit_columns.add(column)

    def setAutoEditColumns(self, columns: list[int]):
        """设置多个列自动进入编辑"""
        self._auto_edit_columns.update(columns)

    def _on_header_select_row(self, section: int):
        """通过垂直表头点击选中整行时，清除单元格焦点"""
        self.selectRow(section)
        # 清除单元格焦点，让焦点回到 TableView 本身
        self.setFocus()

    def _on_click_auto_edit(self, index: QModelIndex):
        """鼠标点击时自动进入编辑"""
        # 如果 index 无效，不做任何操作
        if not index.isValid():
            return

        # 右键点击后不自动编辑
        if self.suppress_auto_edit:
            return

        # 如果模型没有行，不自动编辑
        model = self.model()
        if model is None or model.rowCount() == 0:
            return

        if index.column() in self._auto_edit_columns:
            if self.state() != QTableView.EditingState:
                self.edit(index)
            return

        # 如果不是自动编辑列，不进入编辑
        self.selectionModel().setCurrentIndex(index, self.selectionModel().NoUpdate)

    def currentChanged(self, current: QModelIndex, previous: QModelIndex):
        """当焦点单元格改变时，自动进入编辑状态（表头选择整行时不触发）"""
        super().currentChanged(current, previous)

        # 如果没有有效的单元格，不自动进入编辑
        if not current.isValid():
            return

        # 右键点击或表头选择整行，不自动进入编辑
        if self.suppress_auto_edit:
            return

        if current.column() in self._auto_edit_columns:
            QTimer.singleShot(0, lambda: self._try_edit(current))

    def _try_edit(self, index: QModelIndex):
        """尝试进入编辑状态"""
        if self.state() != QTableView.EditingState:
            self.edit(index)

    def addRow(self):
        """添加一行"""
        self.suppress_auto_edit = True
        model = self.model()
        if model is None:
            return

        model.insertRow(model.rowCount())
        self.suppress_auto_edit = False

    def insertRow(self, row: int):
        """插入一行"""
        self.suppress_auto_edit = True
        model = self.model()
        if model is None:
            return

        model.insertRow(row)
        self.suppress_auto_edit = False

    def removeRow(self, row: int):
        """删除一行"""
        self.suppress_auto_edit = True
        model = self.model()
        if model is None:
            return

        model.removeRow(row)
        self.suppress_auto_edit = False


class FilterModel(QStandardItemModel):
    """过滤表格模型"""

    COL_LBRACKET, COL_FIELD, COL_COMPARE, COL_VALUE, COL_RBRACKET, COL_LOGIC = range(
        6)

    def __init__(self, parent=None):
        super().__init__(0, 6, parent)
        self.setHorizontalHeaderLabels(
            ["左括号", "字段", "比较符", "值", "右括号", "逻辑符"]
        )

    def data(self, index, role=Qt.DisplayRole):
        """重写 data 方法，格式化某些列的显示"""
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            column = index.column()
            raw_data = super().data(index, Qt.EditRole)

            # 值列需要格式化显示
            if column == self.COL_VALUE:
                if not raw_data:
                    return ""

                # 获取同行字段名来确定类型
                field_index = self.index(index.row(), self.COL_FIELD)
                field_name = super().data(field_index, Qt.EditRole)

                if field_name:
                    field_value = HistoryData.get_field_value(field_name)
                    if isinstance(field_value, datetime):
                        # 尝试解析时间戳并格式化为可读格式
                        try:
                            ts = int(raw_data)
                            if ts > 1e15:  # 微秒
                                ts = ts / 1_000_000
                            elif ts > 1e12:  # 毫秒
                                ts = ts / 1_000
                            dt = datetime.fromtimestamp(ts)
                            return dt.strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, TypeError, OSError):
                            return raw_data

            return raw_data

        return super().data(index, role)

    def get_row_data(self, row: int) -> dict:
        """获取指定行的所有数据"""
        return {
            "left_bracket": self.data(self.index(row, self.COL_LBRACKET)),
            "field": self.data(self.index(row, self.COL_FIELD)),
            "compare": self.data(self.index(row, self.COL_COMPARE)),
            "value": self.data(self.index(row, self.COL_VALUE)),
            "right_bracket": self.data(self.index(row, self.COL_RBRACKET)),
            "logic": self.data(self.index(row, self.COL_LOGIC)),
        }

    def get_field_value_type(self, row: int):
        """获取指定行字段的原始值类型"""
        field_name = str(self.data(self.index(row, self.COL_FIELD)))
        return HistoryData.get_field_value(field_name)


class SortModel(QStandardItemModel):
    """排序表格模型"""

    COL_FIELD, COL_ORDER = range(2)

    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["排序字段", "升序/降序"])

    def get_row_data(self, row: int) -> dict:
        """获取指定行的所有数据"""
        return {
            "field": self.data(self.index(row, self.COL_FIELD)),
            "order": self.data(self.index(row, self.COL_ORDER)),
        }


class FilterWidget(QWidget):
    """筛选条件控件"""

    def __init__(self, float_decimals: int = 2, parent=None):
        super().__init__(parent)
        self._float_decimals = float_decimals

        # 使用 QSplitter 实现横向分割
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左侧：过滤表格
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.table = AutoEditTableView()
        self.table.setModel(FilterModel(self))
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setSelectionBehavior(QTableView.SelectItems)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # 设置所有列自动进入编辑
        self.table.setAutoEditColumns(
            list(range(FilterModel.COL_LBRACKET, FilterModel.COL_LOGIC + 1)))
        # 禁用双击编辑
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        filter_layout.addWidget(self.table)
        splitter.addWidget(filter_widget)

        # 右侧：排序表格
        sort_widget = QWidget()
        sort_layout = QVBoxLayout(sort_widget)
        sort_layout.setContentsMargins(0, 0, 0, 0)
        sort_layout.setSpacing(0)

        self.sort_table = AutoEditTableView()
        self.sort_table.setModel(SortModel(self))
        self.sort_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.sort_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.sort_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sort_table.customContextMenuRequested.connect(
            self.show_sort_context_menu)
        self.sort_table.setSelectionBehavior(QTableView.SelectItems)
        self.sort_table.setSelectionMode(QTableView.ExtendedSelection)
        self.sort_table.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # 设置所有列自动进入编辑
        self.sort_table.setAutoEditColumns(
            [SortModel.COL_FIELD, SortModel.COL_ORDER])
        # 禁用双击编辑
        self.sort_table.setEditTriggers(QTableView.NoEditTriggers)
        sort_layout.addWidget(self.sort_table)
        splitter.addWidget(sort_widget)

        # 设置初始比例
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setMinimumSize(0, 0)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self._setup_delegates()
        self._connect_field_change_signal()

    def _connect_field_change_signal(self):
        """当字段列改变时，更新值列的默认值"""
        self.table.model().dataChanged.connect(self._on_field_changed)

    def _on_field_changed(self, topLeft, bottomRight, roles):
        """字段列改变时触发"""
        if Qt.EditRole in roles and topLeft.column() == FilterModel.COL_FIELD:
            for row in range(topLeft.row(), bottomRight.row() + 1):
                self._update_value_default(row)

    def _update_value_default(self, row: int):
        """更新指定行的值列默认值"""
        model = self.table.model()
        field_name = model.data(model.index(row, FilterModel.COL_FIELD))

        if not field_name:
            return

        field_value = HistoryData.get_field_value(field_name)
        new_default = self._get_default_value(field_value)

        # 获取当前值（使用 EditRole 获取原始数据）
        current_value = model.data(model.index(
            row, FilterModel.COL_VALUE), Qt.EditRole)

        # 始终更新为新类型的默认值
        model.setData(
            model.index(row, FilterModel.COL_VALUE),
            new_default,
            Qt.EditRole
        )

    def _get_default_value(self, field_value) -> str:
        """获取字段类型的默认值"""
        from shared_types.enums import BaseDiaPlayEnum

        if field_value is None:
            return ""
        elif isinstance(field_value, BaseDiaPlayEnum):
            # 枚举类型返回第一个选项
            return field_value.__class__.display_names()[0]
        elif isinstance(field_value, datetime):
            # 日期类型返回当前时间戳（微秒）
            ts = int(datetime.now().timestamp() * 1_000_000)
            return str(ts)
        elif isinstance(field_value, float):
            return "0.0"
        elif isinstance(field_value, int):
            return "0"
        else:
            return ""

    def _setup_delegates(self):
        """设置列代理"""
        # 左括号
        self.table.setItemDelegateForColumn(
            FilterModel.COL_LBRACKET,
            ComboBoxDelegate(["", "(", "(("], self)
        )
        # 字段
        self.table.setItemDelegateForColumn(
            FilterModel.COL_FIELD,
            EditableComboBoxDelegate(HistoryData.fields(), self)
        )
        # 比较符
        self.table.setItemDelegateForColumn(
            FilterModel.COL_COMPARE,
            ComboBoxDelegate(CompareSymbol.display_names(), self)
        )
        # 值列 - 使用智能代理
        self.table.setItemDelegateForColumn(
            FilterModel.COL_VALUE,
            FilterValueDelegate(self._float_decimals, self)
        )
        # 右括号
        self.table.setItemDelegateForColumn(
            FilterModel.COL_RBRACKET,
            ComboBoxDelegate(["", ")", "))"], self)
        )
        # 逻辑符
        self.table.setItemDelegateForColumn(
            FilterModel.COL_LOGIC,
            ComboBoxDelegate(LogicSymbol.display_names(), self)
        )

        # 排序表格代理
        self.sort_table.setItemDelegateForColumn(
            SortModel.COL_FIELD,
            EditableComboBoxDelegate(HistoryData.fields(), self)
        )
        self.sort_table.setItemDelegateForColumn(
            SortModel.COL_ORDER,
            ComboBoxDelegate(
                [_translate("Form", "升序"), _translate("Form", "降序")], self
            )
        )

    def show_sort_context_menu(self, pos):
        """排序列表右键菜单"""
        menu = QMenu(self)
        menu.addAction(_translate("Form", "添加"), self._add_sort_row)
        menu.addAction(_translate("Form", "插入"), self._insert_sort_row)
        menu.addAction(_translate("Form", "删除"), self._del_sort_row)
        menu.exec_(self.sort_table.mapToGlobal(pos))

    def _add_sort_row(self):
        """添加排序行"""
        model = self.sort_table.model()
        row = model.rowCount()
        model.insertRow(row)
        model.setData(model.index(row, SortModel.COL_FIELD),
                      HistoryData.fields()[0])
        model.setData(model.index(row, SortModel.COL_ORDER),
                      _translate("Form", "升序"))

    def _add_sort_row_at(self, row: int, field: str | None = None, order: str | None = None):
        """在指定位置添加排序行"""
        model = self.sort_table.model()
        if field is None:
            field = HistoryData.fields()[0]
        if order is None:
            order = _translate("Form", "升序")

        self.sort_table.insertRow(row)
        model.setData(model.index(row, SortModel.COL_FIELD), field)
        model.setData(model.index(row, SortModel.COL_ORDER), order)

    def _insert_sort_row(self):
        """在当前行前插入排序行"""
        current_row = self.sort_table.currentIndex().row()
        self._add_sort_row_at(current_row if current_row >= 0 else 0)

    def _del_sort_row(self):
        """删除选中的排序行"""
        selected_rows = set(
            index.row() for index in self.sort_table.selectionModel().selectedIndexes())
        if not selected_rows:
            return
        for row in sorted(selected_rows, reverse=True):
            self.sort_table.removeRow(row)

    def _del_sort_row_at(self, row: int):
        """删除指定行的排序"""
        if row >= 0:
            self.sort_table.removeRow(row)

    def gen_order_str(self) -> str:
        """生成排序 SQL 语句"""
        model = self.sort_table.model()
        if model.rowCount() == 0:
            return ""

        orders = []
        for row in range(model.rowCount()):
            field = model.data(model.index(row, SortModel.COL_FIELD))
            order_text = model.data(model.index(row, SortModel.COL_ORDER))
            order_sql = "ASC" if order_text == _translate(
                "Form", "升序") else "DESC"
            orders.append(f"{field} {order_sql}")

        if orders:
            return " ORDER BY " + ", ".join(orders)
        return ""

    def set_float_decimals(self, decimals: int) -> None:
        """动态设置小数位数"""
        self._float_decimals = decimals
        # 更新值列代理
        self.table.setItemDelegateForColumn(
            FilterModel.COL_VALUE,
            FilterValueDelegate(self._float_decimals, self)
        )

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction(_translate("Form", "添加"), self.add_row)
        menu.addAction(
            _translate("Form", "插入"), lambda: self.insert_row(
                self.table.currentIndex().row())
        )
        menu.addAction(_translate("Form", "删除"), self.del_row)
        menu.exec_(self.table.mapToGlobal(pos))

    def add_row(self):
        self.insert_row(self.table.model().rowCount())

    def del_row(self):
        # 获取所有选中的行
        selected_rows = set(index.row()
                            for index in self.table.selectionModel().selectedIndexes())
        if not selected_rows:
            return
        # 取消行选中
        self.table.clearSelection()
        # 从后往前删除，避免索引变化
        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)

    def insert_row(self, row: int):
        if row < 0:
            row = 0
        model = self.table.model()
        self.table.insertRow(row)
        # 设置默认值
        model.setData(model.index(row, FilterModel.COL_FIELD),
                      HistoryData.fields()[0])
        model.setData(model.index(row, FilterModel.COL_COMPARE),
                      CompareSymbol.display_names()[0])
        model.setData(model.index(row, FilterModel.COL_LOGIC),
                      LogicSymbol.display_names()[0])
        # 不需要手动设置值，代理会根据字段类型自动处理

    def gen_filter_str(self):
        model = cast(FilterModel, self.table.model())
        filter_str = ""
        left_count = 0
        right_count = 0
        for row in range(model.rowCount()):
            data = model.get_row_data(row)
            field_value_type = model.get_field_value_type(row)

            left_bracket = data["left_bracket"] or ""
            field = data["field"] or ""
            compare_text = data["compare"] or ""
            value = data["value"] or ""
            right_bracket = data["right_bracket"] or ""
            logic_text = data["logic"] or ""

            if not field or not compare_text:
                continue

            compare = CompareSymbol.from_display_name(compare_text)
            logic = LogicSymbol.from_display_name(logic_text).to_sql

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

            # 处理值
            from shared_types.enums import BaseDiaPlayEnum
            if isinstance(field_value_type, BaseDiaPlayEnum):
                enum_cls = field_value_type.__class__
                for e in enum_cls:
                    if e.display_name == value:
                        value = str(e.value)
                        break
            elif compare in (CompareSymbol.Contains, CompareSymbol.NotContains):
                if isinstance(field_value_type, (int, float)):
                    values = value.split(",")
                    for v in values:
                        if not v.replace("-", "").replace(".", "").isdigit():
                            QMessageBox.warning(
                                self, "错误", f"第{row}行 {v} 不是数字"
                            )
                            return None
                    value = ",".join(v for v in values)
                elif isinstance(field_value_type, datetime):
                    values = value.split(",")
                    parsed_values = []
                    for v in values:
                        v = v.strip()
                        if not v:
                            continue
                        try:
                            # 尝试解析为时间戳（微秒）
                            ts = int(float(v))
                            parsed_values.append(str(ts))
                        except ValueError:
                            # 尝试解析为日期时间字符串
                            try:
                                for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                                    try:
                                        dt = datetime.strptime(v, fmt)
                                        parsed_values.append(
                                            str(int(dt.timestamp() * 1_000_000)))
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    raise ValueError(f"无法解析日期: {v}")
                            except ValueError as e:
                                QMessageBox.warning(
                                    self, "错误", f"第{row}行 {v} 不是合法的日期时间"
                                )
                                return None
                    value = ",".join(parsed_values) if parsed_values else ""
                else:
                    value = ",".join(
                        f"'{v}'" for v in value.split(",") if v.strip())
                value = f"({value})" if value else "()"
            elif isinstance(field_value_type, datetime) and value:
                try:
                    # 可能是时间戳字符串
                    ts = int(float(value))
                    value = str(ts)
                except ValueError:
                    # 尝试解析日期时间字符串
                    try:
                        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                            try:
                                dt = datetime.strptime(value, fmt)
                                value = str(int(dt.timestamp() * 1_000_000))
                                break
                            except ValueError:
                                continue
                        else:
                            QMessageBox.warning(
                                self, "错误", f"第{row}行 {value} 不是合法的日期时间"
                            )
                            return None
                    except ValueError:
                        QMessageBox.warning(
                            self, "错误", f"第{row}行 {value} 不是合法的日期时间"
                        )
                        return None
            elif value and not value.startswith("'"):
                value = f"'{value}'"

            is_last = row == model.rowCount() - 1
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

    # 信号：列显示配置变化 (show_fields_json)
    show_fields_changed = pyqtSignal(str)

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
            parent_widget.load_data()  # type: ignore

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
        self.show_fields_changed.emit(json.dumps(
            list(self.showFields), ensure_ascii=False))

    def _get_current_replay_id(self) -> int | None:
        row_idx = self.table.currentIndex().row()
        if row_idx < 0:
            return None
        visible = self.model._visible_headers
        if "replay_id" in visible:
            col = visible.index("replay_id")
            rid = self.model.data(self.model.index(row_idx, col), Qt.UserRole)
            return rid  # type: ignore
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

    # 信号：排序和过滤状态变化 (filter_json, sort_json)
    filter_sort_state_changed = pyqtSignal(str, str)
    # 信号：列显示配置变化 (show_fields_json)
    show_fields_changed = pyqtSignal(str)

    def __init__(
        self,
        db_path: Path,
        config_path: Path,
        float_decimals: int = 2,
        page_size: str = "50",
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
        # 设置默认每页条数
        idx = self.one_page_combo.findText(page_size)
        if idx >= 0:
            self.one_page_combo.setCurrentIndex(idx)

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

    def set_filter_sort_state(self, filter_json: str, sort_json: str) -> None:
        """设置排序和过滤状态（由插件调用）"""
        try:
            filter_rows = json.loads(filter_json)
            if filter_rows:
                self._set_filter_rows(filter_rows)
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            sort_rows = json.loads(sort_json)
            if sort_rows:
                self._set_sort_rows(sort_rows)
        except (json.JSONDecodeError, TypeError):
            pass

        # 恢复后触发一次查询
        self._on_query()

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
        self.table.show_fields_changed.connect(self.show_fields_changed)

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
            order_str = self.filter_widget.gen_order_str()
            sql = "SELECT *, COUNT(*) OVER() AS total_count FROM history"
            if filter_str:
                sql += " WHERE " + filter_str
            elif filter_str is None:
                return
            sql += order_str
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

        # 保存当前的排序和过滤状态
        self._save_filter_sort_state()

    def _get_filter_rows(self) -> list[dict]:
        """获取过滤表格的所有行数据"""
        model = cast(FilterModel, self.filter_widget.table.model())
        rows = []
        for row in range(model.rowCount()):
            rows.append(model.get_row_data(row))
        return rows

    def _get_sort_rows(self) -> list[dict]:
        """获取排序表格的所有行数据"""
        model = cast(SortModel, self.filter_widget.sort_table.model())
        rows = []
        for row in range(model.rowCount()):
            rows.append(model.get_row_data(row))
        return rows

    def _set_filter_rows(self, rows: list[dict]) -> None:
        """恢复过滤表格的行数据"""
        model = self.filter_widget.table.model()
        model.removeRows(0, model.rowCount())
        for row_data in rows:
            row = model.rowCount()
            model.insertRow(row)
            model.setData(model.index(row, FilterModel.COL_LBRACKET),
                          row_data.get("left_bracket"))
            model.setData(model.index(row, FilterModel.COL_FIELD),
                          row_data.get("field"))
            model.setData(model.index(row, FilterModel.COL_COMPARE),
                          row_data.get("compare"))
            model.setData(model.index(row, FilterModel.COL_VALUE),
                          row_data.get("value"), Qt.EditRole)
            model.setData(model.index(row, FilterModel.COL_RBRACKET),
                          row_data.get("right_bracket"))
            model.setData(model.index(row, FilterModel.COL_LOGIC),
                          row_data.get("logic"))

    def _set_sort_rows(self, rows: list[dict]) -> None:
        """恢复排序表格的行数据"""
        model = self.filter_widget.sort_table.model()
        model.removeRows(0, model.rowCount())
        for row_data in rows:
            row = model.rowCount()
            model.insertRow(row)
            model.setData(model.index(row, SortModel.COL_FIELD),
                          row_data.get("field"))
            model.setData(model.index(row, SortModel.COL_ORDER),
                          row_data.get("order"))

    def _save_filter_sort_state(self) -> None:
        """发射排序和过滤状态变化信号"""
        filter_rows = self._get_filter_rows()
        sort_rows = self._get_sort_rows()
        self.filter_sort_state_changed.emit(
            json.dumps(filter_rows, ensure_ascii=False), json.dumps(sort_rows, ensure_ascii=False))

    def closeEvent(self, event: _QCloseEvent):
        """关闭事件"""
        super().closeEvent(event)

    def set_float_decimals(self, decimals: int) -> None:
        """动态设置小数位数"""
        self.filter_widget.set_float_decimals(decimals)

    def restore_show_fields(self, show_fields_json: str) -> None:
        """恢复列显示配置"""
        try:
            fields = json.loads(show_fields_json)
            if not fields:
                fields = self.table.HEADERS
            self.table.showFields = set(fields)
            self.table.model.update_show_fields(self.table.showFields)
        except (json.JSONDecodeError, TypeError):
            pass
