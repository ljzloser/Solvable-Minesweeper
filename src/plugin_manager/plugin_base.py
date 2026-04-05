"""
插件基类定义

每个插件同时具备：
- 后台数据处理能力（订阅事件、处理数据）
- 界面交互能力（可选的 PyQt 界面）

注意：插件共享同一个 ZMQClient，事件通过 EventDispatcher 内部分发
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

_E = TypeVar("_E", bound="BaseEvent")

if TYPE_CHECKING:
    from PyQt5.QtGui import QIcon

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QBrush, QFont

from lib_zmq_plugins.shared.base import BaseEvent, get_event_tag

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget
    from lib_zmq_plugins.client.zmq_client import ZMQClient
    from .event_dispatcher import EventDispatcher


def make_plugin_icon(
    color: str = "#1976d2",
    symbol: str = "?",
    size: int = 64,
) -> QIcon:
    """
    生成插件默认图标的工厂函数

    Args:
        color: 圆形背景颜色（十六进制）
        symbol: 圆心显示的文字/符号
        size: 图标像素尺寸

    Returns:
        生成的 QIcon

    Usage::

        PLUGIN_INFO = PluginInfo(..., icon=make_plugin_icon("#e65100", "📝"))
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)  # type: ignore[attr-defined]

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # 圆形背景
    p.setPen(Qt.NoPen)  # type: ignore[attr-defined]
    p.setBrush(QBrush(QColor(color)))
    p.drawEllipse(pix.rect().adjusted(3, 3, -3, -3))

    # 符号文字
    pen = QPen(QColor("white"), 2)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)  # type: ignore[attr-defined]
    font = QFont("Segoe UI Emoji", int(size * 0.44), QFont.Bold)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignCenter | Qt.AlignVCenter, symbol)  # type: ignore[attr-defined]
    p.end()

    return QIcon(pix)


class WindowMode(str):
    """窗口加载方式枚举"""
    TAB = "tab"           # 标签页内加载
    DETACHED = "detached"  # 独立窗口加载
    CLOSED = "closed"      # 不自动加载

    @classmethod
    def _values(cls) -> list[str]:
        return [cls.TAB, cls.DETACHED, cls.CLOSED]

    # 用于 QComboBox 的显示标签映射
    LABELS = {
        TAB: "标签页内",
        DETACHED: "独立窗口",
        CLOSED: "不自动加载",
    }


class LogLevel(str):
    """日志级别枚举"""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    @classmethod
    def _values(cls) -> list[str]:
        return [cls.TRACE, cls.DEBUG, cls.INFO, cls.WARNING, cls.ERROR]

    # 用于 QComboBox 的显示标签（中文友好）
    LABELS = {
        TRACE: "TRACE (最详细)",
        DEBUG: "DEBUG",
        INFO: "INFO (常规)",
        WARNING: "WARNING",
        ERROR: "ERROR (仅错误)",
    }


@dataclass
class PluginInfo:
    """插件元信息"""
    name: str  # 插件名称
    version: str = "1.0.0"  # 版本号
    author: str = ""  # 作者
    description: str = ""  # 描述
    enabled: bool = True  # 是否启用
    priority: int = 100  # 优先级（数值越小越先执行）
    show_window: bool = True  # 初始化时是否显示窗口
    window_mode: WindowMode = cast(WindowMode, "tab")  # 窗口加载方式
    log_level: LogLevel = cast(LogLevel, "DEBUG")  # 默认日志级别
    icon: QIcon | None = None  # 插件图标，None 使用默认蓝色问号
    log_config: "LogConfig | None" = None  # 日志轮转配置，None 使用全局默认值


