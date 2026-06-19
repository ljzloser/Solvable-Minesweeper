"""
修仙升级数据模型
"""

from __future__ import annotations

from PyQt5.QtCore import QCoreApplication
_translate = QCoreApplication.translate


# ═══════════════════════════════════════════════════════════════
# 仙逆修仙等级名称表（0-100级）
# ═══════════════════════════════════════════════════════════════
LEVEL_NAMES: dict[int, str] = {
    0: _translate("Form", "凡人"),
    1: _translate("Form", "凝气一层"),
    2: _translate("Form", "凝气二层"),
    3: _translate("Form", "凝气三层"),
    4: _translate("Form", "凝气四层"),
    5: _translate("Form", "凝气五层"),
    6: _translate("Form", "凝气六层"),
    7: _translate("Form", "凝气七层"),
    8: _translate("Form", "凝气八层"),
    9: _translate("Form", "凝气九层"),
    10: _translate("Form", "凝气十层"),
    11: _translate("Form", "凝气十一层"),
    12: _translate("Form", "凝气十二层"),
    13: _translate("Form", "凝气十三层"),
    14: _translate("Form", "凝气十四层"),
    15: _translate("Form", "凝气十五层"),
    16: _translate("Form", "筑基初期"),
    17: _translate("Form", "筑基中期"),
    18: _translate("Form", "筑基后期"),
    19: _translate("Form", "筑基大圆满"),
    20: _translate("Form", "结丹初期"),
    21: _translate("Form", "结丹中期"),
    22: _translate("Form", "结丹后期"),
    23: _translate("Form", "结丹大圆满"),
    24: _translate("Form", "元婴初期"),
    25: _translate("Form", "元婴中期"),
    26: _translate("Form", "元婴后期"),
    27: _translate("Form", "元婴大圆满"),
    28: _translate("Form", "化神初期"),
    29: _translate("Form", "化神中期"),
    30: _translate("Form", "化神后期"),
    31: _translate("Form", "化神大圆满"),
    32: _translate("Form", "婴变初期"),
    33: _translate("Form", "婴变中期"),
    34: _translate("Form", "婴变后期"),
    35: _translate("Form", "婴变大圆满"),
    36: _translate("Form", "问鼎初期"),
    37: _translate("Form", "问鼎中期"),
    38: _translate("Form", "问鼎后期"),
    39: _translate("Form", "问鼎大圆满"),
    40: _translate("Form", "阴虚"),
    41: _translate("Form", "阳实"),
    42: _translate("Form", "窥涅初期"),
    43: _translate("Form", "窥涅中期"),
    44: _translate("Form", "窥涅后期"),
    45: _translate("Form", "窥涅大圆满"),
    46: _translate("Form", "净涅初期"),
    47: _translate("Form", "净涅中期"),
    48: _translate("Form", "净涅后期"),
    49: _translate("Form", "净涅大圆满"),
    50: _translate("Form", "碎涅初期"),
    51: _translate("Form", "碎涅中期"),
    52: _translate("Form", "碎涅后期"),
    53: _translate("Form", "碎涅大圆满"),
    54: _translate("Form", "天人一衰"),
    55: _translate("Form", "天人二衰"),
    56: _translate("Form", "天人三衰"),
    57: _translate("Form", "天人四衰"),
    58: _translate("Form", "天人五衰"),
    59: _translate("Form", "空涅初期"),
    60: _translate("Form", "空涅中期"),
    61: _translate("Form", "空涅后期"),
    62: _translate("Form", "空涅大圆满"),
    63: _translate("Form", "空灵初期"),
    64: _translate("Form", "空灵中期"),
    65: _translate("Form", "空灵后期"),
    66: _translate("Form", "空灵大圆满"),
    67: _translate("Form", "空玄初期"),
    68: _translate("Form", "空玄中期"),
    69: _translate("Form", "空玄后期"),
    70: _translate("Form", "空玄大圆满"),
    71: _translate("Form", "空玄一劫"),
    72: _translate("Form", "空玄二劫"),
    73: _translate("Form", "空玄三劫"),
    74: _translate("Form", "空玄四劫"),
    75: _translate("Form", "空玄五劫"),
    76: _translate("Form", "空玄六劫"),
    77: _translate("Form", "空玄七劫"),
    78: _translate("Form", "空玄八劫"),
    79: _translate("Form", "空玄九劫"),
    80: _translate("Form", "空劫初期"),
    81: _translate("Form", "空劫中期"),
    82: _translate("Form", "空劫后期"),
    83: _translate("Form", "空劫大圆满"),
    84: _translate("Form", "大尊"),
    85: _translate("Form", "金尊"),
    86: _translate("Form", "天尊"),
    87: _translate("Form", "跃天尊"),
    88: _translate("Form", "大天尊"),
    89: _translate("Form", "踏天一桥"),
    90: _translate("Form", "踏天二桥"),
    91: _translate("Form", "踏天三桥"),
    92: _translate("Form", "踏天四桥"),
    93: _translate("Form", "踏天五桥"),
    94: _translate("Form", "踏天六桥"),
    95: _translate("Form", "踏天七桥"),
    96: _translate("Form", "踏天八桥"),
    97: _translate("Form", "踏天九桥"),
    98: _translate("Form", "踏天境"),
    99: _translate("Form", "厚土境"),
    100: _translate("Form", "煌天境"),
}


# 游戏难度映射
LEVEL_LABELS: dict[int, str] = {
    3: _translate("Form", "初级"),
    4: _translate("Form", "中级"),
    5: _translate("Form", "高级"),
    6: _translate("Form", "自定义"),
}


# 游戏模式映射
MODE_LABELS: dict[int, str] = {
    0: _translate("Form", "标准"),
    4: _translate("Form", "Win7"),
    5: _translate("Form", "经典无猜"),
    6: _translate("Form", "强无猜"),
    7: _translate("Form", "弱无猜"),
    8: _translate("Form", "准无猜"),
    9: _translate("Form", "强可猜"),
    10: _translate("Form", "弱可猜"),
}


# 仙躯形象：仅大境界突破换图，量变不换（共18张：1.png~18.png）
# 每个 tuple 为 (该大境界起始等级, 图片索引)
REALM_IMAGE: list[tuple[int, int]] = [
    (0,  1),   # 凡人
    (1,  1),   # 凝气
    (16, 2),   # 筑基
    (20, 3),   # 结丹
    (24, 4),   # 元婴
    (28, 5),   # 化神
    (32, 6),   # 婴变
    (36, 7),   # 问鼎
    (40, 8),   # 阴虚阳实
    (42, 9),   # 窥涅
    (46, 10),  # 净涅
    (50, 11),  # 碎涅
    (54, 12),  # 天人五衰
    (59, 13),  # 空涅
    (63, 14),  # 空灵
    (67, 15),  # 空玄（含空玄九劫）
    (80, 16),  # 空劫
    (84, 17),  # 大尊~大天尊
    (89, 18),  # 踏天~煌天境
]


def get_image_index(level: int) -> int:
    for start, idx in reversed(REALM_IMAGE):
        if level >= start:
            return idx
    return 1
