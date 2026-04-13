"""
历史记录数据模型
"""

from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any

from PyQt5.QtCore import QCoreApplication

_translate = QCoreApplication.translate


class LogicSymbol:
    """逻辑连接符（与/或）"""

    And = 0
    Or = 1

    _LABELS = {0: _translate("Form", "与"), 1: _translate("Form", "或")}
    _SQL = {0: "and", 1: "or"}

    @classmethod
    def display_names(cls):
        return [cls._LABELS[cls.And], cls._LABELS[cls.Or]]

    @classmethod
    def from_display_name(cls, name: str):
        for v, n in cls._LABELS.items():
            if n == name:
                return cls(v)
        raise ValueError(name)

    def __init__(self, value: int):
        self.value = value

    @property
    def display_name(self):
        return self._LABELS[self.value]

    @property
    def to_sql(self):
        return self._SQL[self.value]


class CompareSymbol:
    """比较符号"""

    Equal = 0
    NotEqual = 1
    GreaterThan = 2
    LessThan = 3
    GreaterThanOrEqual = 4
    LessThanOrEqual = 5
    Contains = 6
    NotContains = 7

    _LABELS = {
        0: _translate("Form", "等于"),
        1: _translate("Form", "不等于"),
        2: _translate("Form", "大于"),
        3: _translate("Form", "小于"),
        4: _translate("Form", "大于等于"),
        5: _translate("Form", "小于等于"),
        6: _translate("Form", "包含"),
        7: _translate("Form", "不包含"),
    }
    _SQL = {
        0: "=",
        1: "!=",
        2: ">",
        3: "<",
        4: ">=",
        5: "<=",
        6: "in",
        7: "not in",
    }

    @classmethod
    def display_names(cls):
        return [cls._LABELS[i] for i in range(len(cls._LABELS))]

    @classmethod
    def from_display_name(cls, name: str):
        for v, n in cls._LABELS.items():
            if n == name:
                return cls(v)
        raise ValueError(name)

    def __init__(self, value: int):
        self.value = value

    @property
    def display_name(self):
        return self._LABELS[self.value]

    @property
    def to_sql(self):
        return self._SQL[self.value]


class HistoryData:
    """历史记录数据行（纯数据类，用类属性定义字段）"""

    replay_id: int = 0
    game_board_state: int = 0
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
    etime: float = 0
    start_time: int = 0
    end_time: int = 0
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
    pluck: float = 0.0

    @classmethod
    def get_field_value(cls, field_name: str):
        for name, value in inspect.getmembers(cls):
            if (
                not name.startswith("__")
                and not callable(value)
                and not name.startswith("_")
                and name == field_name
            ):
                return value

    @classmethod
    def fields(cls):
        return [
            name
            for name, value in inspect.getmembers(cls)
            if not name.startswith("__")
            and not callable(value)
            and not name.startswith("_")
        ]

    @classmethod
    def query_all(cls):
        return f"select {','.join(cls.fields())} from history"

    @classmethod
    def from_dict(cls, data: dict):
        instance = cls()
        for name, value in inspect.getmembers(cls):
            if (
                not name.startswith("__")
                and not callable(value)
                and not name.startswith("_")
            ):
                new_value = data.get(name)
                # 时间戳字段转换
                if (
                    name in ("etime",)
                    and isinstance(new_value, (int, float))
                    and new_value
                ):
                    value = new_value
                elif (
                    name in ("start_time", "end_time")
                    and isinstance(new_value, (int, float))
                    and new_value
                ):
                    value = datetime.fromtimestamp(new_value / 1_000_000)
                elif isinstance(value, float):
                    value = round(new_value, 4)
                else:
                    value = new_value
                setattr(instance, name, value)
        return instance
