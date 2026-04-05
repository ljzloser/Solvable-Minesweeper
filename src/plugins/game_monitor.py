"""
示例插件：简单游戏监控插件

功能：
- 监听游戏开始、局面刷新、游戏结束事件
- 界面显示局面网格
- 按钮控制新游戏
"""

from plugin_manager import BasePlugin, PluginInfo, make_plugin_icon
from shared_types import (
    GameStartedEvent,
    GameEndedEvent,
    BoardUpdateEvent,
    NewGameCommand,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QGroupBox,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont


class GameMonitorPlugin(BasePlugin):
    """游戏监控插件"""

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="game_monitor",
            description="游戏监控插件",
            icon=make_plugin_icon("#1976d2", "🎮"),
        )

    # 局面值的颜色映射
    CELL_COLORS = {
        0: "#C0C0C0",  # 空
        1: "#0000FF",  # 1 - 蓝
        2: "#008000",  # 2 - 绿
        3: "#FF0000",  # 3 - 红
        4: "#000080",  # 4 - 深蓝
        5: "#800000",  # 5 - 棕
        6: "#008080",  # 6 - 青
        7: "#000000",  # 7 - 黑
        8: "#808080",  # 8 - 灰
        10: "#C0C0C0",  # 未打开
        11: "#C0C0C0",  # 标雷
        14: "#FF0000",  # 踩雷(叉雷)
        15: "#FF0000",  # 踩雷(红雷)
        16: "#FFFFFF",  # 白雷
    }

    def __init__(self, info):
        super().__init__(info)
        self._game_rows = 0
        self._game_cols = 0
        self._game_mines = 0
        self._board = []

    def _setup_subscriptions(self) -> None:
        self.subscribe(GameStartedEvent, self._on_game_started)
        self.subscribe(GameEndedEvent, self._on_game_ended)
        self.subscribe(BoardUpdateEvent, self._on_board_update)

    def _create_widget(self):
        """创建界面"""

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 状态显示区
        status_group = QGroupBox("游戏状态")
        status_layout = QVBoxLayout(status_group)

        self._status_label = QLabel("等待游戏...")
        self._status_label.setStyleSheet("font-size: 14px; padding: 5px;")
        status_layout.addWidget(self._status_label)

        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self._info_label)

        layout.addWidget(status_group)

        # 局面显示区
        board_group = QGroupBox("局面")
        board_layout = QVBoxLayout(board_group)

        self._board_table = QTableWidget()
        self._board_table.setMinimumHeight(200)
        self._board_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._board_table.setSelectionMode(QTableWidget.NoSelection)
        self._board_table.setFocusPolicy(Qt.NoFocus)
        board_layout.addWidget(self._board_table)

        layout.addWidget(board_group)

        # 控制区
        control_group = QGroupBox("新游戏控制")
        control_layout = QVBoxLayout(control_group)

        # 行列雷数设置
        param_layout = QHBoxLayout()

        param_layout.addWidget(QLabel("行:"))
        self._rows_spin = QSpinBox()
        self._rows_spin.setRange(1, 100)
        self._rows_spin.setValue(16)
        param_layout.addWidget(self._rows_spin)

        param_layout.addWidget(QLabel("列:"))
        self._cols_spin = QSpinBox()
        self._cols_spin.setRange(1, 100)
        self._cols_spin.setValue(30)
        param_layout.addWidget(self._cols_spin)

        param_layout.addWidget(QLabel("雷:"))
        self._mines_spin = QSpinBox()
        self._mines_spin.setRange(1, 999)
        self._mines_spin.setValue(99)
        param_layout.addWidget(self._mines_spin)

        control_layout.addLayout(param_layout)

        # 按钮
        self._new_game_btn = QPushButton("开始新游戏")
        self._new_game_btn.clicked.connect(self._on_new_game_clicked)
        control_layout.addWidget(self._new_game_btn)

        layout.addWidget(control_group)

        # 日志区
        log_group = QGroupBox("事件日志")
        log_layout = QVBoxLayout(log_group)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(100)
        log_layout.addWidget(self._log_text)

        layout.addWidget(log_group)

        return widget

    def _log(self, msg: str) -> None:
        """添加日志并滚动到底部"""
        if self._log_text:
            self._log_text.append(msg)
            # 滚动到最后一行
            scrollbar = self._log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _render_board(self) -> None:
        """渲染局面"""
        if not self._board_table or not self._board:
            return

        rows = len(self._board)
        cols = len(self._board[0]) if rows > 0 else 0

        self._board_table.setRowCount(rows)
        self._board_table.setColumnCount(cols)

        # 计算单元格大小
        cell_size = max(12, min(25, 400 // max(rows, cols)))

        for i in range(rows):
            self._board_table.setRowHeight(i, cell_size)
            for j in range(cols):
                val = self._board[i][j] if j < len(self._board[i]) else 10
                item = QTableWidgetItem()

                # 设置文字
                if val == 0:
                    item.setText("")
                elif 1 <= val <= 8:
                    item.setText(str(val))
                elif val == 10:
                    item.setText("")
                elif val == 11:
                    item.setText("🚩")
                elif val in (14, 15, 16):
                    item.setText("💣")
                else:
                    item.setText("")

                # 设置颜色
                color = self.CELL_COLORS.get(val, "#C0C0C0")
                item.setBackground(QColor(color))
                if val in (1, 4, 7):
                    item.setForeground(QColor("#0000FF"))
                elif val == 2:
                    item.setForeground(QColor("#008000"))
                elif val == 3:
                    item.setForeground(QColor("#FF0000"))

                item.setTextAlignment(Qt.AlignCenter)
                font = QFont()
                font.setBold(True)
                font.setPointSize(max(6, cell_size // 3))
                item.setFont(font)

                self._board_table.setItem(i, j, item)

        # 设置列宽
        for j in range(cols):
            self._board_table.setColumnWidth(j, cell_size)

        # 隐藏表头
        self._board_table.horizontalHeader().hide()
        self._board_table.verticalHeader().hide()

    def _on_game_started(self, event: GameStartedEvent) -> None:
        self._game_rows = event.rows
        self._game_cols = event.cols
        self._game_mines = event.mines
        self._board = []

        self._status_label.setText("🎮 游戏进行中")
        self._status_label.setStyleSheet("font-size: 14px; padding: 5px; color: green;")
        self._info_label.setText(f"局面: {event.rows}x{event.cols}, {event.mines}雷")
        msg = f"游戏开始: {event.rows}x{event.cols}, {event.mines}雷"
        self._log(f"🎮 {msg}")
        self.logger.info(msg)

    def _on_game_ended(self, event: GameEndedEvent) -> None:
        result = "🎉 胜利" if event.is_win else "💥 失败"
        color = "green" if event.is_win else "red"

        self._status_label.setText(f"{result}! 用时 {event.time:.2f}秒")
        self._status_label.setStyleSheet(
            f"font-size: 14px; padding: 5px; color: {color};"
        )
        msg = f"{result}: 用时 {event.time:.2f}秒"
        self._log(msg)
        self.logger.info(msg)

    def _on_board_update(self, event: BoardUpdateEvent) -> None:
        self._board = event.board
        self._render_board()
        rows = len(event.board)
        msg = f"局面刷新: {rows}行"
        self._log(f"📊 {msg}")
        self.logger.debug(msg)

    def _on_new_game_clicked(self) -> None:
        """新游戏按钮点击"""
        rows = self._rows_spin.value()
        cols = self._cols_spin.value()
        mines = self._mines_spin.value()

        cmd = NewGameCommand(rows=rows, cols=cols, mines=mines)
        self.send_command(cmd)
        msg = f"发送新游戏指令: {rows}x{cols}, {mines}雷"
        self._log(f"📤 {msg}")
        self.logger.info(msg)

    def on_initialized(self) -> None:
        self._log("✅ 插件已初始化")
        self.logger.info("游戏监控插件已初始化")
