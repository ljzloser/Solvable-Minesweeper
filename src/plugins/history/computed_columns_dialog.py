"""
计算列管理对话框

支持添加、编辑、删除计算列，并验证 SQL 表达式。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QMessageBox,
)

from shared_types.widgets import ConfirmDialog
from .computed_column import ComputedColumn

_translate = QCoreApplication.translate


class ComputedColumnsDialog(ConfirmDialog):
    """计算列管理对话框"""

    def __init__(self, columns: list[ComputedColumn], db_path: Path, parent=None):
        self._columns = [ComputedColumn(col.name, col.expression, col.result_type)
                         for col in columns]
        self._db_path = db_path
        super().__init__(parent, title=_translate("Form", "计算列管理"))
        self.resize(600, 400)

    def _create_content(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 表格
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels([
            _translate("Form", "列名"),
            _translate("Form", "SQL表达式"),
            _translate("Form", "结果类型"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        # 按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton(_translate("Form", "添加"))
        self.del_btn = QPushButton(_translate("Form", "删除"))
        self.validate_btn = QPushButton(_translate("Form", "验证"))
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addWidget(self.validate_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 初始化表格
        self._init_table()

        # 连接信号
        self.add_btn.clicked.connect(self._add_row)
        self.del_btn.clicked.connect(self._del_row)
        self.validate_btn.clicked.connect(self._validate_all)

        return layout

    def _init_table(self):
        """用已有计算列填充表格"""
        for col in self._columns:
            self._add_column_row(col)

    def _add_column_row(self, col: ComputedColumn | None = None):
        """添加一行"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 列名
        name_item = QTableWidgetItem(col.name if col else "")
        self.table.setItem(row, 0, name_item)

        # SQL 表达式
        expr_item = QTableWidgetItem(col.expression if col else "")
        self.table.setItem(row, 1, expr_item)

        # 结果类型
        type_combo = QComboBox()
        type_combo.addItems(["float", "int"])
        if col and col.result_type == "int":
            type_combo.setCurrentIndex(1)
        self.table.setCellWidget(row, 2, type_combo)

    def _add_row(self):
        self._add_column_row()

    def _del_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _validate_all(self):
        """验证所有表达式能否创建视图"""
        columns = self._collect_columns()
        if not columns:
            QMessageBox.information(
                self,
                _translate("Form", "验证"),
                _translate("Form", "没有计算列需要验证"),
            )
            return

        # 检查列名合法性
        for col in columns:
            if not col.name.strip():
                QMessageBox.warning(
                    self,
                    _translate("Form", "验证失败"),
                    _translate("Form", "列名不能为空"),
                )
                return
            if not col.name.isidentifier():
                QMessageBox.warning(
                    self,
                    _translate("Form", "验证失败"),
                    _translate("Form", "列名 '%1' 不是合法标识符").replace(
                        "%1", col.name),
                )
                return

        # 尝试创建视图验证
        view_sql = ComputedColumn.build_view_sql(columns)
        if not view_sql or not self._db_path.exists():
            QMessageBox.warning(
                self,
                _translate("Form", "验证失败"),
                _translate("Form", "无法验证：数据库不存在"),
            )
            return

        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DROP VIEW IF EXISTS _validate_view")
            try:
                cursor.execute(view_sql.replace(
                    "history_view", "_validate_view"))
                conn.commit()
                QMessageBox.information(
                    self,
                    _translate("Form", "验证通过"),
                    _translate("Form", "所有 %1 个计算列表达式有效").replace(
                        "%1", str(len(columns))
                    ),
                )
            except sqlite3.Error as e:
                conn.rollback()
                QMessageBox.warning(
                    self,
                    _translate("Form", "验证失败"),
                    _translate("Form", "SQL 错误: %1").replace("%1", str(e)),
                )
            finally:
                cursor.execute("DROP VIEW IF EXISTS _validate_view")
                conn.commit()
        finally:
            conn.close()

    def _collect_columns(self) -> list[ComputedColumn]:
        """从表格收集计算列"""
        columns = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            expr_item = self.table.item(row, 1)
            type_widget = self.table.cellWidget(row, 2)

            name = name_item.text().strip() if name_item else ""
            expression = expr_item.text().strip() if expr_item else ""
            result_type = type_widget.currentText() if type_widget else "float"

            if name and expression:
                columns.append(ComputedColumn(name, expression, result_type))
        return columns

    def get_columns(self) -> list[ComputedColumn]:
        """获取对话框中的计算列列表"""
        return self._collect_columns()
