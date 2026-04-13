"""
文本配置类型 → QLineEdit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt5.QtWidgets import QLineEdit

from .base_config import BaseConfig, ConfigWidgetWrapper


@dataclass
class TextConfig(BaseConfig[str]):
    """
    文本配置 → QLineEdit

    Args:
        default: 默认值
        label: 显示标签
        placeholder: 占位符文本
        password: 是否为密码输入（显示为 ***）
        description: tooltip 提示

    用法::

        api_key = TextConfig("", "API密钥", password=True, placeholder="输入密钥...")
        name = TextConfig("", "名称", placeholder="请输入名称")
    """

    placeholder: str = ""
    password: bool = False

    widget_type = "textedit"

    def __post_init__(self) -> None:
        """确保默认值是字符串类型"""
        self.default = str(self.default)

    def create_widget(self) -> ConfigWidgetWrapper:
        """创建 QLineEdit 控件"""
        widget = QLineEdit()
        widget.setText(str(self.default))

        if self.placeholder:
            widget.setPlaceholderText(self.placeholder)

        if self.password:
            widget.setEchoMode(QLineEdit.Password)

        if self.description:
            widget.setToolTip(self.description)

        return ConfigWidgetWrapper(widget, widget.text, widget.setText, widget.textChanged)

    def to_storage(self, value: str) -> str:
        """转换为存储格式"""
        return str(value)

    def from_storage(self, data: Any) -> str:
        """从存储格式恢复"""
        return str(data) if data is not None else self.default
