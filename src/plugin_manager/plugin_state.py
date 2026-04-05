"""
插件状态持久化

将每个插件的 UI 状态保存到 JSON 文件，包括：
- 是否启用
- 初始化时是否加载窗口
- 加载到标签页 / 独立窗口 / 不加载
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import loguru
from .plugin_base import WindowMode, LogLevel

logger = loguru.logger.bind(name="PluginState")


@dataclass
class PluginState:
    """单个插件的持久化状态"""
    enabled: bool = True          # 是否启用
    show_window: bool = True      # 是否在初始化时显示窗口
    window_mode: WindowMode = WindowMode.TAB  # 窗口加载方式
    log_level: LogLevel = LogLevel.DEBUG  # 日志级别


# 默认状态，插件第一次出现时使用
_DEFAULT = PluginState()


class PluginStateManager:
    """管理所有插件状态的读写"""

    def __init__(self, file_path: str | Path):
        self._file = Path(file_path)
        self._states: dict[str, PluginState] = {}
        self._dirty = False

    # ── 读写 ────────────────────────────────────────────

    def load(self) -> None:
        """从 JSON 文件加载状态"""
        if not self._file.exists():
            logger.info("State file not found: %s (will create on save)", self._file)
            return
        try:
            raw: dict[str, dict[str, Any]] = json.loads(self._file.read_text("utf-8"))
            for name, d in raw.items():
                self._states[name] = PluginState(**{k: v for k, v in d.items() if k in asdict(_DEFAULT)})
            logger.info("Loaded state for %d plugin(s)", len(self._states))
        except Exception as e:
            logger.error("Failed to load state from %s: %s", self._file, e)

    def save(self) -> None:
        """写入 JSON 文件（仅在有变更时）"""
        if not self._dirty:
            return
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            raw = {name: asdict(st) for name, st in self._states.items()}
            self._file.write_text(
                json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self._dirty = False
            logger.info("Saved state for %d plugin(s)", len(self._states))
        except Exception as e:
            logger.error("Failed to save state to %s: %s", self._file, e)

    # ── 查询 / 修改 ─────────────────────────────────────

    def get(self, name: str) -> PluginState:
        """获取某个插件的状态（不存在则返回系统默认值）"""
        return self._states.get(name, _DEFAULT)

    def get_effective(self, name: str, plugin_default: PluginState | None = None) -> PluginState:
        """
        获取有效状态（优先级链：JSON 覆盖 > 插件声明 > 系统默认）

        Args:
            name: 插件名
            plugin_default: 插件自身声明的默认值（来自 PluginInfo），为 None 时使用系统默认
        """
        if name in self._states:
            # JSON 中有记录 → 以 JSON 为准，缺失字段回退到插件/系统默认
            saved = self._states[name]
            fallback = plugin_default or _DEFAULT
            return PluginState(
                enabled=saved.enabled if saved.enabled != _DEFAULT.enabled else fallback.enabled,
                show_window=saved.show_window if saved.show_window != _DEFAULT.show_window else fallback.show_window,
                window_mode=saved.window_mode if saved.window_mode != _DEFAULT.window_mode else fallback.window_mode,
                log_level=saved.log_level if saved.log_level != _DEFAULT.log_level else fallback.log_level,
            )
        # 无 JSON 记录 → 使用插件声明或系统默认
        return (plugin_default or _DEFAULT)

    def set(self, name: str, state: PluginState) -> None:
        """更新某个插件的状态（标记为脏）"""
        self._states[name] = state
        self._dirty = True

    def remove(self, name: str) -> None:
        """移除某条记录"""
        if name in self._states:
            del self._states[name]
            self._dirty = True

    @property
    def all_states(self) -> dict[str, PluginState]:
        return dict(self._states)
