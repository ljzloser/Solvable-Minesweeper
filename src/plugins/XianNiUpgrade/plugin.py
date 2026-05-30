"""
XianNiUpgrade - 修仙升级插件主体

每局扫雷胜利后获得经验，从凡人修炼到一招摧毁108颗修正星的绝世强者，共100级。
"""
from __future__ import annotations

import math
import json
import base64
from datetime import datetime

from PyQt5.QtWidgets import QWidget

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from plugin_sdk import BasePlugin, PluginInfo, make_plugin_icon, WindowMode
from shared_types.events import CloseEvent, GameFinishedEvent

from .widgets import XianNiUpgradeUI
from .models import LEVEL_NAMES, LEVEL_LABELS, MODE_LABELS, get_image_index


# AES-GCM 加密密钥（明文写死，只防无编程知识的人）
_ENCRYPT_KEY = b"f[{gr!%$%^65sr60"


def _encrypt(data: bytes) -> bytes:
    nonce = get_random_bytes(12)
    cipher = AES.new(_ENCRYPT_KEY, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return base64.b64encode(nonce + tag + ciphertext)


def _decrypt(data: bytes) -> bytes:
    raw = base64.b64decode(data)
    nonce = raw[:12]
    tag = raw[12:28]
    ciphertext = raw[28:]
    cipher = AES.new(_ENCRYPT_KEY, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)


def _total_xp(level: int) -> int:
    """升到第 level 级所需的累计总经验"""
    return math.floor(
        0.025 * level ** 4.29637
        + 11.37 * level ** 2.13
        + 88.605 * level ** 0.885
    )


class XianNiUpgradePlugin(BasePlugin):
    """修仙升级插件"""

    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="xian_ni_upgrade",
            version="1.0.0",
            author="eee555",
            description="仙逆背景的修炼体系 - 每局扫雷胜利获得经验，从凡人修炼到一招摧毁108颗修正星的绝世强者",
            icon=make_plugin_icon("#8E24AA", "仙", 64),
            window_mode=WindowMode.TAB,
        )

    def _setup_subscriptions(self) -> None:
        self.subscribe(GameFinishedEvent, self._on_game_finished)
        self.subscribe(CloseEvent, self._on_close)

    def _create_widget(self) -> QWidget:
        self._ui = XianNiUpgradeUI()
        self._ui.set_image_dir(self.data_dir / "asserts")
        return self._ui

    def on_initialized(self) -> None:
        self._load_data()
        self._push_ui_update()

    def on_shutdown(self) -> None:
        self._save_data()

    # ═══════════════════════════════════════════════════════════
    # 【TODO】每局经验计算公式
    # ═══════════════════════════════════════════════════════════

    def _calc_xp(self, event: GameFinishedEvent) -> int:
        """每局获得的经验值"""
        return 80

    # ═══════════════════════════════════════════════════════════
    # 数据管理
    # ═══════════════════════════════════════════════════════════

    def _load_data(self):
        path = self.data_dir / "player_data.dat"
        if path.exists():
            try:
                raw = _decrypt(path.read_bytes())
                self._player_data = json.loads(raw)
                self.logger.info(f"已加载存档: Lv.{self._player_data['level']}")
                return
            except Exception as e:
                self.logger.warning(f"读取存档失败: {e}")

        self._player_data = {
            "level": 0,
            "xp": 0,
            "history": [],
        }

    def _save_data(self):
        path = self.data_dir / "player_data.dat"
        try:
            raw = json.dumps(self._player_data, ensure_ascii=False).encode("utf-8")
            path.write_bytes(_encrypt(raw))
        except Exception as e:
            self.logger.error(f"保存存档失败: {e}")

    def _on_game_finished(self, event: GameFinishedEvent):
        if event.game_state != 6:
            return

        xp_gained = self._calc_xp(event)
        self._player_data["xp"] += xp_gained

        while self._player_data["level"] < 100:
            need = _total_xp(self._player_data["level"] + 1)
            if self._player_data["xp"] < need:
                break
            self._player_data["level"] += 1

        # 封顶
        top = _total_xp(100)
        if self._player_data["xp"] > top:
            self._player_data["xp"] = top

        self._player_data["history"].append({
            "time": int(datetime.now().timestamp()),
            "level": LEVEL_LABELS.get(event.level, str(event.level)),
            "mode": MODE_LABELS.get(event.mode, str(event.mode)),
            "rtime": round(event.rtime, 2),
            "bbbv": event.bbbv,
            "xp": xp_gained,
        })

        if len(self._player_data["history"]) > 1000:
            self._player_data["history"] = self._player_data["history"][-1000:]

        self._save_data()
        self._push_ui_update()

    def _on_close(self, event: CloseEvent):
        self._save_data()

    def _push_ui_update(self):
        level = self._player_data["level"]
        xp = self._player_data["xp"]
        xp_next = _total_xp(level + 1) if level < 100 else _total_xp(100)

        data = {
            "level": level,
            "xp": xp,
            "xp_next": xp_next,
            "rank": LEVEL_NAMES.get(level, ""),
            "image_index": get_image_index(level),
            "history": self._player_data["history"][::-1][:100],
        }
        self._ui._signal_update.emit(data)
