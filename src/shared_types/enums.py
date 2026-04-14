"""
共享枚举类型

定义游戏状态、鼠标状态、游戏模式、游戏难度等枚举。
这些枚举遵循 evf 标准（ms_toollib 也遵循此标准）。

参考：https://github.com/eee555/ms-toollib/blob/main/evf%E6%A0%87%E5%87%86.md
"""
from __future__ import annotations

from enum import Enum

from PyQt5.QtCore import QCoreApplication

_translate = QCoreApplication.translate


class BaseDiaPlayEnum(Enum):
    """带显示名称的枚举基类"""

    @property
    def display_name(self) -> str:
        return self.name

    @classmethod
    def from_display_name(cls, display_name: str) -> "BaseDiaPlayEnum":
        for member in cls:
            if member.display_name == display_name:
                return member
        raise ValueError(f"Invalid display name: {display_name}")

    @classmethod
    def display_names(cls) -> list[str]:
        return [member.display_name for member in cls]

    @classmethod
    def try_create(cls, value: int) -> "BaseDiaPlayEnum | int":
        """尝试创建枚举，如果值不在定义中则返回原始值"""
        try:
            return cls(value)
        except ValueError:
            return value


class GameBoardState(BaseDiaPlayEnum):
    """
    游戏板状态枚举

    这些魔数遵循 ms_toollib 标准。
    """
    Ready = 1
    Playing = 2
    Win = 3
    Loss = 4
    PreFlaging = 5
    Display = 6

    @property
    def display_name(self) -> str:
        match self:
            case GameBoardState.Win:
                return _translate("Form", "胜利")
            case GameBoardState.Loss:
                return _translate("Form", "失败")
            case GameBoardState.Ready:
                return _translate("Form", "准备")
            case GameBoardState.Playing:
                return _translate("Form", "进行中")
            case GameBoardState.PreFlaging:
                return _translate("Form", "预标记")
            case GameBoardState.Display:
                return _translate("Form", "回放")
            case _:
                return str(self.value)


class MouseState(BaseDiaPlayEnum):
    """
    鼠标状态枚举

    游戏过程中，鼠标的动作会触发鼠标事件，并在 evf 录像中记录为
    诸如 "mv", "lc", "lr", "rc", "rr", "mc", "mr", "pf", "cc", "l", "r", "m"
    动作导致鼠标转移至不同的状态，用于计算左键、右键、双击等次数，显示局面高亮等。

    这些魔数遵循 ms_toollib 标准。
    """
    UpUp = 1
    UpDown = 2
    UpDownNotFlag = 3
    DownUp = 4
    Chording = 5
    ChordingNotFlag = 6
    DownUpAfterChording = 7
    Undefined = 8

    @property
    def display_name(self) -> str:
        match self:
            case MouseState.UpUp:
                return _translate("Form", "双键抬起")
            case MouseState.UpDown:
                return _translate("Form", "右键按下且标过雷")
            case MouseState.UpDownNotFlag:
                return _translate("Form", "右键按下且没有标过雷")
            case MouseState.DownUp:
                return _translate("Form", "左键按下")
            case MouseState.Chording:
                return _translate("Form", "双键按下")
            case MouseState.ChordingNotFlag:
                return _translate("Form", "双键按下且先按下右键且没有标雷")
            case MouseState.DownUpAfterChording:
                return _translate("Form", "双击后先弹起右键左键还没有弹起")
            case MouseState.Undefined:
                return _translate("Form", "未初始化")
            case _:
                return str(self.value)


class GameMode(BaseDiaPlayEnum):
    """
    游戏模式枚举

    这些魔数遵循 evf 标准（ms_toollib 也是遵循 evf 标准）。
    """
    Standard = 0
    Win7 = 4
    ClassicNoGuess = 5
    StrictNoGuess = 6
    WeakNoGuess = 7
    BlessingMode = 8
    GuessableNoGuess = 9
    LuckyMode = 10

    @property
    def display_name(self) -> str:
        match self:
            case GameMode.Standard:
                return _translate("Form", "标准")
            case GameMode.Win7:
                return _translate("Form", "win7")
            case GameMode.ClassicNoGuess:
                return _translate("Form", "经典无猜")
            case GameMode.StrictNoGuess:
                return _translate("Form", "强无猜")
            case GameMode.WeakNoGuess:
                return _translate("Form", "弱无猜")
            case GameMode.BlessingMode:
                return _translate("Form", "准无猜")
            case GameMode.GuessableNoGuess:
                return _translate("Form", "强可猜")
            case GameMode.LuckyMode:
                return _translate("Form", "弱可猜")
            case _:
                return str(self.value)


class GameLevel(BaseDiaPlayEnum):
    """
    游戏难度枚举

    这些魔数遵循 evf 标准（ms_toollib 也是遵循 evf 标准）。
    """
    BEGINNER = 3
    INTERMEDIATE = 4
    EXPERT = 5
    CUSTOM = 6

    @property
    def display_name(self) -> str:
        match self:
            case GameLevel.BEGINNER:
                return _translate("Form", "初级")
            case GameLevel.INTERMEDIATE:
                return _translate("Form", "中级")
            case GameLevel.EXPERT:
                return _translate("Form", "高级")
            case GameLevel.CUSTOM:
                return _translate("Form", "自定义")
            case _:
                return str(self.value)
