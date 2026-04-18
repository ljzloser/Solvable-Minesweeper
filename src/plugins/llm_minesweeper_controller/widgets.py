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

        # 对话显示区
        chat_group = QGroupBox("LLM对话")
        chat_layout = QVBoxLayout()
        self._chat_text = QTextEdit()
        self._chat_text.setReadOnly(True)
        self._chat_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Microsoft YaHei', monospace;
                font-size: 13px;
            }
        """)
        chat_layout.addWidget(self._chat_text)
        chat_group.setLayout(chat_layout)
        layout.addWidget(chat_group, stretch=1)

        # 日志显示区
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout()
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(120)
        self._log_text.setStyleSheet("font-size: 11px; color: #666;")
        log_layout.addWidget(self._log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 控制按钮
        button_layout = QHBoxLayout()
        self._analyze_button = QPushButton("🤖 分析并操作")
        self._analyze_button.setStyleSheet("padding: 6px; font-size: 14px;")
        self._test_button = QPushButton("🔗 测试连接")
        self._clear_chat_button = QPushButton("🗑 清除对话")
        self._clear_log_button = QPushButton("🗑 清除日志")
        button_layout.addWidget(self._analyze_button)
        button_layout.addWidget(self._test_button)
        button_layout.addWidget(self._clear_chat_button)
        button_layout.addWidget(self._clear_log_button)
        layout.addLayout(button_layout)

        # 信号连接
        self._log_signal.connect(self._on_log)
        self._chat_signal.connect(self._on_chat)
        self._status_signal.connect(self._on_status)
        self._enable_buttons_signal.connect(self._on_enable_buttons)

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
        scrollbar.setValue(scrollbar.maximum())

    def _on_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _on_enable_buttons(self, enabled: bool) -> None:
        self._analyze_button.setEnabled(enabled)
        self._test_button.setEnabled(enabled)

    def _clear_log(self) -> None:
        self._log_text.clear()

    def _clear_chat(self) -> None:
        self._chat_text.clear()

    # ── 线程安全的公开方法（由插件调用） ──

    def log_message(self, text: str) -> None:
        self._log_signal.emit(text)

    def add_chat_message(self, role: str, text: str) -> None:
        self._chat_signal.emit(role, text)

    def update_status(self, text: str) -> None:
        self._status_signal.emit(text)

    def set_buttons_enabled(self, enabled: bool) -> None:
        self._enable_buttons_signal.emit(enabled)

    def set_analyze_callback(self, callback) -> None:
        self._analyze_button.clicked.connect(callback)

    def set_test_button_callback(self, callback) -> None:
        self._test_button.clicked.connect(callback)
