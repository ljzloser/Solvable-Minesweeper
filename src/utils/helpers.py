import os
import sys

from PyQt5.QtCore import QCoreApplication

def trans_expression(expression: str):
    expression = expression.lower().strip()[:10000]
    expression = expression.replace("3bv", "bbbv")
    expression = expression.replace("opening", "op")
    expression = expression.replace("click", "cl")
    # expression = expression.replace("\"", "'")
    expression = expression.replace("island", "isl")
    expression = expression.replace("chording", "double")
    expression = expression.replace("solved_bbbv", "bbbv_solved")
    expression = expression.replace("mine_num", "minenum")
    expression = expression.replace("width", "column")
    expression = expression.replace("height", "row")
    return expression


def trans_game_mode(mode: int) -> str:
    _translate = QCoreApplication.translate
    if mode == 0:
        return _translate("Form", "\u6807\u51c6")
    elif mode == 1:
        return 'upk'
    elif mode == 2:
        return 'cheat'
    elif mode == 3:
        return 'Density'
    elif mode == 4:
        return 'win7'
    elif mode == 5:
        return _translate("Form", '\u7ecf\u5178\u65e0\u731c')
    elif mode == 6:
        return _translate("Form", '\u5f3a\u65e0\u731c')
    elif mode == 7:
        return _translate("Form", '\u5f31\u65e0\u731c')
    elif mode == 8:
        return _translate("Form", '\u51c6\u65e0\u731c')
    elif mode == 9:
        return _translate("Form", '\u5f3a\u53ef\u731c')
    elif mode == 10:
        return _translate("Form", '\u5f31\u53ef\u731c')
