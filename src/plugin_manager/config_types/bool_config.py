"""
布尔配置类型 → QCheckBox
"""

from __future__ import annotations

from typing import Any, Callable

from PyQt5.QtWidgets import QCheckBox

from .base_config import BaseConfig


class BoolConfig(BaseConfig[bool]):
    """
    布尔配置 → QCheckBox

    用法::

        auto_save = BoolConfig(True, "自动保存", description="录制完成自动保存")
    """

    widget_type = "checkbox"

    def __post_init__(self) -> None:
        """确保默认值是布尔类型"""
        self.default = bool(self.default)

    def create_widget(self) -> tuple[QCheckBox, Callable[[], bool], Callable[[bool], None]]:
        """创建 QCheckBox 控件"""
        widget = QCheckBox()
        widget.setChecked(self.default)
        if self.description:
            widget.setToolTip(self.description)
        return widget, widget.isChecked, widget.setChecked

    def to_storage(self, value: bool) -> bool:
        """转换为存储格式"""
        return bool(value)

    def from_storage(self, data: Any) -> bool:
        """从存储格式恢复"""
        return bool(data)
