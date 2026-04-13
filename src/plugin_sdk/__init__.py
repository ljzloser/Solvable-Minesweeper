"""
插件 SDK

提供给插件开发者使用的模块：
- BasePlugin: 插件基类
- PluginInfo: 插件信息
- config_types: 配置类型
- service_registry: 服务注册
- server_bridge: 服务端桥接（主进程使用）
"""

from .plugin_base import (
    BasePlugin,
    PluginInfo,
    PluginLifecycle,
    WindowMode,
    LogLevel,
    make_plugin_icon,
)
from .service_registry import (
    ServiceRegistry,
    ServiceNotFoundError,
    ServiceAlreadyRegisteredError,
)
from .server_bridge import GameServerBridge

# 配置类型
from .config_types import (
    BaseConfig,
    ConfigWidgetBase,
    ConfigWidgetWrapper,
    OtherInfoBase,
    BoolConfig,
    IntConfig,
    FloatConfig,
    ChoiceConfig,
    TextConfig,
    ColorConfig,
    FileConfig,
    PathConfig,
    LongTextConfig,
    RangeConfig,
)

__all__ = [
    # 插件基类
    "BasePlugin",
    "PluginInfo",
    "PluginLifecycle",
    "WindowMode",
    "LogLevel",
    "make_plugin_icon",
    # 服务注册
    "ServiceRegistry",
    "ServiceNotFoundError",
    "ServiceAlreadyRegisteredError",
    # 服务端桥接
    "GameServerBridge",
    # 配置类型
    "BaseConfig",
    "ConfigWidgetBase",
    "ConfigWidgetWrapper",
    "OtherInfoBase",
    "BoolConfig",
    "IntConfig",
    "FloatConfig",
    "ChoiceConfig",
    "TextConfig",
    "ColorConfig",
    "FileConfig",
    "PathConfig",
    "LongTextConfig",
    "RangeConfig",
]
