from __future__ import annotations

from plugins.XianNiUpgrade.plugin import XianNiUpgradePlugin


def test_non_standard_modes_can_gain_base_xp():
    plugin = XianNiUpgradePlugin.__new__(XianNiUpgradePlugin)

    xp = plugin._calc_xp_base(
        mode=8,
        level=3,
        row=8,
        column=8,
        mine_num=10,
        rtime=30.0,
        bbbv=20,
        cell1=0,
        cell2=0,
        cell3=0,
        cell4=0,
        cell5=0,
        cell6=0,
        cell7=0,
        cell8=0,
        op=0,
        isl=0,
        ioe=0.95,
        nf=True,
    )

    assert xp > 0