class BasePlugin(ABC):
    """
    插件基类
    
    每个插件同时具备后台数据处理和界面交互能力：
    - 后台部分：订阅事件、处理数据、发送控制指令
    - 界面部分：可选的 PyQt 界面组件
    
    所有插件共享同一个 ZMQClient，事件通过 EventDispatcher 内部分发。

    子类必须实现 ``plugin_info()`` 类方法来声明元信息::

        class MyPlugin(BasePlugin):
            @classmethod
            def plugin_info(cls) -> PluginInfo:
                return PluginInfo(
                    name="my_plugin",
                    description="我的插件",
                    icon=make_plugin_icon("#e65100", "📝"),
                )
    """

    @classmethod
    @abstractmethod
    def plugin_info(cls) -> PluginInfo:
        """返回插件元信息。子类必须重写此方法。"""

    def __init__(self, info: PluginInfo):
        self._info = info
        self._client: ZMQClient | None = None
        self._event_dispatcher: EventDispatcher | None = None
        self._widget: QWidget | None = None
        self._initialized = False

        # 每个插件拥有独立的 loguru logger（日志写入 plugins/<name>.log）
        from .logging_setup import get_plugin_logger
        self.logger, self._log_sink_id = get_plugin_logger(
            info.name,
            log_config=info.log_config,  # 插件可自定义轮转策略
        )
        self._log_level: LogLevel = info.log_level  # 当前日志级别
    
    # ═══════════════════════════════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════════════════════════════
    
    @property
    def info(self) -> PluginInfo:
        return self._info
    
    @property
    def name(self) -> str:
        return self._info.name
    
    @property
    def is_enabled(self) -> bool:
        return self._info.enabled
    
    @property
    def widget(self) -> QWidget | None:
        return self._widget
    
    @property
    def client(self) -> ZMQClient | None:
        return self._client

    @property
    def log_level(self) -> LogLevel:
        """当前日志级别"""
        return self._log_level

    def set_log_level(self, level: LogLevel | str) -> None:
        """
        动态设置插件的日志级别

        Args:
            level: 日志级别 (LogLevel 枚举或字符串 "TRACE"/"DEBUG" 等)
        """
        from .logging_setup import set_plugin_log_level
        if isinstance(level, str):
            level = LogLevel(level.upper())
        self._log_level = level
        set_plugin_log_level(self._log_sink_id, level)
        self.logger.debug("Log level changed to %s", level)

    @property
    def plugin_icon(self) -> QIcon:
        """返回插件图标（使用 PluginInfo.icon，未设置则生成默认图标）"""
        if self._info.icon:
            return self._info.icon
        return make_plugin_icon()
    
    # ═══════════════════════════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════════════════════════
    
    def set_client(self, client: ZMQClient) -> None:
        self._client = client
    
    def set_event_dispatcher(self, dispatcher: EventDispatcher) -> None:
        self._event_dispatcher = dispatcher
    
    def initialize(self) -> None:
        """初始化插件"""
        if self._initialized:
            return
        
        self._setup_subscriptions()
        self._widget = self._create_widget()
        self._initialized = True
        self.on_initialized()
    
    def shutdown(self) -> None:
        """关闭插件"""
        if not self._initialized:
            return
        
        self.on_shutdown()
        
        if self._event_dispatcher:
            self._event_dispatcher.unsubscribe_all(self)
        
        if self._widget:
            self._widget.deleteLater()
            self._widget = None
        
        self._initialized = False
    
    # ═══════════════════════════════════════════════════════════════════
    # 抽象方法
    # ═══════════════════════════════════════════════════════════════════
    
    @abstractmethod
    def _setup_subscriptions(self) -> None:
        """
        设置事件订阅
        
        子类实现此方法，订阅感兴趣的事件：
            self.subscribe(GameStartedEvent, self._on_game_started)
            self.subscribe(BoardUpdateEvent, self._on_board_update)
        """
        pass
    
    # ═══════════════════════════════════════════════════════════════════
    # 可选重写
    # ═══════════════════════════════════════════════════════════════════
    
    def _create_widget(self) -> QWidget | None:
        """创建界面组件，返回 None 表示无界面"""
        return None
    
    def on_initialized(self) -> None:
        """插件初始化完成回调"""
        pass
    
    def on_shutdown(self) -> None:
        """插件关闭前回调"""
        pass
    
    # ═══════════════════════════════════════════════════════════════════
    # 事件订阅（使用事件类）
    # ═══════════════════════════════════════════════════════════════════
    
    def subscribe(
        self,
        event_class: type[_E],
        handler: Callable[[_E], None],
    ) -> None:
        """
        订阅事件

        Args:
            event_class: 事件类（如 GameStartedEvent）
            handler: 事件处理函数，参数类型必须与 event_class 一致
        """
        if self._event_dispatcher:
            tag = get_event_tag(event_class)
            self._event_dispatcher.subscribe(tag, handler, self._info.priority, self)
    
    def unsubscribe(self, event_class: type[BaseEvent]) -> None:
        """取消订阅事件"""
        if self._event_dispatcher:
            tag = get_event_tag(event_class)
            self._event_dispatcher.unsubscribe(tag, self)
    
    # ═══════════════════════════════════════════════════════════════════
    # 指令发送
    # ═══════════════════════════════════════════════════════════════════
    
    def send_command(self, command: Any) -> None:
        """发送控制指令到主进程（异步）"""
        if self._client:
            self._client.send_command(command)
    
    def request(self, command: Any, timeout: float = 5.0) -> Any:
        """发送请求并等待响应（同步）"""
        if self._client:
            return self._client.request(command, timeout)
        return None
    
    # ═══════════════════════════════════════════════════════════════════
    # 辅助
    # ═══════════════════════════════════════════════════════════════════
    
    def enable(self) -> None:
        """启用插件"""
        self._info.enabled = True
        if not self._initialized:
            self.initialize()
    
    def disable(self) -> None:
        """禁用插件"""
        self._info.enabled = False
        if self._initialized:
            self.shutdown()
    
    def __repr__(self) -> str:
        return f"<Plugin {self._info.name} v{self._info.version}>"
