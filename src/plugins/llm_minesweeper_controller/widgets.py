"""
llm_minesweeper_controller - UI 组件
"""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QGroupBox, QSplitter,
)
from PyQt5.QtCore import pyqtSignal, Qt


class LlmMinesweeperControllerWidget(QWidget):
    """插件 UI"""

    _log_signal = pyqtSignal(str)
    _chat_signal = pyqtSignal(str, str)  # role, text
    _status_signal = pyqtSignal(str)
    _enable_buttons_signal = pyqtSignal(bool)
    _summary_signal = pyqtSignal(str)
    _stop_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # 状态显示
        status_group = QGroupBox("状态")
        status_layout = QHBoxLayout()
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self._status_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # 上下文摘要 + 对话区（水平布局）
        main_splitter = QSplitter(Qt.Horizontal)

        # 上下文摘要（左侧）
        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        self._summary_text.setMaximumWidth(280)
        self._summary_text.setMinimumWidth(200)
        self._summary_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 11px;
                color: #0078d4;
                background-color: #f0f6ff;
            }
        """)

        # 对话显示区（右侧，宽）
        self._chat_text = QTextEdit()
        self._chat_text.setReadOnly(True)
        self._chat_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            }
        """)

        main_splitter.addWidget(self._summary_text)
        main_splitter.addWidget(self._chat_text)
        main_splitter.setStretchFactor(0, 0)  # 摘要不拉伸
        main_splitter.setStretchFactor(1, 1)  # 对话拉伸

        layout.addWidget(main_splitter, stretch=1)

        # 日志显示区
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout()
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(80)
        self._log_text.setStyleSheet("font-size: 11px; color: #666;")
        log_layout.addWidget(self._log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 控制按钮
        button_layout = QHBoxLayout()
        self._analyze_button = QPushButton("🤖 分析并操作")
        self._analyze_button.setStyleSheet("padding: 6px; font-size: 14px;")
        self._stop_button = QPushButton("⏹ 停止")
        self._stop_button.setStyleSheet("padding: 6px; font-size: 14px;")
        self._stop_button.setEnabled(False)  # 默认禁用，有任务时才启用
        self._test_button = QPushButton("🔗 测试连接")
        self._clear_chat_button = QPushButton("🗑 清除对话")
        self._clear_log_button = QPushButton("🗑 清除日志")
        button_layout.addWidget(self._analyze_button)
        button_layout.addWidget(self._stop_button)
        button_layout.addWidget(self._test_button)
        button_layout.addWidget(self._clear_chat_button)
        button_layout.addWidget(self._clear_log_button)
        layout.addLayout(button_layout)

        # 信号连接
        self._log_signal.connect(self._on_log)
        self._chat_signal.connect(self._on_chat)
        self._status_signal.connect(self._on_status)
        self._enable_buttons_signal.connect(self._on_enable_buttons)
        self._summary_signal.connect(self._on_summary)
        self._stop_signal.connect(self._on_stop_clicked)

        # 按钮事件
        self._clear_log_button.clicked.connect(self._clear_log)
        self._clear_chat_button.clicked.connect(self._clear_chat)

    def _on_log(self, text: str) -> None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_text.append(f"[{timestamp}] {text}")

    def _on_chat(self, role: str, text: str) -> None:
        color_map = {
            "system": "#2196F3",
            "assistant": "#4CAF50",
            "tool": "#FF9800",
            "user": "#9C27B0",
            "error": "#F44336",
        }
        color = color_map.get(role, "#333")
        self._chat_text.append(
            f'<span style="color:{color}; font-weight:bold;">[{role}]</span> '
            f'{text}'
        )
        # 滚动到底部
        scrollbar = self._chat_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def _on_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _on_enable_buttons(self, enabled: bool) -> None:
        self._analyze_button.setEnabled(enabled)
        self._test_button.setEnabled(enabled)
        self._stop_button.setEnabled(not enabled)  # 停止按钮与主按钮相反

    def _on_stop_clicked(self) -> None:
        """停止按钮点击处理"""
        self._stop_signal.emit()

    def _clear_log(self) -> None:
        self._log_text.clear()

    def _clear_chat(self) -> None:
        self._chat_text.clear()

    def _on_summary(self, text: str) -> None:
        """更新上下文摘要显示"""
        self._summary_text.setPlainText(text)
        # 滚动到顶部
        self._summary_text.moveCursor(self._summary_text.textCursor().Start)

    # ── 线程安全的公开方法（由插件调用） ──

    def log_message(self, text: str) -> None:
        self._log_signal.emit(text)

    def add_chat_message(self, role: str, text: str) -> None:
        self._chat_signal.emit(role, text)

    def update_status(self, text: str) -> None:
        self._status_signal.emit(text)

    def set_buttons_enabled(self, enabled: bool) -> None:
        self._enable_buttons_signal.emit(enabled)

    def update_summary(self, text: str) -> None:
        self._summary_signal.emit(text)

    def set_analyze_callback(self, callback) -> None:
        self._analyze_button.clicked.connect(callback)

    def set_test_button_callback(self, callback) -> None:
        self._test_button.clicked.connect(callback)

    def set_stop_button_callback(self, callback) -> None:
        self._stop_button.clicked.connect(callback)
