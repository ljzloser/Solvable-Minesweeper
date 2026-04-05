"""
事件分发器

负责将事件分发给订阅了该事件的插件
支持优先级排序和异常隔离
"""
from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

import loguru

if TYPE_CHECKING:
    from .plugin_base import BasePlugin

logger = loguru.logger.bind(name="EventDispatcher")


@dataclass
class HandlerEntry:
    """事件处理函数条目"""
    handler: Callable[[Any], None]
    priority: int
    plugin: BasePlugin | None = None


class EventDispatcher:
    """
    事件分发器
    
    功能：
    - 管理事件订阅
    - 按优先级分发事件
    - 异常隔离（一个处理函数出错不影响其他）
    - 线程安全
    """
    
    def __init__(self):
        self._handlers: dict[str, list[HandlerEntry]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Any], None],
        priority: int = 100,
        plugin: BasePlugin | None = None,
    ) -> None:
        """
        订阅事件
        
        Args:
            event_type: 事件类型名称
            handler: 事件处理函数
            priority: 优先级（数值越小越先执行）
            plugin: 所属插件（用于取消订阅）
        """
        with self._lock:
            entry = HandlerEntry(
                handler=handler,
                priority=priority,
                plugin=plugin,
            )
            self._handlers[event_type].append(entry)
            # 按优先级排序
            self._handlers[event_type].sort(key=lambda e: e.priority)
            logger.debug(
                f"Subscribed to '{event_type}' with priority {priority}"
            )
    
    def unsubscribe(self, event_type: str, plugin: BasePlugin) -> None:
        """
        取消插件对某事件的所有订阅
        
        Args:
            event_type: 事件类型名称
            plugin: 要取消订阅的插件
        """
        with self._lock:
            handlers = self._handlers.get(event_type)
            if handlers:
                self._handlers[event_type] = [
                    entry for entry in handlers
                    if entry.plugin != plugin
                ]
                logger.debug(f"Unsubscribed plugin '{plugin.name}' from '{event_type}'")
    
    def unsubscribe_all(self, plugin: BasePlugin) -> None:
        """
        取消插件的所有事件订阅
        
        Args:
            plugin: 要取消订阅的插件
        """
        with self._lock:
            for event_type in list(self._handlers.keys()):
                self._handlers[event_type] = [
                    entry for entry in self._handlers[event_type]
                    if entry.plugin != plugin
                ]
    
    def dispatch(self, event_type: str, event: Any) -> None:
        """
        分发事件给所有订阅者
        
        Args:
            event_type: 事件类型名称
            event: 事件数据
        """
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))
        
        if not handlers:
            logger.debug(f"No handlers for event '{event_type}'")
            return
        
        logger.debug(
            f"Dispatching '{event_type}' to {len(handlers)} handler(s)"
        )
        
        for entry in handlers:
            # 检查插件是否启用
            if entry.plugin and not entry.plugin.is_enabled:
                continue
            
            try:
                entry.handler(event)
            except Exception as e:
                plugin_name = entry.plugin.name if entry.plugin else "unknown"
                logger.error(
                    f"Handler error in plugin '{plugin_name}' "
                    f"for event '{event_type}': {e}",
                    exc_info=True,
                )
    
    def dispatch_async(self, event_type: str, event: Any) -> None:
        """
        异步分发事件（在新线程中执行）
        
        Args:
            event_type: 事件类型名称
            event: 事件数据
        """
        thread = threading.Thread(
            target=self.dispatch,
            args=(event_type, event),
            daemon=True,
        )
        thread.start()
    
    def get_handlers(self, event_type: str) -> list[HandlerEntry]:
        """获取某事件的所有处理函数"""
        with self._lock:
            return list(self._handlers.get(event_type, []))
    
    def clear(self) -> None:
        """清除所有订阅"""
        with self._lock:
            self._handlers.clear()
    
    def __repr__(self) -> str:
        total = sum(len(handlers) for handlers in self._handlers.values())
        return f"<EventDispatcher: {len(self._handlers)} event types, {total} handlers>"
