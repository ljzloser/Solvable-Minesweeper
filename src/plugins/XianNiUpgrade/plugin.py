"""
XianNiUpgrade - 修仙升级插件主体

每局扫雷胜利后获得经验，从凡人修炼到一招摧毁108颗修正星的绝世强者，共100级。
"""
from __future__ import annotations

import math
import json
import base64
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import QWidget, QMessageBox

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

import ms_toollib as ms

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
        self._ui.set_absorb_callbacks(self.validate_replays, self.absorb_replays)
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
        return 8000

    def _calc_xp2(self, video: ms.EvfVideo) -> int:
        """通过录像计算经验值"""
        return 1

    # ═══════════════════════════════════════════════════════════
    # 数据管理
    # ═══════════════════════════════════════════════════════════

    def _load_data(self):
        path = self.data_dir / "player_data.dat"
        if path.exists():
            try:
                raw = _decrypt(path.read_bytes())
                data = json.loads(raw)
                if "identifiers" in data and "players" in data:
                    self._identifiers = data["identifiers"]
                    self._players = data["players"]
                    self._history = data.get("history", [])
                    self._current_pid = data.get("current_pid", 0)
                    self._imported = set(tuple(v) for v in data.get("imported_videos", []))
                    self.logger.info(f"已加载存档，{len(self._identifiers)} 个玩家")
                    return
                self.logger.info("旧存档格式，忽略")
            except Exception as e:
                self.logger.warning(f"读取存档失败: {e}")

        self._identifiers = []
        self._players = []
        self._history = []
        self._current_pid = 0
        self._imported: set[tuple[str, str]] = set()

    def _save_data(self):
        path = self.data_dir / "player_data.dat"
        data = {
            "identifiers": self._identifiers,
            "players": self._players,
            "history": self._history,
            "current_pid": self._current_pid,
            "imported_videos": [list(v) for v in self._imported],
        }
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        path.write_bytes(_encrypt(raw))

    def _get_or_create_pid(self, identifier: str) -> int:
        identifier = identifier.strip()
        if not identifier:
            identifier = "匿名玩家"
        try:
            return self._identifiers.index(identifier)
        except ValueError:
            pid = len(self._identifiers)
            self._identifiers.append(identifier)
            self._players.append({"level": 0, "xp": 0})
            return pid

    # ═══════════════════════════════════════════════════════════
    # 吸收灵气（导入其他版本录像获得经验）
    # ═══════════════════════════════════════════════════════════

    def validate_replays(self, exe_path: str, replay_path: str) -> dict | None:
        """校验录像并返回预览数据，失败返回 None"""
        try:
            exe = Path(exe_path)
            if not exe.exists():
                self.logger.error(f"校验程序不存在: {exe_path}")
                return None

            actual_md5 = hashlib.md5(exe.read_bytes()).hexdigest()

            match actual_md5:
                case "d5fd61ae1372297aa7008d7b7cd8a13b":
                    return self._validate_metasweeper322(exe, replay_path)
                case _:
                    self.logger.error(f"未知法器 MD5: {actual_md5}")
                    return None
        except Exception as e:
            self.logger.error(f"校验失败: {e}")
            return None

    def _validate_metasweeper322(self, exe: Path, replay_path: str) -> dict | None:
        """元扫雷 3.2.2 的录像校验与解析"""
        try:
            cmd = [str(exe), "-c", replay_path]
            self.logger.info(f"执行: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                self.logger.error(f"校验程序返回非零: {result.returncode}")
                return None

            out_path = exe.parent / "_internal" / "out.json"
            if not out_path.exists():
                self.logger.error(f"未找到结果文件: {out_path}")
                return None

            report = json.loads(out_path.read_bytes())
            if report.get("error"):
                self.logger.error(f"校验报告错误: {report['error']}")
                return None

            new_files = []
            dup_files = []
            for d in report.get("data", []):
                if d.get("status") != 0:
                    continue
                fp = d["file"]
                try:
                    v = ms.EvfVideo(fp)
                    v.parse()
                    key = (str(v.start_time), v.player_identifier)
                    entry = {
                        "file": fp,
                        "player": v.player_identifier,
                        "start_time": v.start_time,
                        "level": getattr(v, "level", 3),
                        "mode": getattr(v, "mode", 0),
                        "rtime": getattr(v, "rtime", 0.0),
                        "bbbv": getattr(v, "bbbv", 0),
                        "xp": self._calc_xp2(v),
                    }
                    if key in self._imported:
                        dup_files.append(entry)
                    elif entry["xp"] > 0:
                        new_files.append(entry)
                except Exception as e:
                    self.logger.warning(f"解析录像失败 {fp}: {e}")

            return {
                "md5": "d5fd61ae1372297aa7008d7b7cd8a13b",
                "new_files": new_files,
                "duplicates": dup_files,
                "total_new_xp": sum(n["xp"] for n in new_files),
            }
        except Exception as e:
            self.logger.error(f"元扫雷 3.2.2 校验失败: {e}")
            return None

    def absorb_replays(self, preview: dict) -> int:
        """根据预览数据实际吸收经验，返回获得的总经验"""
        gained_total = 0

        for entry in preview["new_files"]:
            xp_per = entry.get("xp", 0)
            key = (str(entry["start_time"]), entry["player"])
            self._imported.add(key)

            pid = self._get_or_create_pid(entry["player"])
            self._current_pid = pid
            player = self._players[pid]
            player["xp"] += xp_per
            gained_total += xp_per

            while player["level"] < 100:
                need = _total_xp(player["level"] + 1)
                if player["xp"] < need:
                    break
                player["level"] += 1

            top = _total_xp(100)
            if player["xp"] > top:
                player["xp"] = top

            self._history.append({
                "pid": pid,
                "time": int(datetime.now().timestamp()),
                "level": entry["level"],
                "mode": entry["mode"],
                "rtime": round(entry["rtime"], 2),
                "bbbv": entry["bbbv"],
                "xp": xp_per,
            })

        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        self._save_data()
        self._push_ui_update()
        return gained_total

    def _build_update_data(self) -> dict:
        if not self._players:
            return {
                "player_name": "",
                "level": 0,
                "total_xp": 0,
                "xp_curr": 0,
                "xp_need": _total_xp(1),
                "rank": LEVEL_NAMES.get(0, ""),
                "image_index": get_image_index(0),
                "history": [],
            }
        pid = self._current_pid
        if pid >= len(self._players):
            pid = 0
            self._current_pid = 0
        player = self._players[pid]
        level = player["level"]
        xp = player["xp"]
        xp_base = _total_xp(level)
        xp_next = _total_xp(level + 1) if level < 100 else _total_xp(100)
        return {
            "player_name": self._identifiers[pid] if self._identifiers else "",
            "level": level,
            "total_xp": xp,
            "xp_curr": xp - xp_base,
            "xp_need": xp_next - xp_base,
            "rank": LEVEL_NAMES.get(level, ""),
            "image_index": get_image_index(level),
            "history": self._history[::-1][:100],
        }

    def _on_game_finished(self, event: GameFinishedEvent):
        if event.game_state != 6:
            return

        pid = self._get_or_create_pid(event.player_identifier)
        self._current_pid = pid
        player = self._players[pid]

        xp_gained = self._calc_xp(event)
        player["xp"] += xp_gained

        while player["level"] < 100:
            need = _total_xp(player["level"] + 1)
            if player["xp"] < need:
                break
            player["level"] += 1

        top = _total_xp(100)
        if player["xp"] > top:
            player["xp"] = top

        self._history.append({
            "pid": pid,
            "time": int(datetime.now().timestamp()),
            "level": event.level,
            "mode": event.mode,
            "rtime": round(event.rtime, 2),
            "bbbv": event.bbbv,
            "xp": xp_gained,
        })

        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        self._save_data()
        self._push_ui_update()

    def _on_close(self, event: CloseEvent):
        self._save_data()

    def _push_ui_update(self):
        self._ui._signal_update.emit(self._build_update_data())
